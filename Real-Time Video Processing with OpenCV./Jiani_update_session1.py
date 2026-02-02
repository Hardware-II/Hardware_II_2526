import cv2
import numpy as np


cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Fail to open camera")
    exit()

# ================= human detect =================
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

mode = 0

cv2.namedWindow("Human + Hand Detection")


def nothing(x):
    pass


# scale
cv2.createTrackbar("Scale %", "Human + Hand Detection", 100, 200, nothing)


# ================= main loop =================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # ===== scale =====
    scale = cv2.getTrackbarPos("Scale %", "Human + Hand Detection")
    scale = max(scale, 30)

    w = int(frame.shape[1] * scale / 100)
    h = int(frame.shape[0] * scale / 100)
    frame = cv2.resize(frame, (w, h))

    output = frame.copy()

    # ================= image operate =================
    if mode == 1:
        output = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    elif mode == 2:
        output = cv2.GaussianBlur(frame, (15, 15), 0)

    elif mode == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        output = cv2.Canny(gray, 80, 150)

    elif mode == 4:
        output = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    elif mode == 5:  # cartoon
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 7)
        edges = cv2.adaptiveThreshold(gray, 255,
                                      cv2.ADAPTIVE_THRESH_MEAN_C,
                                      cv2.THRESH_BINARY, 9, 9)
        color = cv2.bilateralFilter(frame, 9, 250, 250)
        output = cv2.bitwise_and(color, color, mask=edges)

    
    if len(output.shape) == 2:
        output = cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)

    # =================================================
    #            ① human detect rectangle
    # =================================================
    boxes, _ = hog.detectMultiScale(frame, winStride=(8, 8))

    person_count = 0

    for (x, y, w, h) in boxes:
        person_count += 1

        cv2.rectangle(output, (x, y), (x + w, y + h),
                      (0, 255, 0), 3)

        cv2.putText(output, "Person",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 0), 2)

    # =================================================
    #            ② hand detect circle
    # =================================================
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower_skin = np.array([0, 30, 60])
    upper_skin = np.array([20, 150, 255])

    mask = cv2.inRange(hsv, lower_skin, upper_skin)

    mask = cv2.GaussianBlur(mask, (5, 5), 0)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    hand_count = 0

    for cnt in contours:
        area = cv2.contourArea(cnt)

        if area > 2000:  
            (x, y), radius = cv2.minEnclosingCircle(cnt)

            if radius > 20:
                hand_count += 1

                center = (int(x), int(y))
                radius = int(radius)

                cv2.circle(output, center, radius,
                           (255, 0, 0), 3)

                cv2.putText(output, "Hand",
                            (center[0] - 20, center[1] - radius - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (255, 0, 0), 2)

    # =================================================
    # information
    # =================================================
    cv2.putText(output,
                f"Mode:{mode}  Person:{person_count}  Hand:{hand_count}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2)

    cv2.imshow("Human + Hand Detection", output)

    # ================= key =================
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break
    elif key in [ord(str(i)) for i in range(6)]:
        mode = int(chr(key))


cap.release()
cv2.destroyAllWindows()