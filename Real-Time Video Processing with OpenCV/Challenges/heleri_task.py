import cv2
import numpy as np


def nothing(x):
    pass


def main():
    cap = cv2.VideoCapture(0)  # kui ei tööta, proovi 1 või 2
    if not cap.isOpened():
        raise RuntimeError("Webcam ei avanenud. Proovi VideoCapture(1) või kontrolli kaamera õigusi.")

    # --- Flags / toggles ---
    use_gray = False
    use_blur = False
    use_edges = False
    draw_overlay = True
    use_hsv = False          # BGR -> HSV (visualiseerimiseks)
    hsv_to_bgr_demo = False  # HSV -> BGR demo (teeme HSV-s väikse muudatuse ja konverdime tagasi)
    creative_mode = 0        # 0=off, 1=invert, 2=colormap, 3=cartoon

    scale = 1.0  # resize scale

    # Akna seadistus
    window = "Heleri OpenCV Challenge"
    cv2.namedWindow(window)

    # Trackbar, et resize oleks "dünaamiline" ka hiirega
    cv2.createTrackbar("Scale %", window, 100, 200, nothing)  # 100% default, max 200%

    print("\nControls:")
    print("  q / ESC  -> quit")
    print("  g        -> toggle grayscale")
    print("  b        -> toggle blur")
    print("  e        -> toggle edge detection (Canny)")
    print("  o        -> toggle overlay (text + shapes)")
    print("  h        -> toggle BGR->HSV view")
    print("  j        -> toggle HSV->BGR demo (hue shift)")
    print("  0        -> creative off")
    print("  1        -> creative: invert")
    print("  2        -> creative: colormap")
    print("  3        -> creative: cartoon effect")
    print("  + / -    -> resize scale up/down")
    print("  r        -> reset scale to 1.0\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ------------- Dynamic Resize -------------
        tb_scale = cv2.getTrackbarPos("Scale %", window) / 100.0
        # kombineeri klahviga scale ja trackbari scale (võta näiteks keskmine või lihtsalt trackbar "võidab")
        # siin: trackbar võidab, aga + / - muudab ka trackbarit (allpool)
        scale = tb_scale

        h, w = frame.shape[:2]
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Hoia “orig” alles, et overlay jms oleks lihtne
        output = frame.copy()

        # ------------- Color Space Experiments -------------
        if use_hsv:
            hsv = cv2.cvtColor(output, cv2.COLOR_BGR2HSV)
            # HSV nägemine BGR aknas: konverdime tagasi BGR, aga see on HSV "värviruumina" nähtav
            output = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        if hsv_to_bgr_demo:
            hsv = cv2.cvtColor(output, cv2.COLOR_BGR2HSV)
            # Nihuta Hue (toon) natuke (0..179 OpenCV-s)
            hsv[..., 0] = (hsv[..., 0].astype(np.int16) + 20) % 180
            output = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        # ------------- Grayscale -------------
        if use_gray:
            gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
            output = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)  # hoia 3-kanalilisena, et overlay/efektid oleksid lihtsad

        # ------------- Blur / Edge Detection -------------
        if use_blur:
            output = cv2.GaussianBlur(output, (9, 9), 0)

        if use_edges:
            # Edge detection on tavaliselt parem gray pealt
            gray_edges = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray_edges, 60, 140)
            output = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        # ------------- Creative Effects (optional) -------------
        if creative_mode == 1:
            # invert
            output = 255 - output

        elif creative_mode == 2:
            # colormap
            gray2 = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
            output = cv2.applyColorMap(gray2, cv2.COLORMAP_JET)

        elif creative_mode == 3:
            # cartoon-ish: smooth + edges overlay
            img_color = cv2.bilateralFilter(output, d=9, sigmaColor=75, sigmaSpace=75)
            img_gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
            img_blur = cv2.medianBlur(img_gray, 7)
            img_edge = cv2.adaptiveThreshold(
                img_blur, 255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY,
                9, 2
            )
            img_edge = cv2.cvtColor(img_edge, cv2.COLOR_GRAY2BGR)
            output = cv2.bitwise_and(img_color, img_edge)

        # ------------- Draw Shapes + Text -------------
        if draw_overlay:
            oh, ow = output.shape[:2]

            # rectangle
            cv2.rectangle(output, (20, 20), (220, 120), (0, 255, 0), 2)

            # circle
            cv2.circle(output, (ow - 80, 80), 50, (255, 0, 0), 2)

            # line
            cv2.line(output, (0, oh - 1), (ow - 1, 0), (0, 0, 255), 2)

            # text
            status = f"gray:{use_gray} blur:{use_blur} edges:{use_edges} hsv_view:{use_hsv} hsv_demo:{hsv_to_bgr_demo} creative:{creative_mode} scale:{scale:.2f}"
            cv2.putText(output, status, (20, oh - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow(window, output)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break
        elif key == ord("g"):
            use_gray = not use_gray
        elif key == ord("b"):
            use_blur = not use_blur
        elif key == ord("e"):
            use_edges = not use_edges
        elif key == ord("o"):
            draw_overlay = not draw_overlay
        elif key == ord("h"):
            use_hsv = not use_hsv
        elif key == ord("j"):
            hsv_to_bgr_demo = not hsv_to_bgr_demo
        elif key == ord("0"):
            creative_mode = 0
        elif key == ord("1"):
            creative_mode = 1
        elif key == ord("2"):
            creative_mode = 2
        elif key == ord("3"):
            creative_mode = 3
        elif key in (ord("+"), ord("=")):  # '=' on sama klahv paljudel klaviatuuridel
            # suurenda trackbari
            val = cv2.getTrackbarPos("Scale %", window)
            cv2.setTrackbarPos("Scale %", window, min(200, val + 5))
        elif key in (ord("-"), ord("_")):
            val = cv2.getTrackbarPos("Scale %", window)
            cv2.setTrackbarPos("Scale %", window, max(10, val - 5))
        elif key == ord("r"):
            cv2.setTrackbarPos("Scale %", window, 100)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
