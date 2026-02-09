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

# NOTE: Heatmap causes large OSC packets -> OFF for stability
SEND_HEATMAP = False

# Heatmap grid resolution (kept for future, but not sent)
GRID_W = 16
GRID_H = 9
HEAT_DECAY = 0.96
HEAT_ADD_PER_PERSON = 1

# Fake YOLO (people simulation)
SIM_ENABLED = True
SIM_PEOPLE_MIN = 1
SIM_PEOPLE_MAX = 3
SIM_SPEED = 0.12
SIM_TICK = 0.1

# DWELL-TO-VOTE
DWELL_SECONDS = 5.0

# Branch thresholds + hysteresis
TH_CRISIS_ENTER = 25
TH_CRISIS_EXIT  = 35

TH_ECO_ENTER = 70
TH_ECO_EXIT  = 60

TH_GRIDLOCK_ENTER = 30
TH_GRIDLOCK_EXIT  = 40
# ---------------------------------------

client = SimpleUDPClient(PROCESSING_IP, PROCESSING_PORT)

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, int(v)))

# City state (0..100)
city = {"housing": 50, "green": 50, "mobility": 50, "social": 50, "budget": 50}

# ---------------- STORY / NARRATIVE TREE ----------------
DECKS = {
    "NORMAL": [
        {
            "title": "Empty Lot Decision",
            "situation": "A central empty lot becomes available. What should the city prioritize?",
            "options": {
                "HOUSING": "Build affordable apartments (fast approval).",
                "GREEN": "Create a public park + shade trees.",
                "MOBILITY": "Turn it into a transit hub + bike parking."
            },
            "effects": {
                "HOUSING": {"housing": +7, "green": -3, "mobility": 0,  "social": +2, "budget": -4},
                "GREEN":   {"housing": -2, "green": +8, "mobility": 0,  "social": +3, "budget": -3},
                "MOBILITY":{"housing": 0,  "green": -2, "mobility": +8, "social": +1, "budget": -5},
            }
        },
        {
            "title": "Heatwave Week",
            "situation": "A heatwave hits. Citizens ask for immediate measures.",
            "options": {
                "HOUSING": "Retrofit buildings with insulation + cooling support.",
                "GREEN": "Plant trees + add water fountains in streets.",
                "MOBILITY": "Reduce car traffic + expand shaded transit stops."
            },
            "effects": {
                "HOUSING": {"housing": +5, "green": -1, "mobility": 0,  "social": +3, "budget": -6},
                "GREEN":   {"housing": 0,  "green": +7, "mobility": +1, "social": +4, "budget": -4},
                "MOBILITY":{"housing": -1, "green": +1, "mobility": +6, "social": +2, "budget": -3},
            }
        },
        {
            "title": "Commuter Conflict",
            "situation": "Rush hours are chaotic. Residents demand solutions.",
            "options": {
                "HOUSING": "Encourage mixed-use housing near jobs (reduce commuting).",
                "GREEN": "Convert a lane into a green corridor (calmer streets).",
                "MOBILITY": "Increase bus frequency + dedicated lanes."
            },
            "effects": {
                "HOUSING": {"housing": +6, "green": -2, "mobility": +2, "social": +2, "budget": -4},
                "GREEN":   {"housing": -2, "green": +6, "mobility": +1, "social": +2, "budget": -2},
                "MOBILITY":{"housing": 0,  "green": -1, "mobility": +8, "social": +1, "budget": -5},
            }
        },
        {
            "title": "New Investor Offer",
            "situation": "An investor offers funding, but wants visible impact quickly.",
            "options": {
                "HOUSING": "Build a showcase housing block (high density).",
                "GREEN": "Create a landmark park project.",
                "MOBILITY": "Launch a new tram line section."
            },
            "effects": {
                "HOUSING": {"housing": +8, "green": -4, "mobility": 0,  "social": +1, "budget": +3},
                "GREEN":   {"housing": -1, "green": +8, "mobility": 0,  "social": +2, "budget": +2},
                "MOBILITY":{"housing": 0,  "green": -2, "mobility": +8, "social": +1, "budget": +1},
            }
        },
    ],

    "ECO": [
        {
            "title": "Eco Momentum",
            "situation": "Your green policy is trending. International media wants a flagship project.",
            "options": {
                "HOUSING": "Eco-housing prototypes (wood + passive cooling).",
                "GREEN": "Turn streets into micro-forests + shade corridors.",
                "MOBILITY": "Ban cars from the center + expand cycling grid."
            },
            "effects": {
                "HOUSING": {"housing": +6, "green": +2, "mobility": 0,  "social": +2, "budget": -5},
                "GREEN":   {"housing": -1, "green": +9, "mobility": +1, "social": +3, "budget": -4},
                "MOBILITY":{"housing": 0,  "green": +3, "mobility": +7, "social": +1, "budget": -4},
            }
        },
        {
            "title": "Water as Commons",
            "situation": "Summer drought: you must choose how to protect public life.",
            "options": {
                "HOUSING": "Subsidize greywater systems in buildings.",
                "GREEN": "Prioritize public fountains + irrigation for parks.",
                "MOBILITY": "Cool corridors at transit stops + shaded routes."
            },
            "effects": {
                "HOUSING": {"housing": +4, "green": +1, "mobility": 0,  "social": +2, "budget": -4},
                "GREEN":   {"housing": 0,  "green": +7, "mobility": 0,  "social": +3, "budget": -5},
                "MOBILITY":{"housing": 0,  "green": +2, "mobility": +5, "social": +2, "budget": -4},
            }
        },
        {
            "title": "Biodiversity Debate",
            "situation": "Residents want wilder parks, but maintenance teams warn about costs.",
            "options": {
                "HOUSING": "Compact housing to free land for nature.",
                "GREEN": "Rewild parks + reduce mowing (biodiversity boost).",
                "MOBILITY": "Turn parking into pollinator streets + cycle lanes."
            },
            "effects": {
                "HOUSING": {"housing": +6, "green": +2, "mobility": 0,  "social": +1, "budget": -3},
                "GREEN":   {"housing": -1, "green": +8, "mobility": 0,  "social": +2, "budget": -2},
                "MOBILITY":{"housing": 0,  "green": +4, "mobility": +6, "social": +1, "budget": -3},
            }
        },
    ],

    "CRISIS": [
        {
            "title": "Budget Crisis",
            "situation": "Budget is critical. Services risk shutdown. Choose what to protect.",
            "options": {
                "HOUSING": "Cut luxury permits, protect basic housing aid.",
                "GREEN": "Pause new parks, keep only essential green maintenance.",
                "MOBILITY": "Reduce service frequency, keep one strong corridor."
            },
            "effects": {
                "HOUSING": {"housing": +4, "green": -2, "mobility": -1, "social": +1, "budget": +7},
                "GREEN":   {"housing": -1, "green": +1, "mobility": -1, "social": 0,  "budget": +8},
                "MOBILITY":{"housing": -1, "green": -1, "mobility": +2, "social": -1, "budget": +7},
            }
        },
        {
            "title": "Protest Night",
            "situation": "Protests rise. People ask: who is the city for?",
            "options": {
                "HOUSING": "Emergency shelters + anti-eviction policy.",
                "GREEN": "Open public spaces for assemblies + dialogue.",
                "MOBILITY": "Guarantee night buses for safe movement."
            },
            "effects": {
                "HOUSING": {"housing": +7, "green": 0,  "mobility": 0,  "social": +5, "budget": -4},
                "GREEN":   {"housing": 0,  "green": +4, "mobility": 0,  "social": +4, "budget": -3},
                "MOBILITY":{"housing": 0,  "green": 0,  "mobility": +6, "social": +3, "budget": -4},
            }
        },
        {
            "title": "External Aid Offer",
            "situation": "A bailout is offered, but it comes with constraints.",
            "options": {
                "HOUSING": "Accept aid for housing only (targeted stability).",
                "GREEN": "Accept aid for climate resilience (long-term savings).",
                "MOBILITY": "Accept aid for transit modernization (efficiency)."
            },
            "effects": {
                "HOUSING": {"housing": +8, "green": -1, "mobility": 0,  "social": +2, "budget": +6},
                "GREEN":   {"housing": 0,  "green": +7, "mobility": 0,  "social": +1, "budget": +7},
                "MOBILITY":{"housing": 0,  "green": -1, "mobility": +8, "social": +1, "budget": +6},
            }
        },
    ],

    "GRIDLOCK": [
        {
            "title": "Traffic Collapse",
            "situation": "Mobility is failing. Ambulances are delayed. What is the emergency move?",
            "options": {
                "HOUSING": "Allow temporary housing near hospitals + job centers.",
                "GREEN": "Create green 'slow streets' to reduce car dominance.",
                "MOBILITY": "Emergency bus lanes + signal priority now."
            },
            "effects": {
                "HOUSING": {"housing": +6, "green": -1, "mobility": +3, "social": +1, "budget": -3},
                "GREEN":   {"housing": -1, "green": +6, "mobility": +2, "social": +2, "budget": -2},
                "MOBILITY":{"housing": 0,  "green": -1, "mobility": +9, "social": +1, "budget": -5},
            }
        },
        {
            "title": "Micromobility Boom",
            "situation": "Scooters and bikes surge. Conflicts rise between pedestrians and riders.",
            "options": {
                "HOUSING": "Build mixed-use hubs to reduce trip length.",
                "GREEN": "Create shared green promenades (slow, calm movement).",
                "MOBILITY": "Separate lanes + enforce rules + parking zones."
            },
            "effects": {
                "HOUSING": {"housing": +6, "green": 0,  "mobility": +2, "social": +1, "budget": -3},
                "GREEN":   {"housing": -1, "green": +6, "mobility": +1, "social": +2, "budget": -2},
                "MOBILITY":{"housing": 0,  "green": -1, "mobility": +7, "social": +1, "budget": -4},
            }
        },
        {
            "title": "Night Transit",
            "situation": "Night movement is unsafe and slow. Workers demand reliability.",
            "options": {
                "HOUSING": "Support worker housing near night economy zones.",
                "GREEN": "Lighted green corridors for walking safety.",
                "MOBILITY": "Night buses + on-demand shuttle pilots."
            },
            "effects": {
                "HOUSING": {"housing": +5, "green": 0,  "mobility": +1, "social": +2, "budget": -3},
                "GREEN":   {"housing": 0,  "green": +5, "mobility": +1, "social": +2, "budget": -2},
                "MOBILITY":{"housing": 0,  "green": 0,  "mobility": +8, "social": +2, "budget": -4},
            }
        },
    ],
}

TRANSITIONS = {
    "ECO": {
        "title": "PATH SHIFT: ECO CITY",
        "situation": "Green policies dominate the narrative. The city pivots to ecology-first decisions.",
        "options": {"HOUSING":"Eco housing.", "GREEN":"Green expansion.", "MOBILITY":"Car-light mobility."},
        "effects": {
            "HOUSING": {"housing": +3, "green": +2, "mobility": 0,  "social": +1, "budget": -2},
            "GREEN":   {"housing": 0,  "green": +4, "mobility": 0,  "social": +1, "budget": -2},
            "MOBILITY":{"housing": 0,  "green": +2, "mobility": +3, "social": +1, "budget": -2},
        }
    },
    "CRISIS": {
        "title": "PATH SHIFT: CRISIS MODE",
        "situation": "Budget pressure forces tough trade-offs. Survival and stability become the theme.",
        "options": {"HOUSING":"Protect shelter.", "GREEN":"Essential green.", "MOBILITY":"Core corridor."},
        "effects": {
            "HOUSING": {"housing": +2, "green": -1, "mobility": 0,  "social": +1, "budget": +3},
            "GREEN":   {"housing": 0,  "green": +1, "mobility": 0,  "social": 0,  "budget": +3},
            "MOBILITY":{"housing": 0,  "green": 0,  "mobility": +2, "social": 0,  "budget": +3},
        }
    },
    "GRIDLOCK": {
        "title": "PATH SHIFT: GRIDLOCK",
        "situation": "Mobility collapses. The city enters emergency movement planning.",
        "options": {"HOUSING":"Local hubs.", "GREEN":"Calm streets.", "MOBILITY":"Emergency transit."},
        "effects": {
            "HOUSING": {"housing": +2, "green": 0,  "mobility": +1, "social": +1, "budget": -2},
            "GREEN":   {"housing": 0,  "green": +2, "mobility": +1, "social": +1, "budget": -1},
            "MOBILITY":{"housing": 0,  "green": 0,  "mobility": +3, "social": +1, "budget": -3},
        }
    },
    "NORMAL": {
        "title": "PATH SHIFT: NORMAL",
        "situation": "The city stabilizes. Choices return to long-term planning and balance.",
        "options": {"HOUSING":"Steady housing.", "GREEN":"Maintain green.", "MOBILITY":"Improve reliability."},
        "effects": {
            "HOUSING": {"housing": +2, "green": 0,  "mobility": 0,  "social": +1, "budget": -1},
            "GREEN":   {"housing": 0,  "green": +2, "mobility": 0,  "social": +1, "budget": -1},
            "MOBILITY":{"housing": 0,  "green": 0,  "mobility": +2, "social": +1, "budget": -1},
        }
    }
}

current_path = "NORMAL"
deck_index = {k: 0 for k in DECKS.keys()}
transition_pending = None

# ---------------- GAME STATE ----------------
state = {
    "round": 1,
    "prompt": "Starting…",
    "time_left": ROUND_DURATION,
    "scores": {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0},
    "zone_counts": {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0},
    "people": [],
    "people_count": 0,
    "avg_speed": 0.0,
    "max_speed": 0.0,
    "dwell_seconds": DWELL_SECONDS,
    "story": {},
    "last_result": "",
    "city": city,
    "path": current_path,
    # kept for future (not sent)
    "grid_w": GRID_W,
    "grid_h": GRID_H,
    "heatmap": [0]*(GRID_W*GRID_H),
}

round_start_time = time.time()
_people = []
_last_sim_t = time.time()
_dwell = {}  # pid -> {zone, enter_t, voted}

def zone_from_x(nx: float) -> str:
    if nx < 1/3:
        return "HOUSING"
    elif nx < 2/3:
        return "GREEN"
    else:
        return "MOBILITY"

def current_card():
    global transition_pending
    if transition_pending is not None:
        return TRANSITIONS[transition_pending]
    deck = DECKS[current_path]
    i = deck_index[current_path] % len(deck)
    return deck[i]

def advance_card_pointer():
    global transition_pending
    if transition_pending is not None:
        transition_pending = None
        return
    deck_index[current_path] = (deck_index[current_path] + 1) % len(DECKS[current_path])

def set_story_payload():
    c = current_card()
    state["story"] = {
        "path": current_path if transition_pending is None else transition_pending,
        "title": c["title"],
        "situation": c["situation"],
        "options": c["options"],
    }
    state["prompt"] = c["title"]
    state["path"] = current_path if transition_pending is None else transition_pending

# ---------------- OSC SEND (SPLIT) ----------------
def send_core():
    payload = {
        "round": state["round"],
        "time_left": state["time_left"],
        "prompt": state["prompt"],
        "last_result": state["last_result"],
        "dwell_seconds": state["dwell_seconds"],
        "scores": state["scores"],
        "zone_counts": state["zone_counts"],
    }
    client.send_message("/game/core", json.dumps(payload))

def send_story():
    client.send_message("/game/story", json.dumps(state["story"]))

def send_city():
    client.send_message("/game/city", json.dumps(city))

def send_people():
    # people list can still grow later, but right now it's small
    client.send_message("/game/people", json.dumps(state["people"]))

def send_heatmap():
    if not SEND_HEATMAP:
        return
    payload = {
        "grid_w": GRID_W,
        "grid_h": GRID_H,
        "heatmap": state["heatmap"]
    }
    client.send_message("/game/heatmap", json.dumps(payload))

def send_all():
    # order doesn't matter, but keep consistent
    send_core()
    send_story()
    send_city()
    send_people()
    send_heatmap()

def reset_round_data():
    for k in state["scores"]:
        state["scores"][k] = 0
    for k in state["zone_counts"]:
        state["zone_counts"][k] = 0
    # heatmap kept but not sent
    state["heatmap"] = [0]*(GRID_W*GRID_H)

    now = time.time()
    for pid in list(_dwell.keys()):
        _dwell[pid]["voted"] = False
        _dwell[pid]["enter_t"] = now

def decide_winner():
    s = state["scores"]
    maxv = max(s.values())
    zones = [z for z, v in s.items() if v == maxv]
    if len(zones) == 1:
        return zones[0]

    occ = state["zone_counts"]
    maxo = max(occ[z] for z in zones)
    zones2 = [z for z in zones if occ[z] == maxo]
    if len(zones2) == 1:
        return zones2[0]
    return random.choice(zones2)

def apply_effects_for_choice(card, winner_zone: str):
    eff = card["effects"].get(winner_zone, {})
    for k, dv in eff.items():
        city[k] = clamp(city[k] + dv, 0, 100)

def evaluate_next_path():
    global current_path
    b = city["budget"]
    g = city["green"]
    m = city["mobility"]

    if current_path == "CRISIS":
        if b > TH_CRISIS_EXIT:
            return "NORMAL"
        return "CRISIS"
    if current_path == "ECO":
        if g < TH_ECO_EXIT:
            return "NORMAL"
        return "ECO"
    if current_path == "GRIDLOCK":
        if m > TH_GRIDLOCK_EXIT:
            return "NORMAL"
        return "GRIDLOCK"

    if b < TH_CRISIS_ENTER:
        return "CRISIS"
    if m < TH_GRIDLOCK_ENTER:
        return "GRIDLOCK"
    if g > TH_ECO_ENTER:
        return "ECO"
    return "NORMAL"

def end_round_and_advance():
    global current_path, transition_pending, round_start_time

    card = current_card()
    winner = decide_winner()
    apply_effects_for_choice(card, winner)

    choice_text = card["options"][winner]
    state["last_result"] = f"Round {state['round']} → {winner}: {choice_text}"

    next_path = evaluate_next_path()
    if next_path != current_path:
        transition_pending = next_path
        current_path = next_path

    advance_card_pointer()

    state["round"] += 1
    reset_round_data()
    set_story_payload()

    round_start_time = time.time()
    state["time_left"] = ROUND_DURATION

    send_all()

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
    for p in state["people"]:
        pid = int(p.get("id", 0))
        z = zone_from_x(p["x"])

        if pid not in _dwell:
            _dwell[pid] = {"zone": z, "enter_t": now, "voted": False}

        if _dwell[pid]["zone"] != z:
            _dwell[pid]["zone"] = z
            _dwell[pid]["enter_t"] = now
            _dwell[pid]["voted"] = False

        dwell_time = now - _dwell[pid]["enter_t"]
        progress = max(0.0, min(1.0, dwell_time / DWELL_SECONDS))

        p["zone"] = z
        p["dwell"] = float(dwell_time)
        p["dwell_progress"] = float(progress)
        p["ready"] = bool(progress >= 1.0 and not _dwell[pid]["voted"])

        if dwell_time >= DWELL_SECONDS and not _dwell[pid]["voted"]:
            state["scores"][z] += 1
            state["prompt"] = f"Dwell vote registered: {z}"
            _dwell[pid]["voted"] = True

def round_timer_loop():
    while True:
        time.sleep(0.2)
        elapsed = time.time() - round_start_time
        left = max(0, int(ROUND_DURATION - elapsed))
        state["time_left"] = left
        if elapsed >= ROUND_DURATION:
            end_round_and_advance()
        else:
            send_all()

# ---------------- Sim people ----------------
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
        update_zone_counts_from_people()
        compute_speed_metrics()
        update_dwell_and_votes(now)
        send_all()

# ---------------- OSC Handlers ----------------
def on_zone_click(address, zone_name, *_):
    z = str(zone_name)
    if z in state["scores"]:
        state["scores"][z] += 1
        state["prompt"] = f"Manual vote registered: {z}"
        send_all()

def on_people_json(address, people_json):
    try:
        people = json.loads(str(people_json))
        if isinstance(people, list):
            state["people"] = people
            now = time.time()
            update_zone_counts_from_people()
            compute_speed_metrics()
            update_dwell_and_votes(now)
            send_all()
    except Exception as e:
        state["prompt"] = f"Bad /game/people JSON: {e}"
        send_all()

dispatcher = Dispatcher()
dispatcher.map("/game/zone_click", on_zone_click)
dispatcher.map("/game/people_in", on_people_json)

if __name__ == "__main__":
    print("Starting Group02 Floor Game Server (SPLIT OSC, HEATMAP OFF)")
    print(f"Listening OSC on {PYTHON_IP}:{PYTHON_PORT} | Sending to {PROCESSING_IP}:{PROCESSING_PORT}")

    set_story_payload()
    send_all()

    threading.Thread(target=round_timer_loop, daemon=True).start()
    threading.Thread(target=sim_loop, daemon=True).start()

    server = BlockingOSCUDPServer((PYTHON_IP, PYTHON_PORT), dispatcher)
    server.serve_forever()