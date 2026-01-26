Roboflow & YOLO Dataset Preparation Notes
=========================================

This document summarizes key steps and principles for preparing datasets for object detection using Roboflow and YOLO format.

1. Image Upload via Roboflow
----------------------------
- Go to https://roboflow.com and create a free account.
- Create a new project and select the appropriate project type (e.g., Object Detection).
- Upload your images. Supported formats: JPG, PNG, etc.
- Ensure images are clear and representative of the objects you want to detect.

2. Bounding Box Annotation
--------------------------
- Annotate objects in each image using Roboflow’s annotation tool.
- Draw bounding boxes tightly around each object.
- Assign correct labels to each object.
- Check annotations carefully — incorrect labels reduce model accuracy.

3. Data Augmentation Principles
-------------------------------
- Apply augmentation to increase dataset variety and robustness.
- Common augmentations:
  - Flipping (horizontal/vertical)
  - Rotation and shearing
  - Brightness/contrast adjustments
  - Scaling and cropping
  - Adding noise or blur
- Avoid excessive augmentation that changes the object identity.

4. Dataset Versioning
--------------------
- Create a new version of your dataset whenever:
  - You add new images
  - You correct annotations
  - You apply new augmentations
- Versioning helps track changes and maintain reproducibility.

5. Export for YOLO Format
-------------------------
- After finalizing annotations, export your dataset in YOLO format.
- YOLO format includes:
  - Images folder
  - Labels folder (text files with bounding box coordinates)
  - Classes file (list of object labels)
- Download the exported dataset to use for training YOLO models.

6. Best Practices
-----------------
- Keep a balanced dataset across all classes.
- Review annotations for accuracy before export.
- Use versioning to avoid losing previous datasets.
- Start with a small dataset for testing before full training.

Instructor:
-----------
Hamid Peiro
Computational Design · Robotics · Digital Fabrication
