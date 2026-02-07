from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

import json
import time
import threading

# ---------------- CONFIG ----------------
PYTHON_IP = "127.0.0.1"
PYTHON_PORT = 8000

PROCESSING_IP = "127.0.0.1"
PROCESSING_PORT = 9000

ROUND_DURATION = 30  # seconds
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
    "scores": {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0},
}

round_start_time = time.time()


def send_state():
    """Send full game state to Processing via OSC as a JSON string."""
    state["t"] = time.time()
    payload = json.dumps(state)
    client.send_message("/game/state", payload)
    print("-> state sent:", state)


def reset_scores():
    for k in state["scores"]:
        state["scores"][k] = 0


def next_round():
    """Advance to next round every ROUND_DURATION seconds."""
    global round_start_time

    state["round"] += 1
    reset_scores()

    prompt_index = (state["round"] - 1) % len(PROMPTS)
    state["prompt"] = PROMPTS[prompt_index]

    round_start_time = time.time()
    print(f"\n=== ROUND {state['round']} === {state['prompt']}")

    send_state()


def round_timer_loop():
    """Background timer thread that triggers next rounds."""
    while True:
        time.sleep(1)
        if time.time() - round_start_time >= ROUND_DURATION:
            next_round()


def on_zone_click(address, zone_name):
    """Receive a click/vote from Processing."""
    zone = str(zone_name)

    if zone in state["scores"]:
        state["scores"][zone] += 1
        state["prompt"] = f"Vote registered: {zone}"
    else:
        state["prompt"] = f"Unknown zone: {zone}"

    send_state()


dispatcher = Dispatcher()
dispatcher.map("/game/zone_click", on_zone_click)


if __name__ == "__main__":
    print("Starting Group02 Floor Game Server")
    print(f"Listening for OSC events on {PYTHON_IP}:{PYTHON_PORT} (Processing -> Python)")
    print(f"Sending OSC state to {PROCESSING_IP}:{PROCESSING_PORT} (Python -> Processing)")

    # start timer in background
    timer_thread = threading.Thread(target=round_timer_loop, daemon=True)
    timer_thread.start()

    # send initial state
    send_state()

    # start OSC server (blocking)
    server = BlockingOSCUDPServer((PYTHON_IP, PYTHON_PORT), dispatcher)
    server.serve_forever()