from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

import json
import time
import threading
import random
import math

# ---------------- CONFIG ----------------
PYTHON_IP = "127.0.0.1"
PYTHON_PORT = 8000

PROCESSING_IP = "127.0.0.1"
PROCESSING_PORT = 9000

ROUND_DURATION = 30  # seconds

# Heatmap grid resolution
GRID_W = 16
GRID_H = 9

# Heatmap decay (0.0..1.0). Closer to 1.0 = slower fade
HEAT_DECAY = 0.96
HEAT_ADD_PER_PERSON = 1

# Fake YOLO (people simulation)
SIM_ENABLED = True
SIM_PEOPLE_MIN = 1
SIM_PEOPLE_MAX = 3
SIM_SPEED = 0.12  # normalized units per second
SIM_TICK = 0.1    # seconds

# DWELL-TO-VOTE
DWELL_SECONDS = 5.0
# ---------------------------------------

client = SimpleUDPClient(PROCESSING_IP, PROCESSING_PORT)

PROMPTS = [
    "More housing vs green space?",
    "Invest in public transport?",
    "Build parking or bike lanes?",
    "Expand parks or apartments?",
    "More offices downtown?"
]

state = {
    "t": 0.0,
    "round": 1,
    "prompt": PROMPTS[0],
    "time_left": ROUND_DURATION,

    # votes
    "scores": {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0},

    # occupancy outputs
    "zone_counts": {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0},

    # heatmap
    "grid_w": GRID_W,
    "grid_h": GRID_H,
    "heatmap": [0] * (GRID_W * GRID_H),

    # people detections (normalized 0..1)
    "people": [],

    # metrics
    "people_count": 0,
    "avg_speed": 0.0,
    "max_speed": 0.0,

    # dwell config for UI
    "dwell_seconds": DWELL_SECONDS,
}

round_start_time = time.time()

# Internal people state for simulator
_people = []
_last_sim_t = time.time()

# Dwell tracking per person id
# example:
# _dwell[id] = {"zone": "GREEN", "enter_t": 123.4, "voted": False}
_dwell = {}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def zone_from_x(nx: float) -> str:
    if nx < 1/3:
        return "HOUSING"
    elif nx < 2/3:
        return "GREEN"
    else:
        return "MOBILITY"


def send_state():
    state["t"] = time.time()
    client.send_message("/game/state", json.dumps(state))


def reset_round_data():
    for k in state["scores"]:
        state["scores"][k] = 0
    for k in state["zone_counts"]:
        state["zone_counts"][k] = 0
    state["heatmap"] = [0] * (GRID_W * GRID_H)

    # reset dwell votes each round
    for pid in list(_dwell.keys()):
        _dwell[pid]["voted"] = False
        _dwell[pid]["enter_t"] = time.time()


def next_round():
    global round_start_time

    state["round"] += 1
    reset_round_data()

    prompt_index = (state["round"] - 1) % len(PROMPTS)
    state["prompt"] = PROMPTS[prompt_index]

    round_start_time = time.time()
    state["time_left"] = ROUND_DURATION

    print(f"\n=== ROUND {state['round']} === {state['prompt']}")
    send_state()


def grid_index_from_norm(nx, ny):
    gx = int(nx * GRID_W)
    gy = int(ny * GRID_H)
    gx = clamp(gx, 0, GRID_W - 1)
    gy = clamp(gy, 0, GRID_H - 1)
    return gy * GRID_W + gx


def apply_heat_decay():
    hm = state["heatmap"]
    for i in range(len(hm)):
        hm[i] = int(hm[i] * HEAT_DECAY)
    state["heatmap"] = hm


def add_heat_from_people():
    hm = state["heatmap"]
    for p in state["people"]:
        idx = grid_index_from_norm(p["x"], p["y"])
        hm[idx] += HEAT_ADD_PER_PERSON
    state["heatmap"] = hm


def update_zone_counts_from_people():
    counts = {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0}
    for p in state["people"]:
        counts[zone_from_x(p["x"])] += 1
    state["zone_counts"] = counts


def compute_speed_metrics():
    speeds = [p.get("speed", 0.0) for p in state["people"]]
    if not speeds:
        state["people_count"] = 0
        state["avg_speed"] = 0.0
        state["max_speed"] = 0.0
        return
    state["people_count"] = len(speeds)
    state["avg_speed"] = sum(speeds) / len(speeds)
    state["max_speed"] = max(speeds)


def update_dwell_and_votes(now: float):
    """
    For each person:
    - determine current zone
    - if zone changed: reset timer + allow voting again
    - if stayed >= DWELL_SECONDS and not voted yet: register vote once
    Also write dwell_progress into people dict for UI.
    """
    for p in state["people"]:
        pid = int(p.get("id", 0))
        z = zone_from_x(p["x"])

        if pid not in _dwell:
            _dwell[pid] = {"zone": z, "enter_t": now, "voted": False}

        # zone change => reset dwell + allow new vote
        if _dwell[pid]["zone"] != z:
            _dwell[pid]["zone"] = z
            _dwell[pid]["enter_t"] = now
            _dwell[pid]["voted"] = False

        dwell_time = now - _dwell[pid]["enter_t"]
        progress = clamp(dwell_time / DWELL_SECONDS, 0.0, 1.0)

        # attach to people for UI
        p["zone"] = z
        p["dwell"] = float(dwell_time)
        p["dwell_progress"] = float(progress)
        p["ready"] = bool(progress >= 1.0 and not _dwell[pid]["voted"])

        # vote once per "stay"
        if dwell_time >= DWELL_SECONDS and not _dwell[pid]["voted"]:
            if z in state["scores"]:
                state["scores"][z] += 1
                state["prompt"] = f"Dwell vote registered: {z}"
            _dwell[pid]["voted"] = True


def round_timer_loop():
    while True:
        time.sleep(0.2)
        elapsed = time.time() - round_start_time
        state["time_left"] = max(0, int(ROUND_DURATION - elapsed))
        send_state()
        if elapsed >= ROUND_DURATION:
            next_round()


# ---------------- Fake YOLO (people simulation) ----------------

def _spawn_people():
    global _people
    n = random.randint(SIM_PEOPLE_MIN, SIM_PEOPLE_MAX)
    _people = []
    for i in range(n):
        _people.append({
            "id": i,
            "x": random.random(),
            "y": random.random(),
            "vx": (random.random()*2 - 1) * SIM_SPEED,
            "vy": (random.random()*2 - 1) * SIM_SPEED,
        })


def _step_people(dt):
    for p in _people:
        p["vx"] += (random.random()*2 - 1) * 0.03
        p["vy"] += (random.random()*2 - 1) * 0.03

        sp = math.sqrt(p["vx"]*p["vx"] + p["vy"]*p["vy"])
        if sp > SIM_SPEED:
            p["vx"] = (p["vx"] / sp) * SIM_SPEED
            p["vy"] = (p["vy"] / sp) * SIM_SPEED

        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt

        if p["x"] < 0:
            p["x"] = 0
            p["vx"] *= -1
        if p["x"] > 1:
            p["x"] = 1
            p["vx"] *= -1
        if p["y"] < 0:
            p["y"] = 0
            p["vy"] *= -1
        if p["y"] > 1:
            p["y"] = 1
            p["vy"] *= -1


def sim_loop():
    global _last_sim_t
    if SIM_ENABLED:
        _spawn_people()

    while True:
        time.sleep(SIM_TICK)
        now = time.time()
        dt = now - _last_sim_t
        _last_sim_t = now

        if not SIM_ENABLED:
            continue

        _step_people(dt)

        people = []
        for p in _people:
            speed = math.sqrt(p["vx"]*p["vx"] + p["vy"]*p["vy"])
            people.append({
                "id": int(p["id"]),
                "x": float(p["x"]),
                "y": float(p["y"]),
                "vx": float(p["vx"]),
                "vy": float(p["vy"]),
                "speed": float(speed),
            })

        state["people"] = people

        # Update quantitative outputs
        apply_heat_decay()
        add_heat_from_people()
        update_zone_counts_from_people()
        compute_speed_metrics()

        # Dwell vote update (this modifies scores + attaches dwell_progress to people)
        update_dwell_and_votes(now)

        # Keep prompt "scenario" unless we just voted
        if "Dwell vote registered" not in state["prompt"]:
            state["prompt"] = PROMPTS[(state["round"] - 1) % len(PROMPTS)]

        send_state()


# ---------------- OSC Handlers ----------------

def on_zone_click(address, zone_name, px=None, py=None, w=None, h=None):
    """
    Optional manual vote click (keeps useful for debugging).
    """
    zone = str(zone_name)
    if zone in state["scores"]:
        state["scores"][zone] += 1
        state["prompt"] = f"Manual vote registered: {zone}"
    else:
        state["prompt"] = f"Unknown zone: {zone}"
    send_state()


def on_people_json(address, people_json):
    """
    ROS2->OSC can send detections to server:
      /game/people  "<JSON string list of people>"
    Format:
      [{"id":1,"x":0.2,"y":0.7,"vx":0,"vy":0,"speed":0}, ...]
    """
    try:
        people = json.loads(str(people_json))
        if isinstance(people, list):
            state["people"] = people

            apply_heat_decay()
            add_heat_from_people()
            update_zone_counts_from_people()
            compute_speed_metrics()
            update_dwell_and_votes(time.time())

            send_state()
    except Exception as e:
        state["prompt"] = f"Bad /game/people JSON: {e}"
        send_state()


dispatcher = Dispatcher()
dispatcher.map("/game/zone_click", on_zone_click)
dispatcher.map("/game/people", on_people_json)

if __name__ == "__main__":
    print("Starting Group02 Floor Game Server (DWELL=5s + fake YOLO + decay)")
    print(f"Listening OSC on {PYTHON_IP}:{PYTHON_PORT} | Sending state to {PROCESSING_IP}:{PROCESSING_PORT}")

    threading.Thread(target=round_timer_loop, daemon=True).start()
    threading.Thread(target=sim_loop, daemon=True).start()

    send_state()

    server = BlockingOSCUDPServer((PYTHON_IP, PYTHON_PORT), dispatcher)
    server.serve_forever()