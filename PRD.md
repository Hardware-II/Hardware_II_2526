# PRD — Urban Park Interactive Design Table
**Version:** 0.2
**Date:** 2026-02-18
**Author:** [Your name]
**Status:** Draft — post-interview revision

---

## 1. Overview

The **Urban Park Interactive Design Table** is a hardware-software installation that allows
users to compose a 2D plan-view layout of an urban park using natural hand gestures captured
by an overhead RGB camera. The system runs on a standard PC and outputs to a large monitor.
No mouse, keyboard, or touch input is required during the design interaction — all
manipulation is gesture-driven.

The primary purpose is **pedagogical**: to demonstrate participatory urban design in a
classroom or workshop setting, making spatial thinking accessible without requiring CAD
skills. Sessions are short (10–30 min) with multiple participants taking turns.

---

## 2. Problem Statement

Traditional urban design tools (AutoCAD, Rhino, GIS) have steep learning curves and require
dedicated hardware. Public participation in park design is limited because non-specialists
cannot easily express spatial ideas. This system lowers the barrier: anyone who can point and
grab can place a bench or a tree.

---

## 3. Users & Context

| Stakeholder | Role |
|---|---|
| Students / workshop participants | Primary users — place and arrange furniture using gestures |
| Instructor / facilitator | Loads the base plan, manages sessions via keyboard shortcuts, guides activity |
| Observers | Watch the 86" display, discuss design decisions |

**Context:** Academic classroom running in projector-darkened conditions. A dedicated lamp
illuminates the interaction zone. Multiple participants take turns; the system must be easy to
reset between users.

---

## 4. Hardware Setup

```
        ┌──────────────────────────────────────┐
        │  Trust GXT 1160 Vero (1080p, 30fps)  │  ← mounted on top of the Optoma display
        └──────────────────┬───────────────────┘        looking down-forward at the table
                           │ USB
        ┌──────────────────▼───────────────────┐
        │         PC (high-end desktop)         │  ← Python application, dedicated RTX/RX GPU
        └──────────────────┬───────────────────┘
                           │ HDMI / DisplayPort
        ┌──────────────────▼───────────────────┐
        │    Optoma 5861RK — 86" 4K display    │  ← UI output at 1080p (display upscales to 4K)
        └──────────────────────────────────────┘
                           ▲
                    users stand here
              ┌────────────────────────┐
              │  Interaction zone      │  1957 × 1171 mm flat surface
              │  (desk in front of     │  Dedicated lamp overhead for consistent
              │   the display)         │  illumination in dim classroom
              └────────────────────────┘
```

### Key hardware details

| Item | Specification |
|---|---|
| Camera | Trust Gaming GXT 1160 Vero — 1920×1080, 30 fps, Fixed Focus, Auto White Balance, USB |
| Camera position | Mounted on top of the Optoma 86" screen — angled view, **not** purely overhead |
| Monitor | Optoma 5861RK — 86", 4K UHD (3840×2160) |
| Render resolution | Pygame renders at **1080p (1920×1080)**; display hardware upscales to 4K |
| PC | High-end desktop, dedicated GPU (RTX or RX series), 8+ CPU cores |
| Interaction zone | 1957 × 1171 mm flat table surface directly in front of the display |
| User posture | **Standing**, facing the screen |
| Hand operating height | Hands hover **~10–30 cm above the table surface** (mid-air) |
| Calibration height | Homography calibrated to **30 cm above the table** — the nominal hover plane |
| Lighting | Classroom is dim (projector-darkened). A **dedicated lamp** points at the table zone |

### Camera geometry note

The camera is at the top of an 86" screen (~2 m from floor). It looks **down and forward** at
the table surface, producing a perspective view — not a top-down orthographic projection. The
homography transform (§8) corrects for this perspective distortion. MediaPipe hand tracking
at this angle sees palms tilting toward the camera, which is within the model's training
distribution.

---

## 5. System Architecture

```
Trust GXT 1160 Vero (OpenCV VideoCapture)
        │  1920×1080 @ 30fps
        ▼
Hand Tracking (MediaPipe Hands)
        │  21-landmark skeleton per hand, up to 2 hands
        ▼
Gesture Recognizer
        │  Named gesture events: PINCH, RELEASE, HOVER, WRIST_ROLL,
        │  SWIPE_H (horizontal), SWIPE_V (vertical)
        ▼
Interaction Controller
        │  State machine: IDLE → DRAGGING_NEW | DRAGGING_PLACED |
        │  ROTATING | SCALING | SIDEBAR_SCROLL | TAB_SWITCH
        ▼
UI / Renderer (Pygame @ 1920×1080)
        │
        ▼
Optoma 5861RK (HDMI — displays 1080p, upscales to 4K)
```

### Modules

| Module | Technology | Responsibility |
|---|---|---|
| Camera capture | OpenCV `cv2.VideoCapture` (USB index 0) | Grab 1080p frames from Trust GXT 1160 |
| Hand tracking | MediaPipe `Hands` (model_complexity=1) | Detect up to 2 hands, return 21 landmarks each |
| Gesture recognizer | Custom Python | Classify landmark patterns into named gesture events |
| Coordinate mapper | Custom Python + OpenCV | Project camera 2D coords → screen UI coords via homography H |
| Interaction controller | Custom Python | State machine mapping gesture events + position → UI commands |
| UI / Renderer | Pygame 2.x | Draw plan, sidebar, furniture sprites, cursor, overlays |
| Furniture data | JSON + PNG sprites | Catalog of furniture types with icons (assets already available) |
| Session manager | Python | Load plan image, export PNG, reset session |

---

## 6. Functional Requirements

### FR-1: Plan Import

| ID | Requirement |
|---|---|
| FR-1.1 | The system shall accept a raster image (PNG, JPEG) as the base park plan |
| FR-1.2 | The plan image shall be loaded at startup via a file-picker dialog or CLI argument |
| FR-1.3 | The plan shall be displayed in the main canvas area, letterboxed or pillarboxed to fit any aspect ratio |
| FR-1.4 | The canvas background (outside the plan image) shall use an earthy neutral tone matching the visual theme |
| FR-1.5 | The plan shall remain static (non-editable) during a design session |
| FR-1.6 | The system shall handle landscape, portrait, and square plan images gracefully |
| FR-1.7 | SVG support is desirable but not required for v1 |

### FR-2: Furniture Catalog Sidebar

| ID | Requirement |
|---|---|
| FR-2.1 | A vertical sidebar (~25% of screen width) shall display furniture organized by category |
| FR-2.2 | Category tabs shall appear at the top of the sidebar; a **horizontal swipe** gesture across the tab row cycles between tabs |
| FR-2.3 | The active tab's items are shown below the tabs; if items exceed the sidebar height, a **vertical swipe** gesture scrolls them |
| FR-2.4 | Each furniture item shall display: a PNG icon, a label, and a **count badge** showing how many of that type are currently placed on the canvas |
| FR-2.5 | The sidebar shall be displayed on the left or right side of the screen, configurable at session startup |
| FR-2.6 | Moving the cursor hand into the sidebar zone shall automatically deselect any selected canvas item |
| FR-2.7 | The catalog shall include at minimum the items in the categories below |

**Furniture categories (v1 catalog — PNG sprite assets already available):**

| Category | Items |
|---|---|
| Seating | Bench, picnic table, lounger |
| Vegetation | Deciduous tree, conifer, shrub, flower bed |
| Play | Swing set, slide, climbing frame, sandbox |
| Lighting | Lamp post, solar bollard |
| Water | Fountain, drinking station |
| Services | Waste bin, bike rack, information board |
| Paths | Paving tile (1×1 m), stepping stone |

### FR-3: Gesture Interaction

#### Gesture vocabulary

| Gesture name | Physical motion | Detected via |
|---|---|---|
| **HOVER** | Open hand, index extended, palm faces camera | All fingers extended; pinch ratio > release threshold |
| **PINCH** | Thumb tip touches index tip | Thumb-to-index distance < pinch threshold (normalized to hand size) |
| **RELEASE** | Thumb and index separate | Thumb-to-index distance > release threshold (hysteresis — higher than pinch threshold) |
| **WRIST_ROLL** | Pronation / supination of wrist while pinched | Angle of thumb–pinky MCP axis in camera frame relative to PINCH baseline |
| **SWIPE_H** | Fast lateral hand movement (left or right) while pinched | dx velocity > V_threshold in sidebar header zone |
| **SWIPE_V** | Fast vertical hand movement (up or down) while pinched | dy velocity > V_threshold in sidebar item zone |

#### Pinch detection

- **Threshold type:** Normalized — pinch distance as a percentage of the wrist-to-middle-MCP span of the same hand. This adapts to the user's distance from the camera.
- **Hysteresis:** PINCH fires when normalized distance < 20% (configurable); RELEASE fires only when distance > 35%. This prevents rapid flip-flopping.
- **Time-based hold:** Both PINCH and RELEASE must be sustained for ≥5 frames (~167 ms at 30 fps) before the event fires.

#### Gesture requirement table

| ID | Requirement |
|---|---|
| FR-3.1 | System shall detect and track up to 2 hands simultaneously |
| FR-3.2 | Gesture classification shall run at ≥15 fps |
| FR-3.3 | A visual cursor shall reflect the dominant hand position in real time |
| FR-3.4 | The cursor shall change shape to reflect the current mode (HOVER, PINCH, ROTATING, SCALING) |
| FR-3.5 | The status bar shall display the current gesture/mode name as text |
| FR-3.6 | If hand tracking is lost during a drag, the ghost sprite shall freeze at the last known position for 500 ms, then drop in place |
| FR-3.7 | The camera debug overlay (small inset, corner of screen) shall be toggle-able via `Ctrl+D` |

### FR-4: Placement & Manipulation

#### FR-4a: Picking up from the sidebar

| ID | Requirement |
|---|---|
| FR-4a.1 | PINCH over a sidebar item shall attach a semi-transparent ghost sprite to the cursor |
| FR-4a.2 | The ghost sprite shall follow the cursor across the full canvas area |
| FR-4a.3 | RELEASE on the canvas shall place the item at the cursor position |
| FR-4a.4 | The placed item shall auto-select immediately after placement (highlighted ring) |

#### FR-4b: Selection of placed items

| ID | Requirement |
|---|---|
| FR-4b.1 | Exactly one item can be selected at a time. The selected item shows a highlight ring |
| FR-4b.2 | The last dropped item is automatically selected on placement |
| FR-4b.3 | To re-select a different placed item: hover the index fingertip over it for **1 second** (dwell) |
| FR-4b.4 | To deselect: hover over empty canvas for **1 second**, or move the hand into the sidebar zone |

#### FR-4c: Post-placement manipulation (re-drag, rotate, scale)

When the user PINCHes over an already-placed item, the **first dominant motion** determines the operation. Once locked in, the operation persists until RELEASE.

| Operation | Lock-in trigger | Behavior |
|---|---|---|
| **Re-drag** | Horizontal hand displacement (dx) exceeds threshold N first | Item follows cursor; RELEASE drops it at new position |
| **Scale** | Vertical hand displacement (dy) exceeds threshold N first | Move up → item grows; move down → item shrinks. Relative to size at PINCH moment |
| **Rotate** | Wrist roll angle (Δθ) exceeds threshold M° first | Continuous rotation tracking; snaps to nearest 45° increment (snap can be disabled by instructor in config) |

| ID | Requirement |
|---|---|
| FR-4c.1 | Re-drag shall move the item to the RELEASE position |
| FR-4c.2 | Scale shall adjust the item's rendered size proportionally; minimum size = 20% of nominal, maximum = 300% |
| FR-4c.3 | Rotation shall track wrist roll angle continuously with 45° snap-to-grid by default |
| FR-4c.4 | The intent lock-in is determined by whichever of dx, dy, or Δθ first exceeds its respective threshold after PINCH |

#### FR-4d: Returning an item to the sidebar

| ID | Requirement |
|---|---|
| FR-4d.1 | While dragging a placed item (re-drag mode), if the user RELEASES inside the sidebar zone, the item is removed from the canvas |
| FR-4d.2 | The item is not "deleted" — it returns to the catalog; the sidebar count badge for that type decrements |
| FR-4d.3 | A brief visual animation (item flies back to sidebar) shall confirm the return |

#### FR-4e: Overlap handling

| ID | Requirement |
|---|---|
| FR-4e.1 | No collision constraints — items can overlap freely |
| FR-4e.2 | When a placed or dragged item overlaps an existing placed item, both items receive a brief red-tint flash as a soft warning |
| FR-4e.3 | The placement is still allowed after the warning |

### FR-5: Session Management

| ID | Requirement |
|---|---|
| FR-5.1 | `Ctrl+E` shall export the current layout as a PNG: the plan image composited with all placed furniture sprites at their current positions, rotations, and scales |
| FR-5.2 | The export PNG shall be saved automatically to the same folder as the loaded plan image, with the filename `<plan_name>_<YYYYMMDD_HHMMSS>.png` |
| FR-5.3 | A brief on-screen toast notification shall confirm a successful export (filename + path) |
| FR-5.4 | `Ctrl+R` shall clear all placed items and reload the base plan image (reset session) |
| FR-5.5 | `Ctrl+D` shall toggle the camera debug overlay (small inset camera feed with MediaPipe skeleton) |
| FR-5.6 | `Escape` shall quit the application |

---

## 7. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | End-to-end gesture latency (hand move → screen response) < 100 ms |
| NFR-2 | System shall sustain ≥30 fps during normal operation on the target PC |
| NFR-3 | No internet connection required during operation |
| NFR-4 | Setup (calibration + launch) shall take < 5 minutes |
| NFR-5 | The UI shall be readable from 1.5 m away — large fonts (≥24pt equivalent at 1080p), high-contrast icons |
| NFR-6 | False positive gesture rate shall be low enough not to disrupt a 10-minute session |
| NFR-7 | The system shall sustain a 30-minute session without crash or restart |

---

## 8. Coordinate Mapping & Calibration

Because the camera sits atop the 86" screen and looks down-forward at the table, raw camera
coordinates reflect a perspective-distorted view of the interaction zone. A **homography
transform H** maps camera pixel coordinates to screen UI coordinates.

### Calibration plane

Calibration is performed at **30 cm above the table surface** — the nominal hand hover height.
This ensures that when users hold their hands at the expected operating height, mapped
positions correspond accurately to their intended screen positions.

### Calibration flow (once per session setup)

1. The system enters calibration mode and displays a **large animated pulsing circle** at the
   first of 4 corners of the screen (top-left, top-right, bottom-right, bottom-left).
2. The user extends their index finger and holds it at the corresponding position in 3D space
   (~30 cm above the table, at the corner of the interaction zone).
3. The user **pinches** (PINCH gesture) to capture the fingertip position. The system records
   the camera-frame coordinates of the index fingertip.
4. The circle moves to the next corner. Repeat for all 4 points.
5. The system computes `H = cv2.findHomography(camera_points, screen_points)`.
6. All subsequent hand positions are transformed via `cv2.perspectiveTransform(H)`.

The homography persists for the session. Re-run if the camera or table is moved.

---

## 9. UI / UX Layout

```
┌────────────────────────────────────────────────────────────────────┐
│  Urban Park Design Table                    [session: park_01.png] │  ← header bar
├────────────────────────────────────────┬───────────────────────────┤
│                                        │  [ Seat ][ Veg ][ Play ]  │  ← category tabs
│                                        │  ┌────┐                   │     swipe ◄► to cycle
│                                        │  │ 🪑 │ Bench        ²   │
│                                        │  └────┘                   │
│         PARK PLAN CANVAS               │  ┌────┐                   │
│    (imported PNG, letterboxed)         │  │ 🍽️  │ Picnic Table  ⁰  │
│                                        │  └────┘                   │
│    [placed furniture sprites]          │  ┌────┐                   │
│    [selected item: highlight ring]     │  │ 🌳 │ Decid. Tree   ³  │
│    [ghost sprite while dragging]       │  └────┘                   │
│                                        │  ┌────┐                   │
│                                        │  │ 🌲 │ Conifer       ⁰  │
│                                        │  └────┘                   │
│                                        │   ↕ swipe to scroll       │
├────────────────────────────────────────┴───────────────────────────┤
│  ◉ [cursor glyph]   Mode: HOVER   Gesture: —   FPS: 30   [cam▣]  │  ← status bar
└────────────────────────────────────────────────────────────────────┘
```

- **Canvas area**: ~75% of screen width, full height minus header/status bar
- **Sidebar**: ~25% width — category tabs row + scrollable item list with count badges
- **Header**: App title + loaded plan filename
- **Status bar**: Cursor glyph (changes shape per mode), mode text, gesture text, FPS counter, camera overlay indicator

### Cursor states

| Mode | Cursor shape / color |
|---|---|
| HOVER | Open hand outline, green |
| PINCH / DRAG | Closed fist outline, amber |
| ROTATING | Circular arrow arc, amber |
| SCALING | Double-headed vertical arrow, amber |
| DWELL (counting) | Circle progress ring around cursor, fills over 1s |

### Visual theme

Green / nature-themed with earthy tones. Design goals:
- Deep forest green for header and sidebar backgrounds
- Warm sand / parchment for the canvas letterbox background
- High-contrast white text and icon labels
- Selected item highlight: bright lime-green ring
- Overlap warning: brief red-tint flash on affected items
- Ghost sprite during drag: 60% opacity

---

## 10. Interaction State Machine

```
                  ┌─────────────────┐
                  │      IDLE       │  cursor visible, no item held
                  └──────┬──────────┘
          ┌───────────────┤ PINCH in
          │               │ sidebar zone
          │               ▼
          │     ┌──────────────────┐
          │     │  DRAGGING_NEW    │  ghost sprite from sidebar follows cursor
          │     └─────────┬────────┘
          │               │ RELEASE on canvas → place item, auto-select, → IDLE
          │               │ RELEASE in sidebar zone → cancel → IDLE
          │
          │ PINCH in canvas zone (on placed item)
          │               ▼
          │     ┌──────────────────┐
          │     │  PINCH_PENDING   │  waiting for dominant motion
          │     └──┬───────┬───┬───┘
          │   dx>N │  dy>N │   │ Δθ>M°
          │        ▼       ▼   ▼
          │  DRAGGING  SCALING  ROTATING
          │  _PLACED           (wrist roll)
          │        │       │   │
          │        └───────┴───┘
          │               │ RELEASE → update item state → IDLE
          │
          └─── SWIPE_H in sidebar tabs → TAB_SWITCH → IDLE
               SWIPE_V in sidebar items → SCROLL → IDLE
               DWELL 1s on placed item → SELECT item → IDLE
               DWELL 1s on empty canvas → DESELECT → IDLE
               Enter sidebar zone while item selected → DESELECT → IDLE
```

---

## 11. Software Stack

| Layer | Library / Tool | Version target |
|---|---|---|
| Language | Python | 3.10+ |
| Camera capture | OpenCV (`cv2`) | 4.x |
| Hand tracking | MediaPipe `Hands` | 0.10.x, `model_complexity=1` |
| Rendering / UI | Pygame | 2.x |
| Homography | OpenCV `findHomography`, `perspectiveTransform` | (bundled with cv2) |
| Data / config | JSON (stdlib) | — |
| Image export | `pygame.image.save` + Pillow for compositing | — |
| Package mgmt | pip / conda | — |

---

## 12. MVP Scope (v1)

### In scope for v1

- Load PNG/JPEG park plan (any aspect ratio, letterboxed)
- Furniture catalog with category tabs + count badges (PNG sprites available)
- Homography calibration via 4-point fingertip-tap at 30 cm hover height
- PINCH/RELEASE drag-and-drop from sidebar to canvas (ghost sprite during drag)
- Post-placement manipulation: re-drag, rotate (wrist roll, 45° snap), scale (vertical drag)
- Selection model: auto-select on drop, dwell re-select (1s), dwell deselect (1s)
- Return-to-sidebar mechanic (drag placed item into sidebar zone to remove from canvas)
- Soft overlap warning (red flash, placement allowed)
- Sidebar: category tabs (horizontal swipe), item scroll (vertical swipe), count badges
- Sidebar side (left/right) configurable at session start
- 500ms ghost freeze on tracking loss
- Dual-mode debouncing (time-based hold + hysteresis)
- Intent disambiguation: first dominant motion locks re-drag / scale / rotate
- Camera debug overlay (toggle `Ctrl+D`): small inset with MediaPipe skeleton
- Instructor keyboard controls: `Ctrl+E` export, `Ctrl+R` reset, `Ctrl+D` debug, `Escape` quit
- PNG export: auto-saved to plan image folder, timestamped filename, toast notification
- Green/earthy visual theme, mode-aware cursor shapes, status bar

### Deferred to v1.1

- Two-hand rotation (more robust angle tracking)
- JSON save/load session (full layout persistence)
- Undo history (`Ctrl+Z`)
- Grid / snap-to-grid option
- SVG plan support
- Per-type item hard limits

---

## 13. Out of Scope

- 3D rendering or elevation views
- Real-time collaboration (multi-user simultaneous)
- Cloud storage or networked sessions
- BIM / IFC export
- Audio feedback
- Mobile or web deployment
- Touch input (the Optoma 5861RK has touch capability but it is not used)

---

## 14. Open Questions

| # | Question | Owner | Status |
|---|---|---|---|
| OQ-1 | Sidebar side default (left or right) for the first session? | Instructor | Open |
| OQ-2 | Should furniture scale to a real-world reference (e.g. 1 px = 0.5 m)? | Instructor | Open |
| OQ-3 | Exact pinch threshold (% of hand span) and wrist-roll threshold (degrees) — to be tuned during hardware testing | Dev | To tune |
| OQ-4 | Exact frame-hold count for debouncing (default 5 frames = 167 ms) — tune based on feel | Dev | To tune |
| OQ-5 | What is the depth-of-field situation at the camera's distance from hands? Fixed-focus camera at ~1.5–2m — verify focus is sharp at that range | Hardware | Open |

---

## 15. Success Metrics

| Metric | Target |
|---|---|
| A new user can place 3 pieces of furniture within 2 minutes, without instruction | Yes |
| Gesture recognition accuracy (correct intent / total attempt) | ≥ 85% |
| System runs for a 30-min session without crash or restart | Yes |
| Exported PNG is legible and usable as a design artifact | Yes |
| Setup time from power-on to ready-to-use | < 5 min |
| Wrist-roll rotation is detectable and usable in the dim-room, angled-camera setup | Yes (verify in hardware test) |
| Return-to-sidebar mechanic is discoverable without instruction | Yes |
