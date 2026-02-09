# Session 03 – YOLO + ROS2 Vision Challenge

In this session, students work with **YOLO object detection** and integrate it with **ROS2**.
The goal is to understand the full workflow from setup to deployment and debugging.

---

## 🧩 Tasks

### Task 1 – Install ROS2 via WSL
- Install Ubuntu using Windows Subsystem for Linux (WSL)
- Install ROS2
- Verify the installation with basic ROS2 commands

---

### Task 2 – Train YOLO with Roboflow
- Choose or create a dataset in Roboflow
- Export the dataset in YOLO format
- Train a YOLO model
- Check training results and basic metrics

---

### Task 3 – Model Testing
Test your trained model on:
- Images
- Videos
- Webcam (live camera)

Observe detection accuracy and performance.

---

### Task 4 – Debugging & Failure Analysis
Spend dedicated time analyzing failure cases:
- Lighting conditions
- Occlusion
- Distance and scale issues

Try to identify **why** the model fails and how it could be improved.

---

### Task 5 – Deployment
Run YOLO in one of the following ways:
- As a standalone Python script
- As a ROS2 node

(Optional) Publish detection results as a ROS2 topic.

---

## ✅ Deliverables
- Trained YOLO model
- Working inference on at least one input type
- Short notes on failure cases and debugging observations

---

## 🎯 Session Goal
Understand how a vision model is trained, tested, debugged, and integrated
into a ROS2-based robotics workflow.
