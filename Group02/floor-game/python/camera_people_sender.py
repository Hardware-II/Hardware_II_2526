import time
import json
import math
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np
from pythonosc.udp_client import SimpleUDPClient


# ----------------------------
# CONFIG
# ----------------------------
SERVER_IP = "127.0.0.1"   # your Python game server
SERVER_PORT = 8000        # server listens here for OSC

OSC_ADDR = "/game/people_in"

CAM_INDEX = 0             # 0 = default webcam
TARGET_FPS = 15           # keep it light
MIN_AREA = 900            # blob size threshold (tune)
MAX_PEOPLE = 8            # cap to avoid huge packets

# normalize coordinates to 0..1 for Processing mapping
# x,y = center of blob in frame
# speed computed in normalized units / second

# Press keys:
#   q = quit
#   + / - adjust MIN_AREA
#   v toggle show preview window


@dataclass
class Track:
    tid: int
    x: float
    y: float
    vx: float
    vy: float
    last_t: float


def dist2(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def main():
    global MIN_AREA

    print("Starting camera_people_sender.py")
    print(f"Sending OSC to {SERVER_IP}:{SERVER_PORT} addr {OSC_ADDR}")
    print("Controls: q quit | +/- blob size threshold | v toggle preview")

    client = SimpleUDPClient(SERVER_IP, SERVER_PORT)

    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Try CAM_INDEX=1 or check permissions.")

    # Reduce resolution to stabilize + speed
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    # Background subtractor = “motion detector”
    bg = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=40, detectShadows=True)

    tracks: List[Track] = []
    next_id = 0
    show_preview = True

    last_send = 0.0
    frame_t_prev = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Camera read failed.")
            break

        t = time.time()
        dt = max(1e-6, t - frame_t_prev)
        frame_t_prev = t

        h, w = frame.shape[:2]

        # background subtraction
        fg = bg.apply(frame)

        # clean mask
        fg = cv2.medianBlur(fg, 5)
        _, fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)

        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
        fg = cv2.morphologyEx(fg, cv2.MORPH_DILATE, np.ones((5, 5), np.uint8), iterations=1)

        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Extract blob centers
        centers = []
        boxes = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < MIN_AREA:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            cx = x + bw / 2.0
            cy = y + bh / 2.0
            centers.append((cx / w, cy / h))
            boxes.append((x, y, bw, bh, area))

        # Keep only top biggest blobs (avoid huge packets)
        if len(centers) > MAX_PEOPLE:
            # sort by area desc
            idx = np.argsort([-b[4] for b in boxes]).tolist()
            idx = idx[:MAX_PEOPLE]
            centers = [centers[i] for i in idx]
            boxes = [boxes[i] for i in idx]

        # Simple nearest-neighbor tracking
        used_tracks = set()
        assigned = {}

        for ci, cxy in enumerate(centers):
            best_j = -1
            best_d = 1e9
            for j, tr in enumerate(tracks):
                if j in used_tracks:
                    continue
                d = dist2((tr.x, tr.y), cxy)
                if d < best_d:
                    best_d = d
                    best_j = j
            # distance threshold for "same person"
            if best_j != -1 and best_d < 0.03 * 0.03:
                assigned[ci] = best_j
                used_tracks.add(best_j)

        # Update matched tracks
        for ci, tj in assigned.items():
            tr = tracks[tj]
            nx, ny = centers[ci]
            vx = (nx - tr.x) / dt
            vy = (ny - tr.y) / dt
            tr.x = nx
            tr.y = ny
            tr.vx = vx
            tr.vy = vy
            tr.last_t = t

        # Create new tracks for unmatched centers
        for ci, cxy in enumerate(centers):
            if ci in assigned:
                continue
            nx, ny = cxy
            tracks.append(Track(tid=next_id, x=nx, y=ny, vx=0.0, vy=0.0, last_t=t))
            next_id += 1

        # Remove stale tracks
        tracks = [tr for tr in tracks if (t - tr.last_t) < 1.0]

        # Build people payload (list of dicts)
        people = []
        for tr in tracks:
            speed = math.sqrt(tr.vx * tr.vx + tr.vy * tr.vy)
            people.append({
                "id": int(tr.tid),
                "x": clamp01(tr.x),
                "y": clamp01(tr.y),
                "vx": float(tr.vx),
                "vy": float(tr.vy),
                "speed": float(speed),
            })

        # Send at TARGET_FPS
        if t - last_send >= (1.0 / TARGET_FPS):
            client.send_message(OSC_ADDR, json.dumps(people))
            last_send = t

        # Preview (optional)
        if show_preview:
            vis = frame.copy()
            for (x, y, bw, bh, area) in boxes:
                cv2.rectangle(vis, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
            cv2.putText(
                vis,
                f"blobs={len(centers)} tracks={len(tracks)} MIN_AREA={MIN_AREA}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )
            cv2.imshow("camera_people_sender (press q)", vis)
            # also show mask small
            cv2.imshow("mask", fg)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("+") or key == ord("="):
            MIN_AREA += 200
            print("MIN_AREA =", MIN_AREA)
        if key == ord("-") or key == ord("_"):
            MIN_AREA = max(200, MIN_AREA - 200)
            print("MIN_AREA =", MIN_AREA)
        if key == ord("v"):
            show_preview = not show_preview
            if not show_preview:
                cv2.destroyWindow("camera_people_sender (press q)")
                cv2.destroyWindow("mask")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()