# Session 04 – Multi-Object Detection, Tracking, and Spatial Analysis

In this session, students work on **detecting and tracking multiple objects**, 
calculating real-world measurements using **homography**, and publishing spatial data 
through ROS2 or visual output.

---

## 🧩 Tasks

### Task 1 – Detect & Track Multiple Objects
- Extend YOLO or another detection model to track multiple objects
- Implement a tracking algorithm (e.g., DeepSORT, SORT, or OpenCV trackers)
- Test on images, videos, and live webcam feed

---

### Task 2 – Implement Homography for Real-World Measurements
- Calibrate a planar surface using known reference points
- Compute homography to map image coordinates to real-world coordinates
- Extract metrics:
  - Object distance and speed
  - Area or density of objects within the calibrated region

---

### Task 3 – Publish Spatial Data
- Publish calculated metrics to:
  - Screen / console for visualization
  - ROS2 topics for further robotic processing
- Ensure data is updated in real-time if using live feed

---

### Task 4 – Debugging & Analysis
- Check tracking consistency and accuracy
- Verify homography calculations against known measurements
- Identify failure cases (e.g., occlusion, perspective errors, overlapping objects)
- Suggest improvements or refinements

---

## ✅ Deliverables
- Working multi-object detection and tracking script or ROS2 node
- Homography-based calculations for distance, speed, and density
- Published spatial data (screen or ROS2 topic)
- Short notes on debugging and observed limitations

---

## 🎯 Session Goal
Students will learn how to combine **detection, tracking, and geometric mapping** 
to extract real-world metrics and integrate them into ROS2 workflows.


Instructor:
-----------
Hamid Peiro
Computational Design · Robotics · Digital Fabrication
