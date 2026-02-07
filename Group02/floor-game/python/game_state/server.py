from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
import json
import time

# Processing -> Python (events)
PYTHON_IP = "127.0.0.1"
PYTHON_PORT = 8000

# Python -> Processing (state)
PROCESSING_IP = "127.0.0.1"
PROCESSING_PORT = 9000

client = SimpleUDPClient(PROCESSING_IP, PROCESSING_PORT)

state = {
    "t": 0.0,
    "round": 1,
    "prompt": "Click a zone to vote (simulating stepping on the floor)",
    "scores": {"HOUSING": 0, "GREEN": 0, "MOBILITY": 0},
}

def send_state():
    state["t"] = time.time()
    client.send_message("/game/state", json.dumps(state))
    print("-> state sent:", state)

def on_zone_click(address, zone_name):
    zone_name = str(zone_name)
    if zone_name in state["scores"]:
        state["scores"][zone_name] += 1
        state["prompt"] = f"Vote registered: {zone_name}"
    else:
        state["prompt"] = f"Unknown zone: {zone_name}"
    send_state()

dispatcher = Dispatcher()
dispatcher.map("/game/zone_click", on_zone_click)

if __name__ == "__main__":
    print(f"Listening for OSC events on {PYTHON_IP}:{PYTHON_PORT}  (Processing -> Python)")
    print(f"Sending OSC state to {PROCESSING_IP}:{PROCESSING_PORT}  (Python -> Processing)")
    send_state()
    server = BlockingOSCUDPServer((PYTHON_IP, PYTHON_PORT), dispatcher)
    server.serve_forever()