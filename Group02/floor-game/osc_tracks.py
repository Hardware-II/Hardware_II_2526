from ultralytics import YOLO
from pythonosc.udp_client import SimpleUDPClient
import cv2
import time

# ================= SETTINGS =================
MODEL_PATH = "yolov8n.pt"   # hiljem saad panna "models/reed_best.pt"
SOURCE = "videos/14728180_3840_2160_60fps.mp4"
TRACKER = "botsort.yaml"
CLASSES = [0]  # COCO person class
OSC_HOST = "127.0.0.1"
OSC_PORT = 8000
OSC_ADDRESS = "/tracks"
SEND_FPS = 5   # 0 = send every frame
DEBUG_VIEW = True
# ============================================


def tracks_from_result(res, frame_w, frame_h):
    tracks = []
    if res is None or res.boxes is None:
        return tracks

    boxes = res.boxes
    ids = getattr(boxes, "id", None)

    xyxy = boxes.xyxy.cpu().numpy()
    conf = boxes.conf.cpu().numpy()
    cls = boxes.cls.cpu().numpy()

    for i, bb in enumerate(xyxy):
        if int(cls[i]) not in CLASSES:
            continue

        x1, y1, x2, y2 = bb.tolist()
        w = max(0.0, x2 - x1)
        h = max(0.0, y2 - y1)
        cx = x1 + w / 2.0
        cy = y1 + h / 2.0

        track_id = int(ids[i].item()) if ids is not None else -1

        tracks.append({
            "id": track_id,
            "cx": cx / frame_w,
            "cy": cy / frame_h,
            "w": w / frame_w,
            "h": h / frame_h,
            "conf": float(conf[i]),
        })

    return tracks


def main():
    model = YOLO(MODEL_PATH)
    client = SimpleUDPClient(OSC_HOST, OSC_PORT)

    cap = cv2.VideoCapture(SOURCE)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {SOURCE}")

    # create resizable window once
    if DEBUG_VIEW:
        cv2.namedWindow("OSC tracks debug", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("OSC tracks debug", 900, 500)

    send_dt = (1.0 / SEND_FPS) if SEND_FPS and SEND_FPS > 0 else 0.0
    last_send = 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        h, w = frame.shape[:2]

        results = model.track(
            source=frame,
            tracker=TRACKER,
            persist=True,
            verbose=False
        )

        res = results[0] if results else None
        tracks = tracks_from_result(res, w, h)

        # ---------- OSC SEND ----------
        now = time.time()
        if (not send_dt) or (now - last_send >= send_dt):
            last_send = now
            payload = []
            for t in tracks:
                payload += [
                    t["id"],
                    t["cx"],
                    t["cy"],
                    t["w"],
                    t["h"],
                    t["conf"]
                ]
            client.send_message(OSC_ADDRESS, payload)

        # ---------- DEBUG VIEW ----------
        if DEBUG_VIEW:
            for t in tracks:
                cx = int(t["cx"] * w)
                cy = int(t["cy"] * h)
                cv2.circle(frame, (cx, cy), 6, (0, 255, 0), -1)
                cv2.putText(
                    frame,
                    f"id:{t['id']}",
                    (cx + 8, cy - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

            cv2.imshow("OSC tracks debug", frame)

            if (cv2.waitKey(1) & 0xFF) == 27:  # ESC
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
    
    