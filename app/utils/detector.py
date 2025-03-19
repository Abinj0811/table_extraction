

"""
Unified detection module for identifying and extracting tables and document components from images.
"""
import os
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from app.utils.preprocessor import ImageProcessor

class TableDetector:
    def __init__(self, table_model_path, makers_model_path):
        """Initialize with both table and makers detection models."""
        self.table_model = YOLO(table_model_path)
        self.makers_model = YOLO(makers_model_path)
        self.makers_class_names = self.makers_model.names
        self.preprocess_image = ImageProcessor()
        
        # Define class mappings for makers model
        self.makers_class_labels = {
            2: "makers",
            3: "dwg_no",
            4: "title",
            5: "mk_name"
        }
        
    @staticmethod
    def iou(box1, box2):
        """Compute Intersection over Union (IoU) between two bounding boxes."""
        x1, y1, x2, y2 = max(box1[0], box2[0]), max(box1[1], box2[1]), min(box1[2], box2[2]), min(box1[3], box2[3])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area_box1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area_box2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area_box1 + area_box2 - intersection
        return intersection / union if union > 0 else 0
    
    def detect_tables(self, image_path):
        """Detect tables in an image using the table model."""
        print(f"\nDetecting tables in: {image_path}")
        
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Failed to load image {image_path}")
            return []
        
        results = self.table_model(image)
        
        detected_tables = []
        for box, cls, conf in zip(results[0].boxes.xyxy.cpu().numpy(),
                                 results[0].boxes.cls.cpu().numpy(),
                                 results[0].boxes.conf.cpu().numpy()):
            if int(cls) in [0, 1]:  # Assuming classes 0 and 1 are tables
                detected_tables.append((box, float(conf)))
        
        # Sort and filter overlapping tables
        detected_tables.sort(key=lambda x: x[1], reverse=True)
        selected_tables = []
        for box, conf in detected_tables:
            if all(self.iou(box, selected_box) <= 0.8 for selected_box, _ in selected_tables):
                selected_tables.append((box, conf))
        
        # Crop tables
        cropped_tables = []
        for box, _ in selected_tables:
            x1, y1, x2, y2 = map(int, box)
            cropped_image = image[y1:y2, x1:x2]
            if cropped_image.size > 0:
                cropped_tables.append((cropped_image, box))
        
        return cropped_tables
    
    def detect_makers_components(self, image_path):
        """Detect makers, dwg_no, title, and mk_name in an image."""
        print(f"\nDetecting components in: {image_path}")
        
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Failed to load image {image_path}")
            return []
        
        results = self.makers_model(image)
        
        detected_items = []
        detected_classes = set()
        
        for box, cls, conf in zip(results[0].boxes.xyxy.cpu().numpy(),
                                 results[0].boxes.cls.cpu().numpy(),
                                 results[0].boxes.conf.cpu().numpy()):
            cls = int(cls)
            
            if cls not in self.makers_class_labels:
                continue  # Skip unwanted classes
            
            class_name = self.makers_class_labels[cls]
            
            detected_items.append((box, cls, float(conf)))
            detected_classes.add(f"{cls}: {class_name}")
        
        if detected_classes:
            print(f"Detected classes: {', '.join(detected_classes)}")
        else:
            print(f"No valid detections found")
        
        # Sort by confidence and filter overlapping boxes
        detected_items.sort(key=lambda x: x[2], reverse=True)
        selected_items = []
        for box, cls, conf in detected_items:
            if all(self.iou(box, selected_box) <= 0.8 for selected_box, _, _ in selected_items):
                selected_items.append((box, cls, conf))
        
        # Crop components
        cropped_components = []
        for box, cls, conf in selected_items:
            x1, y1, x2, y2 = map(int, box)
            cropped_image = image[y1:y2, x1:x2]
            
            if cropped_image.size > 0:
                class_name = self.makers_class_labels.get(cls, f"class_{cls}")
                cropped_components.append((cropped_image, box, class_name))
        
        return cropped_components
    
    def rot_img(self, image_path):
        read_img = cv2.imread(image_path)
        self.preprocess_image.detect_and_rotate_if_landscape(read_img, image_path)
        

    def process_image(self, image_path):
        """Process an image for both tables and makers components."""
        print(f"Processing image: {image_path}")
        
        # Create output folder structure
        parent_folder = Path(image_path).parent
        filename = Path(image_path).stem
        output_folder = os.path.join(parent_folder, filename)
        Path(output_folder).mkdir(parents=True, exist_ok=True)

        self.rot_img(image_path)
        
        # Detect and save tables
        cropped_tables = self.detect_tables(image_path)
        saved_tables = []
        for idx, (table_img, _) in enumerate(cropped_tables):
            table_path = os.path.join(output_folder, f"{filename}_table{idx+1}.png")
            cv2.imwrite(table_path, table_img)
            self.rot_img(table_path)
            saved_tables.append(table_path)
            print(f"✔ Saved table: {table_path}")
        
        # Detect and save makers components
        cropped_components = self.detect_makers_components(image_path)
        saved_components = []
        for comp_img, _, class_name in cropped_components:
            comp_path = os.path.join(output_folder, f"{filename}_{class_name}.png")
            cv2.imwrite(comp_path, comp_img)
            self.rot_img(comp_path)
            saved_components.append(comp_path)
            print(f"✔ Saved component: {comp_path}")
        
        return {
            'output_folder': output_folder,
            'tables': saved_tables,
            'components': saved_components
        }
    
    def process_folder(self, main_folder):
        """Process all images in a folder for tables and makers components."""
        print(f"Scanning folder: {main_folder}\n")
        
        results = {}
        for root, _, files in os.walk(main_folder):
            for file in files:
                if file.endswith((".jpg", ".jpeg", ".png")):
                    image_path = os.path.join(root, file)
                    results[image_path] = self.process_image(image_path)
                    
                    for png_file in results[image_path]['tables'] + results[image_path]['components']:
                        if png_file.endswith(".png"):
                            self.rot_img(png_file)
                        

        return results
    

# tab = TableDetector("app/models/best_tables.pt", "app/models/best_makers.pt")
# tab.process_image("app/images/page_004.jpg")
# tab.rot_img("app/images/page_004.jpg")