#utils/table_detection.py

import os
from ultralytics import YOLO

class TableDetection:
    def __init__(self, model_path: str):
        # Initialize YOLO model with the provided model path
        self.model = YOLO(model_path)

    def detect_tables_in_image(self, image_path: str, conf_thresh: float = 0.5):
        """
        Run YOLO table detection on a single image and return bounding boxes.
        Each bounding box could be in the form of a tuple or dict with (x, y, width, height).
        """
        # Load the image using your preferred method (e.g., OpenCV, PIL)
        image = self._load_image(image_path)
        if image is None:
            print(f"Error: Could not load image at {image_path}")
            return []

        # Run table detection with the YOLO model
        results = self.model(image)
        bbox_tensor = results[0].boxes
        table_boxes = []

        for i in range(bbox_tensor.xyxy.shape[0]):  # Loop over the number of bounding boxes
            xmin, ymin, xmax, ymax = bbox_tensor.xyxy[i].tolist()  # Extract bounding box coordinates
            confidence = bbox_tensor.conf[i].item()  # Extract confidence score
            label = int(bbox_tensor.cls[i].item())  # Extract class label # Extract bbox coordinates, confidence, and label
            
            # Only process the bounding box if the confidence is greater than the threshold
            if confidence >= conf_thresh:
                
                table_boxes.append(
                    {
                        'xmin': xmin,
                        'ymin' : ymin,
                        'xmax' : xmax,
                        'ymax' : ymax
                    }
                )
        
        return table_boxes

    def detect_tables_in_directory(self, images_dir: str, conf_thresh: float = 0.5):
        """
        Run table detection on all images in a directory and return a dictionary
        mapping image filenames to their detected table bounding boxes.
        """
        detected_tables = {}
        image_files = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
        sorted_image_files = sorted(
            image_files,
            key=lambda x: int(os.path.basename(x).split('_')[-1].split('.')[0])
        )
        
        for image_file in sorted_image_files:
            image_path = os.path.join(images_dir, image_file)

            # Detect tables in the current image
            table_boxes = self.detect_tables_in_image(image_path, conf_thresh)
            
            # Store the results in the dictionary
            detected_tables[image_path] = table_boxes
        
        return detected_tables

    @staticmethod
    def _load_image(image_path):
        import cv2
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Unable to load image at {image_path}")
        return image