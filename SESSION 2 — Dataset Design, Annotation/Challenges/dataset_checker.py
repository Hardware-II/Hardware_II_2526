import os
import yaml
import cv2
import random
from collections import defaultdict
import matplotlib.pyplot as plt

# ============================================================================
# NO HARDCODED PATH - YOU'LL BE ASKED TO TYPE IT WHEN YOU RUN THE SCRIPT
# ============================================================================

def get_dataset_path():
    """
    Ask user to input the dataset path via command line.
    
    Returns:
        str: Path to the dataset folder
    """
    print("="*60)
    print("📊 YOLO DATASET VALIDATOR")
    print("="*60)
    print("\nPlease enter the full path to your dataset folder.")
    print("(The folder that contains data.yaml)")
    print("\nExample:")
    print("  /Users/apple/Downloads/Dataset_Labeling_Bounding_Box")
    print("\nOr drag and drop the folder here and press Enter:")
    print("-"*60)
    
    path = input("Dataset path: ").strip()
    
    # Remove quotes if user dragged and dropped (macOS adds quotes)
    path = path.strip('"').strip("'")
    
    return path

def load_yaml(path):
    """
    Load and parse a YAML file.
    
    Args:
        path (str): Path to the YAML file
        
    Returns:
        dict: Parsed YAML content as a dictionary
    """
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def find_images_path(dataset_path, relative_path):
    """
    Intelligently finds the actual location of image folders.
    
    Args:
        dataset_path (str): Base path of the dataset (where data.yaml is)
        relative_path (str): Relative path from data.yaml (e.g., '../train/images')
        
    Returns:
        str: Actual path to images folder, or None if not found
    """
    # STRATEGY 1: Try the path exactly as specified in YAML
    path1 = os.path.normpath(os.path.join(dataset_path, relative_path))
    if os.path.exists(path1):
        return path1
    
    # STRATEGY 2: Remove '../' and look inside the dataset folder
    parts = relative_path.split('/')
    cleaned_parts = [p for p in parts if p != '..']
    path2 = os.path.join(dataset_path, *cleaned_parts)
    if os.path.exists(path2):
        return path2
    
    # STRATEGY 3: Try just the last two parts (e.g., train/images)
    if len(cleaned_parts) >= 2:
        path3 = os.path.join(dataset_path, *cleaned_parts[-2:])
        if os.path.exists(path3):
            return path3
    
    return None

def read_labels(label_path):
    """
    Read YOLO format label file.
    
    Args:
        label_path (str): Path to the .txt label file
        
    Returns:
        list: List of tuples (class_id, x_center, y_center, width, height)
    """
    objects = []
    
    if not os.path.exists(label_path):
        return objects
    
    with open(label_path, 'r') as f:
        for line in f.readlines():
            parts = line.strip().split()
            
            if len(parts) == 5:
                cls, x, y, w, h = parts
                objects.append((
                    int(cls),
                    float(x),
                    float(y),
                    float(w),
                    float(h)
                ))
    
    return objects

def visualize_one_sample(images_path, labels_path, class_names, split_name):
    """
    Display ONE random image from the specified split with bounding boxes.
    
    Args:
        images_path (str): Path to folder containing images
        labels_path (str): Path to folder containing label files
        class_names (list): List of class names for labeling boxes
        split_name (str): Name of the split (train/valid/test) for display
        
    Returns:
        bool: True if successfully visualized, False otherwise
    """
    # Check if images folder exists
    if not os.path.exists(images_path):
        print(f"⚠️ Cannot visualize {split_name}: {images_path} does not exist")
        return False
    
    # Get list of all image files
    imgs = [f for f in os.listdir(images_path) 
            if f.endswith(('.jpg', '.png', '.jpeg'))]
    
    # Check if any images were found
    if not imgs:
        print(f"⚠️ No images found in {split_name}: {images_path}")
        return False
    
    # Randomly select ONE image
    img_name = random.choice(imgs)
    
    # Construct full paths
    img_path = os.path.join(images_path, img_name)
    label_path = os.path.join(
        labels_path, 
        img_name.replace('.jpg', '.txt')
                .replace('.png', '.txt')
                .replace('.jpeg', '.txt')
    )

    # Read the image
    img = cv2.imread(img_path)
    
    if img is None:
        print(f"⚠️ Could not read image: {img_path}")
        return False
    
    # Get image dimensions
    h, w, _ = img.shape

    # Read all labels for this image
    labels = read_labels(label_path)
    
    # Count objects for display
    num_objects = len(labels)

    # Draw each bounding box
    for cls, xc, yc, bw, bh in labels:
        # Convert normalized YOLO coordinates to pixel coordinates
        x1 = int((xc - bw/2) * w)
        y1 = int((yc - bh/2) * h)
        x2 = int((xc + bw/2) * w)
        y2 = int((yc + bh/2) * h)

        # Draw rectangle (green color, thickness 2)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Add class label text above the box
        cv2.putText(
            img, 
            class_names[cls],
            (x1, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    # Display the image
    plt.figure(figsize=(8, 8))
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    plt.title(f"{split_name.upper()} Sample: {img_name}\n({num_objects} object(s) labeled)", 
              fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()
    
    return True

def main():
    """
    Main function that orchestrates the dataset validation process.
    """
    # ========================================================================
    # STEP 1: Get Dataset Path from User Input
    # ========================================================================
    DATASET_PATH = get_dataset_path()
    
    if not DATASET_PATH:
        print("\n❌ No path provided. Exiting.")
        return
    
    # Check if path exists
    if not os.path.exists(DATASET_PATH):
        print(f"\n❌ ERROR: Path does not exist!")
        print(f"   Path entered: {DATASET_PATH}")
        return
    
    print(f"\n✅ Dataset folder: {DATASET_PATH}")
    
    # ========================================================================
    # STEP 2: Show Folder Contents
    # ========================================================================
    print("\n📁 Contents of dataset folder:")
    try:
        for item in os.listdir(DATASET_PATH):
            item_path = os.path.join(DATASET_PATH, item)
            if os.path.isdir(item_path):
                print(f"  📂 {item}/")
            else:
                print(f"  📄 {item}")
    except Exception as e:
        print(f"❌ Error reading folder: {e}")
        return
    
    # ========================================================================
    # STEP 3: Load and Parse data.yaml
    # ========================================================================
    yaml_path = os.path.join(DATASET_PATH, "data.yaml")
    
    if not os.path.exists(yaml_path):
        print(f"\n❌ ERROR: data.yaml not found in {DATASET_PATH}")
        return
    
    data = load_yaml(yaml_path)
    
    print("\n📝 Contents of data.yaml:")
    for key, value in data.items():
        print(f"  {key}: {value}")

    class_names = data["names"]
    print("\n📘 Classes:", class_names)

    # ========================================================================
    # STEP 4: Prepare to Analyze Splits
    # ========================================================================
    stats = defaultdict(int)

    # Build list of available splits
    splits = []
    if "train" in data:
        splits.append(("train", data["train"]))
    if "val" in data:
        splits.append(("val", data["val"]))
    elif "valid" in data:
        splits.append(("valid", data["valid"]))
    if "test" in data:
        splits.append(("test", data["test"]))

    valid_splits = []  # Track which splits were successfully found

    # ========================================================================
    # STEP 5: Process Each Split
    # ========================================================================
    for split_name, relative_path in splits:
        print(f"\n📂 {split_name.upper()}:")
        print(f"  Relative path from YAML: {relative_path}")
        
        img_path = find_images_path(DATASET_PATH, relative_path)
        
        if img_path is None:
            print(f"  ❌ Images directory not found!")
            continue
        
        print(f"  ✅ Found at: {img_path}")
        lbl_path = img_path.replace("images", "labels")
        
        valid_splits.append((split_name, img_path, lbl_path))

        images = [f for f in os.listdir(img_path) 
                  if f.endswith(('.jpg', '.png', '.jpeg'))]
        print(f"  📊 Images found: {len(images)}")

        # Count labels
        for img in images:
            label_file = os.path.join(
                lbl_path, 
                img.replace('.jpg', '.txt')
                   .replace('.png', '.txt')
                   .replace('.jpeg', '.txt')
            )
            
            labels = read_labels(label_file)

            if not labels:
                stats["missing_labels"] += 1

            for obj in labels:
                class_id = obj[0]
                stats[class_names[class_id]] += 1

    # ========================================================================
    # STEP 6: Display Statistics
    # ========================================================================
    print("\n" + "="*60)
    print("📊 OVERALL STATISTICS")
    print("="*60)
    
    print("\n📈 CLASS DISTRIBUTION (across all splits):")
    for k, v in stats.items():
        if k != "missing_labels":
            print(f"  {k}: {v} objects")
    
    if stats.get("missing_labels", 0) > 0:
        print(f"\n⚠️  Missing label files: {stats['missing_labels']}")
    else:
        print(f"\n✅ No missing label files!")

    # ========================================================================
    # STEP 7: Visualize ONE Sample from Each Split
    # ========================================================================
    print("\n" + "="*60)
    print("🖼️  VISUAL SAMPLE CHECK")
    print("="*60)
    print("Showing ONE random image from each split with bounding boxes...\n")
    
    # Visualize one sample from each available split
    for split_name, img_path, lbl_path in valid_splits:
        print(f"📸 Showing sample from {split_name.upper()}...")
        visualize_one_sample(img_path, lbl_path, class_names, split_name)
    
    if not valid_splits:
        print("⚠️ No valid splits found for visualization")
    
    print("\n" + "="*60)
    print("✅ DATASET VALIDATION COMPLETE!")
    print("="*60)

if __name__ == "__main__":
    main()