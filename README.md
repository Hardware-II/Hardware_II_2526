# HARDWARE II: Applied Computer Vision & Robotics with AI  
*Applied Computer Vision & Robotics for Architecture and Interactive Systems*

This repository contains all course materials, session notes, and project guidelines for **HARDWARE II**, giving students hands-on experience in **Computer Vision, AI model training, YOLO deployment, OpenCV, ONNX, and ROS2 integration** for robotics applications. Ethical AI, spatial intelligence, and independent project development are emphasized throughout the course.

---

## 🔧 Core Technology Stack
- **Roboflow** – Dataset management and annotation  
- **YOLO** – Real-time object detection framework  
- **OpenCV** – Image processing and geometry operations  
- **Python** – Main development language  
- **ONNX** – Model optimization and deployment  
- **ROS2** – Robot Operating System  
- **Camera Nodes, AI Inference Nodes, Robot/Arduino Control Nodes**

---

## 📅 Sessions Overview

### **SESSION 1 — Computer Vision & AI System Foundations**
**Goal:** Establish foundational understanding of computer vision and AI pipeline, including ethical considerations in architecture and public space.  
**Topics Covered:**
- Computer Vision basics, Pixels, FPS, Resolution
- Machine Learning vs Deep Learning, CNNs
- Classification, Detection, Segmentation
- YOLO introduction and real-time detection
- Ethical AI and bias considerations
- Full system pipeline: Camera → Dataset → Training → Inference → Robot/Actuator

---

### **SESSION 2 — Dataset Design & Annotation**
**Goal:** Learn how high-quality data drives AI performance.  
**Topics Covered:**
- Dataset concepts, annotation principles, and class design
- Bias, imbalance, and overfitting
- Data augmentation
- Ethical implications in data collection
- Dataset versioning and YOLO export

---

### **SESSION 3 — YOLO Training + ROS2 Perception Preview**
**Goal:** Train AI models and understand integration with ROS2 robotics.  
**Topics Covered:**
- Training vs Inference, Epoch, Loss, mAP
- Precision & Recall, detection errors
- ROS2 introduction: Nodes, Topics, Message flow
- YOLO model deployment as standalone script or ROS2 node
- Debugging lighting, occlusion, and failure cases

---

### **SESSION 4 — OpenCV, Tracking & Spatial Intelligence**
**Goal:** Convert detections into real-world, measurable spatial intelligence.  
**Topics Covered:**
- Image coordinate systems and bounding box geometry
- Object tracking and ID assignment
- Distance and speed estimation
- Perspective correction and homography for spatial mapping
- Publishing spatial data to screen or ROS2 topic

---

### **SESSION 5 — Deployment, ONNX & Full System Integration**
**Goal:** Deploy a complete, autonomous AI system.  
**Topics Covered:**
- Deployment concepts, ONNX, Edge AI vs Cloud AI
- Model size vs speed tradeoff
- Full pipeline: AI → ROS2 → Robot/Actuator
- YOLO to ONNX conversion and inference
- Integration with ROS2 nodes or Arduino/Robot controllers
- System performance metrics (FPS, latency, accuracy)

---

### **Post-Session 5 — Independent Project Work**
**Goal:** Apply all knowledge to design and implement a full AI/robotics system.  
**Deliverables:**
- Fully integrated system: YOLO model, ONNX deployment, real-time inference connected to ROS2 or Arduino
- Documentation: system diagram, metrics, design reflections
- Demonstration (live or recorded)
- Optional integration with Grasshopper or Unity for interactive installations

**Final Project Requirements:**
- Real-time detection
- Custom dataset and trained AI model
- Quantitative outputs (distance, speed, count, density)
- Physical or interactive response
- Integration with ROS2 or Arduino

---
