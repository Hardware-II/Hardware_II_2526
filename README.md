# G.R.A.S.S.
### Gesture-Responsive Architecture for Spatial Staging

*An interactive urban park design table — no mouse, no keyboard, no touch.*

---

## What is it?

G.R.A.S.S. is a hands-free design installation that lets anyone compose an urban park layout using only mid-air hand gestures and voice commands. An overhead camera watches the interaction zone; a large display shows the result in real time.

The goal is to make spatial design **accessible to non-specialists** — if you can point and grab, you can design a park. No CAD skills required.

---

## The Experience

A user stands in front of an 86" satellite map of any location in the world. They reach toward the screen, pinch a bench from the sidebar, drag it onto the park, rotate it to face the path, scale it down, and drop it. They say *"go to Park Güell"* and the map instantly flies to Barcelona. They close their fist and scroll through the vegetation catalog. The whole session takes a few minutes and ends with a one-keystroke PNG export.

---

## Hardware Setup

```
┌──────────────────────────────────────────┐
│   Trust GXT 1160 Vero — 1080p @ 30fps   │  ← mounted on top of the display
└──────────────────┬───────────────────────┘        looking down at the table
                   │ USB
┌──────────────────▼───────────────────────┐
│         PC — Python application          │
└──────────────────┬───────────────────────┘
                   │ HDMI
┌──────────────────▼───────────────────────┐
│     Optoma 5861RK — 86" 4K display      │  ← full-bleed satellite map
└──────────────────────────────────────────┘
                   ▲
          users stand here
    ┌──────────────────────────┐
    │  Interaction zone        │  1957 × 1171 mm desk
    │  hands hover 10–30 cm   │  above the surface
    └──────────────────────────┘
```

| Component | Details |
|---|---|
| Camera | Trust GXT 1160 Vero — 1920×1080, 30 fps, USB, mounted on top of display |
| Display | Optoma 5861RK — 86", 4K UHD (application renders at 1536×864 logical px) |
| Map | Mapbox Satellite — live tile streaming, any location on Earth |
| Microphone | Trust USB Microphone, Google Speech API recognition |

---

## Calibration

At startup the system runs a **4-point homography calibration** that maps the camera's angled perspective view to screen coordinates. Four corner targets appear one at a time; the user pinches at each corner (~30 cm above the table surface). The homography is computed and persists for the session.

Press **Space** to skip calibration (uses a saved mapping from the previous session).

---

## Gesture Vocabulary

All interaction is done with one or two bare hands — no gloves, markers, or controllers.

### Single hand

| Gesture | Motion | Action |
|---|---|---|
| **Hover** | Open hand, index extended | Move cursor |
| **Pinch** | Thumb tip meets index tip | Grab / select |
| **Drag** | Pinch + move horizontally | Move a placed item |
| **Scale** | Pinch + move vertically | Up = grow · Down = shrink |
| **Rotate** | Pinch + roll wrist | Rotates item · Snaps to 45° |
| **Dwell** | Hold cursor still for 1 s | Select / deselect an item |
| **Fist** | Curl all four fingers | Scroll the sidebar up/down |
| **Swipe** | Fast lateral sweep in tab row | Switch furniture category |

### Two hands

| Gesture | Motion | Action |
|---|---|---|
| **Two-hand pinch + spread** | Both hands pinched, move apart | Zoom in |
| **Two-hand pinch + close** | Both hands pinched, move together | Zoom out |
| **Two-hand pinch + translate** | Both hands pinched, move together | Pan the map |

---

## Furniture Catalog

24 items across 6 categories, drag-and-dropped onto the live satellite map.

| Category | Items |
|---|---|
| **Seating** | Bench, Picnic Table, Lounger, Curved Bench |
| **Vegetation** | Deciduous Tree, Conifer, Shrub, Flower Bed, Flowering Tree |
| **Play** | Swing Set, Slide, Climbing Frame, Sandbox, Seesaw, Rocker |
| **Lighting** | Lamp Post, Solar Bollard |
| **Water** | Fountain, Drinking Station, Pond |
| **Services** | Waste Bin, Bike Rack, Info Board |

Each item shows a **count badge** so you can see at a glance how many of each type are on the map.

---

## Voice Commands

All commands are spoken naturally — no wake word needed.

### Map navigation

| Say | Result |
|---|---|
| *"go to Central Park"* | Instant jump — no API call |
| *"go to Park Güell"* | Instant jump to Barcelona |
| *"go to Ciutadella"* | Instant jump to Barcelona |
| *"go to Montjuïc"* | Instant jump to Barcelona |
| *"go to Paris"* | Geocoded via Mapbox |
| *"zoom in"* / *"closer"* | Zoom in one level |
| *"zoom out"* / *"further"* | Zoom out one level |

**37 famous parks** are resolved instantly from a local lookup table (no internet latency), including parks worldwide and all major parks in Barcelona.

### Item placement & manipulation

| Say | Result |
|---|---|
| *"place a bench"* | Queues a bench to be dropped |
| *"place a flowering tree"* | Queues a flowering tree |
| *"rotate 45"* | Rotates selected item 45° |
| *"scale 1.5"* | Scales selected item to 1.5× |
| *"undo"* / *"remove"* | Removes last placed item |
| *"reset"* / *"clear all"* | Clears all placed items |
| *"save"* / *"export"* | Exports layout as PNG |

---

## Placing and Manipulating Items

### Grab from sidebar
1. Move hand over sidebar — the sidebar floats over the right edge of the map
2. **Pinch** over a furniture item — a semi-transparent ghost sprite attaches to your finger
3. Drag onto the map
4. **Release** (open fingers) to drop

### Manipulate a placed item
1. **Dwell** (hover still for 1 s) over a placed item to select it
2. **Pinch** on the selected item — the first dominant movement locks the mode:
   - Horizontal movement → **Drag**
   - Vertical movement → **Scale** (up = grow, down = shrink)
   - Wrist roll → **Rotate** (snaps to 45°)
3. Release to confirm

### Return to catalog
While dragging a placed item, release inside the sidebar — the item is removed from the map and the count badge decrements.

---

## Map

The map is a live Mapbox Satellite feed. Tiles are pre-fetched in parallel (8 threads) during calibration so the map is fully loaded before interaction starts. Panning and zooming continuously fetch adjacent tiles in the background.

Items placed on the map are **anchored to geographic coordinates** — they stay pinned to the correct lat/lon position when you pan or zoom.

---

## Keyboard Shortcuts (Facilitator)

| Shortcut | Action |
|---|---|
| `Space` | Skip calibration (auto-mapping) |
| `Ctrl+E` | Export current layout as PNG |
| `Ctrl+R` | Reset session (clear all items) |
| `Ctrl+D` | Toggle camera debug overlay |
| `Ctrl+M` | Open map location dialog |
| `Ctrl+C` | Re-run calibration |
| `+` / `-` | Zoom in / out |
| `Escape` | Quit |

---

## Technical Architecture

```
Camera (30 fps)
    │
    ▼
MediaPipe HandLandmarker          ← 21 landmarks per hand, up to 2 hands
    │
    ▼
Homography Transform              ← 4-point calibration, corrects perspective
    │
    ▼
Gesture Recognizer                ← Pinch / fist / velocity — with hysteresis
    │
    ▼
Interaction Controller            ← State machine: IDLE / DRAGGING / ROTATING / SCALING
    │
    ▼
Renderer (Pygame)                 ← Map full-bleed + sidebar overlay + items
    │
    ▼
86" Display
```

### Key implementation details

- **Two-thread camera**: capture thread feeds a 1-slot queue; MediaPipe thread always processes the freshest frame — prevents lag accumulation
- **8 parallel tile fetchers** with TCP connection pooling (requests.Session per thread)
- **LIFO + center-out tile queue**: visible center tiles load first, edges fill in around them
- **EMA cursor smoothing** (α = 0.85): reduces jitter without adding lag
- **Fist detection**: avg fingertip-to-MCP distance normalized to hand size, with hysteresis
- **Known parks lookup**: 37 parks bypass geocoding for instant jumps

---

## Running the Application

```bash
python main.py
```

On first launch a file picker appears — select a park plan PNG/JPEG as the base image, or press Cancel to use only the satellite map.

### Configuration (`config.json`)

Key parameters — no code change needed:

```json
{
  "camera_index": 1,
  "mapbox_lat": 41.3851,
  "mapbox_lon": 2.1734,
  "mapbox_zoom": 18,
  "voice_mic_index": 1,
  "cursor_smooth_alpha": 0.85,
  "drag_lock_threshold_px": 28,
  "manipulation_hold_ms": 300
}
```

---

## Software Stack

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| UI & rendering | Pygame 2.6 |
| Hand tracking | MediaPipe HandLandmarker Tasks API |
| Map tiles | Mapbox Styles API (Satellite v9) |
| Voice recognition | Google Speech API (SpeechRecognition + PyAudio) |
| Camera capture | OpenCV 4.x |
| Coordinate mapping | OpenCV homography (findHomography + perspectiveTransform) |

---

## Project Context

Developed at **IAAC (Institute for Advanced Architecture of Catalonia)** as a final project for the *Programming for Hardware* course. The installation is designed for classroom and workshop use — participatory urban design made accessible to anyone, regardless of technical background.

> *"Anyone who can point and grab can design a park."*
