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

# How strongly each person contributes per tick
HEAT_ADD_PER_PERSON = 1

# People simulation (Fake YOLO) toggle
SIM_ENABLED = True
SIM_PEOPLE_MIN = 1
SIM_PEOPLE_MAX = 3
SIM_SPEED = 0.12  # normalized units per second
SIM_TICK = 0.1    # seconds
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

    # votes (game choice)
    "scores": {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0},

    # density/occupancy outputs
    "zone_counts": {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0},
    "grid_w": GRID_W,
    "grid_h": GRID_H,
    "heatmap": [0] * (GRID_W * GRID_H),

    # people detections (normalized 0..1)
    "people": [],

    # metrics (quantitative output)
    "people_count": 0,
    "avg_speed": 0.0,
    "max_speed": 0.0,
}

round_start_time = time.time()

# Internal people state for simulator
_people = []
_last_sim_t = time.time()


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def send_state():
    state["t"] = time.time()
    client.send_message("/game/state", json.dumps(state))


def reset_round_data():
    for k in state["scores"]:
        state["scores"][k] = 0
    for k in state["zone_counts"]:
        state["zone_counts"][k] = 0
    state["heatmap"] = [0] * (GRID_W * GRID_H)


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
    # Multiply each cell by decay factor, rounding down a bit
    hm = state["heatmap"]
    for i in range(len(hm)):
        hm[i] = int(hm[i] * HEAT_DECAY)
    state["heatmap"] = hm


def add_heat_from_people():
    # Each person adds heat to their current cell
    hm = state["heatmap"]
    for p in state["people"]:
        idx = grid_index_from_norm(p["x"], p["y"])
        hm[idx] += HEAT_ADD_PER_PERSON
    state["heatmap"] = hm


def update_zone_counts_from_people():
    # Zones are 3 vertical columns: [0..1/3), [1/3..2/3), [2/3..1]
    counts = {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0}
    for p in state["people"]:
        x = p["x"]
        if x < 1/3:
            counts["HOUSING"] += 1
        elif x < 2/3:
            counts["GREEN"] += 1
        else:
            counts["MOBILITY"] += 1
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


def round_timer_loop():
    # Sends periodic state so UI stays live and timer counts down
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
    # random walk with bounce at edges
    for p in _people:
        # small random steering
        p["vx"] += (random.random()*2 - 1) * 0.03
        p["vy"] += (random.random()*2 - 1) * 0.03

        # clamp speed
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

        # convert to "detections" for Processing
        people = []
        for p in _people:
            speed = math.sqrt(p["vx"]*p["vx"] + p["vy"]*p["vy"])
            people.append({
                "id": p["id"],
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

        # Keep prompt short if not voting right now
        if "Vote registered" not in state["prompt"]:
            state["prompt"] = PROMPTS[(state["round"] - 1) % len(PROMPTS)]

        send_state()


# ---------------- OSC Handlers ----------------

def on_zone_click(address, zone_name, px=None, py=None, w=None, h=None):
    """
    Manual voting via click (still useful).
    """
    zone = str(zone_name)
    if zone in state["scores"]:
        state["scores"][zone] += 1
        state["prompt"] = f"Vote registered: {zone}"
    else:
        state["prompt"] = f"Unknown zone: {zone}"
    send_state()


def on_people_json(address, people_json):
    """
    ROS2->OSC bridge can send detections to the server:
      address: /game/people
      payload: JSON string, example:
        [{"id":1,"x":0.2,"y":0.7,"vx":0.0,"vy":0.0,"speed":0.0}, ...]
    When this arrives, we override state["people"] and update heatmap/metrics.
    """
    try:
        people = json.loads(str(people_json))
        if isinstance(people, list):
            state["people"] = people
            apply_heat_decay()
            add_heat_from_people()
            update_zone_counts_from_people()
            compute_speed_metrics()
            send_state()
    except Exception as e:
        state["prompt"] = f"Bad /game/people JSON: {e}"
        send_state()


dispatcher = Dispatcher()
dispatcher.map("/game/zone_click", on_zone_click)
dispatcher.map("/game/people", on_people_json)

if __name__ == "__main__":
    print("Starting Group02 Floor Game Server (decay + fake YOLO + OSC)")
    print(f"Listening OSC on {PYTHON_IP}:{PYTHON_PORT} | Sending state to {PROCESSING_IP}:{PROCESSING_PORT}")

    # Timer thread (rounds)
    threading.Thread(target=round_timer_loop, daemon=True).start()

    # Simulator thread (people)
    threading.Thread(target=sim_loop, daemon=True).start()

    send_state()

    server = BlockingOSCUDPServer((PYTHON_IP, PYTHON_PORT), dispatcher)
    server.serve_forever()