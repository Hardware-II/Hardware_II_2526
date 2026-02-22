"""
Urban Park Interactive Design Table
====================================
Entry point. Usage:

    python main.py [path/to/park_plan.png]

If no path is given a file-picker dialog is shown.
"""
from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import time
import tkinter as tk
import urllib.parse
import urllib.request
from tkinter import filedialog
from typing import Dict, Optional

from dotenv import load_dotenv
load_dotenv()  # loads .env into os.environ before anything else runs

import pygame

from src.camera import CameraThread
from src.calibration import CalibrationController
from src.gesture import GestureRecognizer
from src.homography import HomographyMapper
from src.interaction import InteractionController, State
from src.models import FurnitureType, PlacedItem
from src.renderer import Renderer
from src.session import SessionManager
from src.tilemap import TileMap
from src.voice import VoiceController


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH  = os.path.join(HERE, "config.json")
CATALOG_PATH = os.path.join(HERE, "assets", "sprites", "catalog.json")
SPRITES_DIR  = os.path.join(HERE, "assets", "sprites")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)



def load_catalog(config: dict) -> Dict[str, FurnitureType]:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    catalog: Dict[str, FurnitureType] = {}
    for item in data["items"]:
        sprite_path = os.path.join(SPRITES_DIR, item["sprite"])
        catalog[item["id"]] = FurnitureType(
            id=item["id"],
            label=item["label"],
            category=item["category"],
            sprite_path=sprite_path,
            nominal_w=item.get("nominal_w", config.get("item_nominal_size_px", 80)),
            nominal_h=item.get("nominal_h", config.get("item_nominal_size_px", 80)),
            color=tuple(item.get("color", [120, 120, 120])),
        )
    return catalog


def pick_plan_file() -> Optional[str]:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="Select park plan image",
        filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
    )
    root.destroy()
    return path if path else None


def geocode_location(query: str, token: str) -> Optional[tuple]:
    """Resolve a place name to (lat, lon) via the Mapbox Geocoding API."""
    encoded = urllib.parse.quote(query)
    url = (
        f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded}.json"
        f"?access_token={token}"
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
        features = data.get("features", [])
        if features:
            lon, lat = features[0]["center"]
            return lat, lon
    except Exception as e:
        print(f"[Mapbox geocode] {e}")
    return None


def fetch_mapbox_satellite(
    lat: float, lon: float, zoom: int, token: str,
    width: int = 1280, height: int = 960,
) -> Optional[str]:
    """Download a Mapbox satellite tile; return path to a temp PNG, or None on error."""
    width  = max(1, min(1280, width))
    height = max(1, min(1280, height))
    url = (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static"
        f"/{lon},{lat},{zoom}/{width}x{height}"
        f"?access_token={token}"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read()
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(data)
        tmp.close()
        return tmp.name
    except Exception as e:
        print(f"[Mapbox fetch] {e}")
    return None


def show_mapbox_dialog(
    token: str, lat: float, lon: float, zoom: int
) -> Optional[tuple]:
    """Tkinter dialog for Mapbox location input. Returns (lat, lon, zoom) or None."""
    result_holder: list = []

    root = tk.Tk()
    root.title("Load Mapbox Satellite")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    pad = {"padx": 8, "pady": 4}

    tk.Label(root, text="Search place:").grid(row=0, column=0, sticky="w", **pad)
    search_var = tk.StringVar()
    search_entry = tk.Entry(root, textvariable=search_var, width=28)
    search_entry.grid(row=0, column=1, **pad)
    search_entry.focus_set()

    status_var = tk.StringVar(value="Type a place name and click Search, or enter lat/lon directly.")
    tk.Label(root, textvariable=status_var, fg="gray", font=("Arial", 9)).grid(
        row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4)
    )

    lat_var  = tk.StringVar(value=str(lat))
    lon_var  = tk.StringVar(value=str(lon))
    zoom_var = tk.StringVar(value=str(zoom))

    def do_search():
        q = search_var.get().strip()
        if not q:
            return
        status_var.set("Searching…")
        root.update()
        res = geocode_location(q, token)
        if res:
            lat_var.set(f"{res[0]:.6f}")
            lon_var.set(f"{res[1]:.6f}")
            status_var.set(f"Found: {q}")
        else:
            status_var.set("Location not found.")

    tk.Button(root, text="Search", command=do_search).grid(row=0, column=2, **pad)

    tk.Label(root, text="Latitude:").grid(row=2, column=0, sticky="w", **pad)
    tk.Entry(root, textvariable=lat_var, width=16).grid(row=2, column=1, sticky="w", **pad)

    tk.Label(root, text="Longitude:").grid(row=3, column=0, sticky="w", **pad)
    tk.Entry(root, textvariable=lon_var, width=16).grid(row=3, column=1, sticky="w", **pad)

    tk.Label(root, text="Zoom (1–22):").grid(row=4, column=0, sticky="w", **pad)
    tk.Entry(root, textvariable=zoom_var, width=6).grid(row=4, column=1, sticky="w", **pad)

    tk.Label(root, text="  Tip: zoom 17–19 works best for park design.", fg="gray",
             font=("Arial", 9)).grid(row=4, column=2, sticky="w", padx=4)

    def on_ok():
        try:
            r_lat  = float(lat_var.get())
            r_lon  = float(lon_var.get())
            r_zoom = max(1, min(22, int(zoom_var.get())))
        except ValueError:
            status_var.set("Invalid values — check lat/lon/zoom.")
            return
        result_holder.append((r_lat, r_lon, r_zoom))
        root.destroy()

    def on_cancel():
        root.destroy()

    search_entry.bind("<Return>", lambda _: do_search())

    btn_frame = tk.Frame(root)
    btn_frame.grid(row=5, column=0, columnspan=3, pady=8)
    tk.Button(btn_frame, text="Load Satellite", command=on_ok,     width=14).pack(side="left", padx=4)
    tk.Button(btn_frame, text="Load Image File…", command=on_cancel, width=14).pack(side="left", padx=4)

    root.mainloop()
    return result_holder[0] if result_holder else None


def select_sidebar_side(config: dict) -> str:
    """Simple pygame dialog to choose sidebar side at session start."""
    # Just read from config — instructor edits config.json
    return config.get("sidebar_side", "right")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # ---- Config & catalog ----
    config = load_config()
    catalog = load_catalog(config)

    # Prefer the environment variable; fall back to config.json (empty by default).
    _env_token = os.environ.get("MAPBOX_TOKEN", "").strip()
    if _env_token:
        config["mapbox_token"] = _env_token
    mapbox_token = config.get("mapbox_token", "").strip()

    # ---- Pygame init ----
    pygame.init()
    pygame.mouse.set_visible(False)

    W = config.get("screen_width", 1920)
    H = config.get("screen_height", 1080)
    fullscreen = config.get("fullscreen", True)

    flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF if fullscreen else pygame.RESIZABLE
    screen = pygame.display.set_mode((W, H), flags)
    W, H = screen.get_size()  # SDL may return a different size due to DPI scaling
    pygame.display.set_caption("Urban Park Design Table")
    clock = pygame.time.Clock()
    TARGET_FPS = 30

    # ---- Slippy map (tile streaming) ----
    tilemap = TileMap(config)

    # ---- Core objects ----
    homography = HomographyMapper()
    camera = CameraThread(config)
    recognizer = GestureRecognizer(config)
    renderer = Renderer(screen, config, catalog, tilemap=tilemap)
    session_mgr = SessionManager("")

    # ---- Voice ----
    voice = VoiceController(config, catalog)
    voice.start()

    # ---- Layout rects from renderer ----
    canvas_rect  = renderer.canvas_rect
    sidebar_rect = renderer.sidebar_rect

    print(f"[main] screen={W}x{H} canvas={canvas_rect} sidebar={sidebar_rect}")

    # Pre-load initial viewport tiles during calibration so the map is ready immediately
    tilemap.prefetch(canvas_rect)

    # ---- Interaction controller ----
    ctrl = InteractionController(config, catalog, canvas_rect, sidebar_rect)

    # ---- Calibration ----
    calib = CalibrationController(W, H, homography, config)

    # ---- Start camera ----
    camera.start()

    # ---- Phases ----
    PHASE_CALIBRATION = "calibration"
    PHASE_RUNNING     = "running"
    phase = PHASE_CALIBRATION

    debug_enabled = config.get("debug_overlay", False)

    # Cursor persistence — keeps cursor visible for 300 ms after tracking is lost
    _last_cursor_pos = None
    _cursor_last_seen = 0.0
    CURSOR_PERSIST_S = 0.3

    # Two-hand map navigation state
    _two_hand_mid:  Optional[tuple] = None
    _two_hand_dist: Optional[float] = None

    # ---- Main loop ----
    running = True
    prev_time = time.monotonic()

    while running:
        now = time.monotonic()
        dt = now - prev_time
        prev_time = now

        # ---- Events ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                ctrl_held = mods & pygame.KMOD_CTRL

                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_SPACE:
                    if phase == PHASE_CALIBRATION:
                        calib.skip()   # instant auto-scale mapping, skip 4-point tap

                elif event.key == pygame.K_e and ctrl_held:
                    if phase == PHASE_RUNNING:
                        path = session_mgr.export_png(screen, canvas_rect)
                        ctrl.show_toast(f"Saved: {os.path.basename(path)}", 3.0)

                elif event.key == pygame.K_r and ctrl_held:
                    if phase == PHASE_RUNNING:
                        ctrl.reset_session()
                        ctrl.show_toast("Session reset.", 2.0)

                elif event.key == pygame.K_d and ctrl_held:
                    debug_enabled = not debug_enabled

                elif event.key == pygame.K_m and ctrl_held:
                    if phase == PHASE_RUNNING:
                        loc = show_mapbox_dialog(
                            mapbox_token,
                            tilemap.lat,
                            tilemap.lon,
                            int(tilemap.zoom),
                        )
                        if loc:
                            lat, lon, zoom = loc
                            tilemap.reset(lat, lon, float(zoom))
                            ctrl.show_toast(f"Map centred on ({lat:.4f}, {lon:.4f})", 2.0)

                elif event.key == pygame.K_c and ctrl_held:
                    # Re-run calibration
                    homography = HomographyMapper()
                    calib = CalibrationController(W, H, homography, config)
                    phase = PHASE_CALIBRATION

                # ---- Map zoom (no modifier needed) ----
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    if phase == PHASE_RUNNING:
                        renderer.map_zoom_by(1.2)
                        ctrl.show_toast(f"Zoom {renderer.map_zoom:.1f}\u00d7", 1.0)

                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    if phase == PHASE_RUNNING:
                        renderer.map_zoom_by(1 / 1.2)
                        ctrl.show_toast(f"Zoom {renderer.map_zoom:.1f}\u00d7", 1.0)

                elif event.key == pygame.K_0:
                    if phase == PHASE_RUNNING:
                        renderer.map_reset()
                        ctrl.show_toast("Map reset", 1.0)

        # ---- Map pan (held arrow keys, frame-rate independent) ----
        if phase == PHASE_RUNNING:
            keys      = pygame.key.get_pressed()
            pan_speed = 400   # px / second
            pan_px    = pan_speed * dt
            if keys[pygame.K_LEFT]:
                renderer.map_pan_by(-pan_px, 0)
            if keys[pygame.K_RIGHT]:
                renderer.map_pan_by( pan_px, 0)
            if keys[pygame.K_UP]:
                renderer.map_pan_by(0, -pan_px)
            if keys[pygame.K_DOWN]:
                renderer.map_pan_by(0,  pan_px)

        # ---- Camera data ----
        frame_result = camera.get_latest()

        # ---- Phase: CALIBRATION ----
        if phase == PHASE_CALIBRATION:
            calib.update(frame_result)
            calib.draw(screen)
            if calib.is_complete:
                phase = PHASE_RUNNING
                time.sleep(0.8)   # brief pause to show "complete" message
                # Seed cursor AFTER sleep so persist timer starts fresh
                _last_cursor_pos = (W // 2, H // 2)
                _cursor_last_seen = time.monotonic()
            pygame.display.flip()
            continue

        # ---- Phase: RUNNING ----
        hand_data     = None
        screen_pos    = None
        raw_landmarks = None
        tracking_fps  = 0.0

        if frame_result:
            tracking_fps = frame_result.tracking_fps

        # ---- Two-hand map navigation vs single-hand furniture ----
        n_hands = len(frame_result.hands) if frame_result else 0

        if n_hands == 2:
            # Both hands visible → freeze furniture controller always
            gesture = recognizer.update(None, None, now)

            h0, h1 = frame_result.hands[0], frame_result.hands[1]

            tip0 = homography.transform(h0.landmarks[8])
            tip1 = homography.transform(h1.landmarks[8])
            ctrl.two_hand_cursors = [tip0, tip1]

            # Navigation activates when BOTH hands are pinching.
            # Use the release threshold (0.38) — a relaxed pinch is enough,
            # no need for a tight finger press.
            _nav_pinch_thresh = config.get("release_threshold_norm", 0.38)
            both_pinched = (h0.pinch_ratio < _nav_pinch_thresh and
                            h1.pinch_ratio < _nav_pinch_thresh)

            if both_pinched:
                _PAN_DAMP  = 1.2
                _ZOOM_DAMP = 0.9
                _ZOOM_CAP  = 0.08
                mid_now  = ((tip0[0] + tip1[0]) / 2, (tip0[1] + tip1[1]) / 2)
                dist_now = math.sqrt((tip0[0]-tip1[0])**2 + (tip0[1]-tip1[1])**2)

                # Pan — only apply delta once anchor is set (no jump on first frame)
                if _two_hand_mid is not None:
                    dx = (mid_now[0] - _two_hand_mid[0]) * _PAN_DAMP
                    dy = (mid_now[1] - _two_hand_mid[1]) * _PAN_DAMP
                    renderer.map_pan_by(dx, dy)

                # Zoom — distance ratio
                if _two_hand_dist is not None and _two_hand_dist > 10 and dist_now > 10:
                    raw   = dist_now / _two_hand_dist - 1.0
                    step  = max(-_ZOOM_CAP, min(_ZOOM_CAP, raw * _ZOOM_DAMP))
                    factor = 1.0 + step
                    if abs(step) > 0.0005:
                        renderer.map_zoom_by(factor)

                _two_hand_mid  = mid_now
                _two_hand_dist = dist_now
            else:
                # Hands open — hold still, reset anchor so no jump when pinch starts
                _two_hand_mid  = None
                _two_hand_dist = None

        else:
            # 0 or 1 hand → reset two-hand state, run furniture controller
            _two_hand_mid  = None
            _two_hand_dist = None
            ctrl.two_hand_cursors = None

            if frame_result and frame_result.hands:
                # Prefer non-left (right) hand
                dominant = None
                for h in frame_result.hands:
                    if not h.is_left:
                        dominant = h
                        break
                if dominant is None:
                    dominant = frame_result.hands[0]

                hand_data     = dominant
                raw_landmarks = dominant.landmarks
                index_tip_cam = dominant.landmarks[8]
                screen_pos    = homography.transform(index_tip_cam)

            gesture = recognizer.update(hand_data, screen_pos, now)

        no_hand_frames = recognizer.no_hand_frames

        # Compute dwell progress for cursor ring
        dwell_progress = 0.0
        if ctrl._dwell_target_id is not None or (
            ctrl._dwell_pos and ctrl._dwell_start > 0
        ):
            elapsed = now - ctrl._dwell_start
            dwell_s = config.get("dwell_time_ms", 1000) / 1000.0
            dwell_progress = min(elapsed / dwell_s, 1.0)

        # Sync map zoom into controller (for scale-aware hit testing)
        ctrl.map_zoom = renderer.map_zoom

        # Record screen positions before update so we can detect user-driven moves
        _prev_positions = {item.id: (item.pos[0], item.pos[1]) for item in ctrl.placed_items}

        # Update interaction state machine
        ctrl.update(
            gesture,
            no_hand_frames,
            dt,
            sidebar_tab_height=config.get("tab_row_height", 52),
            sidebar_item_height=Renderer.ITEM_ROW_H,
        )

        # ---- Map-space coordinate sync ----
        # Items are stored in canonical map-image-pixel coords (item.map_pos).
        # Each frame: if the item was moved by user interaction, re-anchor;
        # otherwise, recompute screen position from the stable map transform.
        for item in ctrl.placed_items:
            if item.map_pos is None:
                # Newly placed item — anchor to map space immediately
                item.map_pos = list(renderer.screen_to_map(item.pos[0], item.pos[1]))
            else:
                prev = _prev_positions.get(item.id)
                moved = prev is None or (
                    abs(item.pos[0] - prev[0]) > 0.5 or
                    abs(item.pos[1] - prev[1]) > 0.5
                )
                if moved:
                    # User dragged the item — re-anchor map_pos to current screen pos
                    item.map_pos = list(renderer.screen_to_map(item.pos[0], item.pos[1]))
                else:
                    # Item static — update screen pos from stable map_pos
                    sx, sy = renderer.map_to_screen(item.map_pos[0], item.map_pos[1])
                    item.pos[0] = sx
                    item.pos[1] = sy

        # Track last known cursor position for persistence
        if screen_pos is not None:
            _last_cursor_pos = screen_pos
            _cursor_last_seen = now

        # Update ghost_pos from gesture when in IDLE (cursor tracking).
        # Keep cursor visible for CURSOR_PERSIST_S after tracking is lost.
        if ctrl.state == State.IDLE:
            if screen_pos is not None:
                ctrl.ghost_pos = screen_pos
            elif _last_cursor_pos and (now - _cursor_last_seen) < CURSOR_PERSIST_S:
                ctrl.ghost_pos = _last_cursor_pos
            else:
                ctrl.ghost_pos = None

        # ---- Voice command dispatch ----
        renderer._voice_status = voice.status
        cmd = voice.get_command()
        if cmd and phase == PHASE_RUNNING:
            action = cmd.get("action")
            if action == "select":
                type_id = cmd.get("type_id")
                ft = catalog.get(type_id)
                label = ft.label if ft else type_id
                # Place item at canvas centre
                place_pos = [canvas_rect.centerx, canvas_rect.centery]
                new_item = PlacedItem(type_id=type_id, pos=place_pos)
                ctrl.placed_items.append(new_item)
                ctrl.selected_id = new_item.id
                ctrl.show_toast(f'Voice: placed "{label}"', 2.0)

            elif action == "undo":
                if ctrl.placed_items:
                    ctrl.placed_items.pop()
                    ctrl.selected_id = None
                    ctrl.show_toast("Voice: undo", 1.5)

            elif action == "reset":
                ctrl.reset_session()
                ctrl.show_toast("Voice: reset", 2.0)

            elif action == "zoom_in":
                renderer.map_zoom_by(2.0)
                ctrl.show_toast("Voice: zoom in", 1.0)

            elif action == "zoom_out":
                renderer.map_zoom_by(0.5)
                ctrl.show_toast("Voice: zoom out", 1.0)

            elif action == "export":
                path = session_mgr.export_png(screen, canvas_rect)
                ctrl.show_toast(f"Saved: {os.path.basename(path)}", 3.0)

            elif action == "goto":
                query = cmd.get("query", "")
                lat_d = cmd.get("lat")
                lon_d = cmd.get("lon")
                zoom_d = cmd.get("zoom")
                if lat_d is not None and lon_d is not None:
                    # Known park — instant jump, no API call
                    tilemap.reset(lat_d, lon_d, float(zoom_d or tilemap.zoom))
                    ctrl.show_toast(f'Voice: \u2192 {query}', 2.0)
                elif mapbox_token and query:
                    res = geocode_location(query, mapbox_token)
                    if res:
                        tilemap.reset(res[0], res[1], tilemap.zoom)
                        ctrl.show_toast(f'Voice: go to "{query}"', 2.0)
                    else:
                        ctrl.show_toast(f'Voice: "{query}" not found', 2.0)

            elif action == "rotate":
                deg = cmd.get("degrees", 0.0)
                sel = next((i for i in ctrl.placed_items if i.id == ctrl.selected_id), None)
                if sel:
                    sel.angle = (sel.angle + deg) % 360
                    ctrl.show_toast(f"Voice: rotate {deg:.0f}°", 1.5)
                else:
                    ctrl.show_toast("Voice: select an item first", 1.5)

            elif action == "scale":
                factor = cmd.get("factor", 1.0)
                sel = next((i for i in ctrl.placed_items if i.id == ctrl.selected_id), None)
                if sel:
                    cfg_min = config.get("item_min_scale", 0.2)
                    cfg_max = config.get("item_max_scale", 3.0)
                    sel.scale = max(cfg_min, min(cfg_max, sel.scale * factor))
                    ctrl.show_toast(f"Voice: scale ×{factor}", 1.5)
                else:
                    ctrl.show_toast("Voice: select an item first", 1.5)

        # ---- Render ----
        debug_frame = frame_result.raw_frame if (debug_enabled and frame_result) else None
        debug_lm    = raw_landmarks if debug_enabled else None

        renderer.draw(ctrl, tracking_fps, debug_frame, debug_lm, dwell_progress)
        pygame.display.flip()
        clock.tick(TARGET_FPS)

    # ---- Cleanup ----
    voice.stop()
    camera.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
