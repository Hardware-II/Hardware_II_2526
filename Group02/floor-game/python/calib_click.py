import cv2
import json
import os

# Save file next to this script
OUT_JSON = os.path.join(os.path.dirname(__file__), "calibration.json")

# Set projector (Processing) resolution here:
PROJ_W = 1920
PROJ_H = 1080

points = []

def on_mouse(event, x, y, flags, param):
    global points
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([int(x), int(y)])
        print(f"Clicked {len(points)}/4:", x, y)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("Camera not found (VideoCapture(0) failed).")

cv2.namedWindow("calibration_click")
cv2.setMouseCallback("calibration_click", on_mouse)

print("Click 4 points in this order: TL, TR, BR, BL")
print("Press ESC to cancel.")

while True:
    ok, frame = cap.read()
    if not ok:
        break

    # draw clicked points
    for i, p in enumerate(points):
        cv2.circle(frame, (p[0], p[1]), 8, (0, 0, 255), -1)
        cv2.putText(frame, str(i+1), (p[0]+10, p[1]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

    cv2.imshow("calibration_click", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        points = []
        break

    if len(points) == 4:
        break

cap.release()
cv2.destroyAllWindows()

if len(points) == 4:
    data = {
        "cam_pts_px": points,  # [[xTL,yTL],[xTR,yTR],[xBR,yBR],[xBL,yBL]]
        "proj_size": [PROJ_W, PROJ_H]
    }
    with open(OUT_JSON, "w") as f:
        json.dump(data, f, indent=2)
    print("Saved:", OUT_JSON)
else:
    print("No calibration saved.")