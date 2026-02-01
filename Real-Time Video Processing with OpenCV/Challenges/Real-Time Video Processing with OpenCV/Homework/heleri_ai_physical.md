# AI + Physical Interface Project  
**Student:** Heleri Koltsin  
**Course:** Hardware II  
**Project Title:** Reed Logic – AI-guided Material Ribbing for Robotic Fabrication

---

## 1. Application Domain
**Robotics / Architecture**

The project sits at the intersection of robotic fabrication and architectural material research, focusing on AI-assisted decision-making for working with natural, non-standardized materials.

---

## 2. Problem Statement
Natural materials such as reed vary significantly in diameter, surface condition, and structural nodes.  
Manual processing of these materials for architectural or fabrication purposes is time-consuming and imprecise.

The goal of this project is to develop an AI-assisted system that analyzes reed stems and automatically generates robotic cutting instructions, ensuring that material processing is adapted to the geometry and internal structure of each individual stem.

---

## 3. AI Detection
The AI system performs **instance segmentation of reed stems** using a custom-trained computer vision model.

From the segmentation output, the system:
- Identifies individual reed stems
- Estimates stem diameter along its length
- Detects structural nodes (internodes vs. node areas) either through learned detection or classical computer vision techniques
- Defines usable internode regions where cutting is allowed

The AI outputs geometric data describing:
- Internode boundaries
- Local stem diameter per internode
- A suitability score for robotic processing

---

## 4. Physical Interface / Actuator
A **UR industrial robot** is used as the physical actuator.

Based on the AI output, the robot:
- Receives generated toolpaths for each reed stem
- Cuts **vertical ribs only within internode regions**, avoiding structural nodes
- Adjusts the number of ribs per internode based on the estimated stem diameter
- Executes cutting paths using a linear tool motion (e.g., blade, rotary cutter, or milling tool)

Communication between the AI system and the robot is handled via:
- Python-based toolpath generation
- URScript commands sent through a TCP socket or RTDE interface

---

## 5. Additional Notes / Ideas
- The system supports a fixed overhead camera setup calibrated to the robot workspace.
- Pixel-to-millimeter scaling is obtained via calibration markers placed on the work surface.
- The project can be extended toward material classification, quality assessment, or adaptive fabrication strategies.
- The workflow bridges Studio material research with robotic fabrication, allowing AI to mediate between natural material logic and industrial processes.

