"""
ROS2 -> OSC bridge skeleton.

Idea:
- Subscribe to a ROS2 topic with people detections (example: PoseArray on /people)
- Convert detections to normalized coordinates (0..1)
- Send OSC message to the game server:
    address: /game/people
    payload: JSON string (list of people dicts)
"""

import json
from pythonosc.udp_client import SimpleUDPClient

# OSC target = our game server
OSC_IP = "127.0.0.1"
OSC_PORT = 8000

client = SimpleUDPClient(OSC_IP, OSC_PORT)

def send_people(people_list):
    client.send_message("/game/people", json.dumps(people_list))

def main():
    print("ROS2->OSC bridge skeleton")
    print("This file requires ROS2 (rclpy) installed to run.")
    print("When ready, add:")
    print("- import rclpy")
    print("- create node")
    print("- subscribe to /people (PoseArray or Detection2DArray)")
    print("- in callback, build people_list = [{'id':..,'x':..,'y':..,'vx':0,'vy':0,'speed':0}, ...]")
    print("- call send_people(people_list)")

if __name__ == "__main__":
    main()