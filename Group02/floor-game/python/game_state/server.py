from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

import json
import time
import threading

PYTHON_IP = "127.0.0.1"
PYTHON_PORT = 8000

PROCESSING_IP = "127.0.0.1"
PROCESSING_PORT = 9000

ROUND_DURATION = 30  # seconds

# Heatmap grid resolution
GRID_W = 16
GRID_H = 9

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
    "scores": {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0},
    "zone_counts": {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0},
    "grid_w": GRID_W,
    "grid_h": GRID_H,
    "heatmap": [0] * (GRID_W * GRID_H),
}

round_start_time = time.time()


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


def round_timer_loop():
    while True:
        time.sleep(0.2)
        elapsed = time.time() - round_start_time
        state["time_left"] = max(0, int(ROUND_DURATION - elapsed))
        send_state()
        if elapsed >= ROUND_DURATION:
            next_round()


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def add_heat(px, py, width, height):
    """
    px, py are click position in pixels from Processing.
    width, height are Processing window size.
    We convert to grid cell and increment heat.
    """
    if width <= 0 or height <= 0:
        return

    gx = int((px / width) * GRID_W)
    gy = int((py / height) * GRID_H)

    gx = clamp(gx, 0, GRID_W - 1)
    gy = clamp(gy, 0, GRID_H - 1)

    idx = gy * GRID_W + gx
    state["heatmap"][idx] += 1


def on_zone_click(address, zone_name, px, py, w, h):
    zone = str(zone_name)

    if zone in state["scores"]:
        state["scores"][zone] += 1
        state["zone_counts"][zone] += 1
        state["prompt"] = f"Vote registered: {zone}"

        add_heat(float(px), float(py), float(w), float(h))
    else:
        state["prompt"] = f"Unknown zone: {zone}"

    send_state()


dispatcher = Dispatcher()
dispatcher.map("/game/zone_click", on_zone_click)


if __name__ == "__main__":
    print("Starting Group02 Floor Game Server (heatmap + timer)")
    timer_thread = threading.Thread(target=round_timer_loop, daemon=True)
    timer_thread.start()

    send_state()

    server = BlockingOSCUDPServer((PYTHON_IP, PYTHON_PORT), dispatcher)
    server.serve_forever()