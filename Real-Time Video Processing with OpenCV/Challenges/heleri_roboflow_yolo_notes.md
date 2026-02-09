# Roboflow & YOLO Dataset Preparation Notes
**Student:** Heleri Koltsin  
**Course:** Hardware II  
**Project:** Reed Logic – Object Detection Dataset

---

## Image Upload via Roboflow
Images of reed bundles and individual reed stems were uploaded to Roboflow to create an object detection dataset.  
The images represent natural material variation in diameter, texture, and structural nodes.

Total images used: **51**

---

## Bounding Box Annotation
All images were manually annotated using Roboflow’s annotation tool.

- Annotation type: **Bounding Boxes**
- Class used: `reed_stem`
- Bounding boxes were drawn tightly around individual reed stems
- Not all stems were annotated per image to avoid visual clutter and redundancy

Manual annotation was preferred over automatic labeling to ensure accuracy on natural, irregular materials.

---

## Data Augmentation Principles
To improve dataset robustness, a second dataset version was generated with moderate augmentations:

- Brightness and contrast adjustments
- Small rotations
- Minor scaling

Augmentations were kept minimal to preserve the physical identity of the reed material.

---

## Dataset Versioning
Two dataset versions were created:

- **v1_bbox** – manually annotated bounding boxes without augmentation
- **v2_augmented** – augmented version used for YOLO export

Versioning allows comparison and reproducibility of dataset changes.

---

## Export for YOLO Format
The final dataset was exported in **YOLOv8 format**, including:

- `images/` folder
- `labels/` folder with normalized bounding box annotations
- `data.yaml` defining classes and dataset paths

The exported dataset is ready for training a YOLO object detection model.

---

## Notes
This dataset is intended to support future AI-assisted robotic fabrication workflows, where detected reed stems inform toolpath generation and material processing decisions.

The YOLO dataset was exported locally as a ZIP file and is available upon request.

