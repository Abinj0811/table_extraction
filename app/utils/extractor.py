"""
Text extraction module for extracting text from images using AWS Textract.
"""

import os
import cv2
import boto3
from pathlib import Path

class TextExtractor:
    def __init__(self):
        """Initialize the TextExtractor with AWS Textract."""
        self.textract_client = boto3.client("textract")

    # Define the allowed class labels
        self.makers_class_labels = {
            2: "makers", 
            3: "dwg_no", 
            4: "title", 
            5: "mk_name"
        }

    def is_maker_class_file(self, filename):
        """Check if the filename contains any of the maker class labels."""
        # Extract stem from filename
        stem = Path(filename).stem
        
        # Check if any of the maker class labels are in the filename
        for label_value in self.makers_class_labels.values():
            if f"_{label_value}" in stem:
                return True
        return False
        
    def extract_text_with_aws(self, image_path):
        """Extract text with bounding boxes from a single image using AWS Textract."""
        # Read image dimensions using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            print(f"⚠️ Image not found or cannot read: {image_path}")
            return None

        image_height, image_width, _ = image.shape  # Get image dimensions
        print(f"Processing image of size {image_width}x{image_height}: {image_path}")

        # Read image as bytes
        with open(image_path, "rb") as image_file_bytes:
            image_bytes = image_file_bytes.read()

        # Call AWS Textract
        try:
            response = self.textract_client.detect_document_text(Document={"Bytes": image_bytes})
            print(f"AWS Textract response received with {len(response.get('Blocks', []))} blocks")
        except Exception as e:
            print(f"❌ Textract failed for {image_path}: {str(e)}")
            return None

        # Extract text with bounding box details
        extracted_data = {"text_lines": []}
        line_count = 0

        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":  # Extract text line by line
                line_count += 1
                bbox = block["Geometry"]["BoundingBox"]

                # Convert normalized values to float pixel coordinates
                x_min = bbox["Left"] * image_width
                y_min = bbox["Top"] * image_height
                x_max = (bbox["Left"] + bbox["Width"]) * image_width
                y_max = (bbox["Top"] + bbox["Height"]) * image_height

                # Define the polygon (clockwise order)
                polygon = [
                    [x_min, y_min],  # Top-left
                    [x_max, y_min],  # Top-right
                    [x_max, y_max],  # Bottom-right
                    [x_min, y_max]   # Bottom-left
                ]

                extracted_data["text_lines"].append({
                    "polygon": polygon,
                    "confidence": block["Confidence"],
                    "text": block["Text"],
                    "bbox": [x_min, y_min, x_max, y_max]  # Bounding box in float pixel format
                })

        print(f"✅ AWS Textract extracted {line_count} text lines from: {image_path}")
        
        # Debug - print the first few text lines if available
        if extracted_data["text_lines"]:
            print("Sample of extracted text:")
            for i, line in enumerate(extracted_data["text_lines"][:3]):
                print(f"  Line {i+1}: '{line['text'][:30]}...' at {line['bbox']}")
        else:
            print("⚠️ No text lines were extracted!")
            
        return extracted_data
        

    def process_images(self, folder_path_map):
        extracted_data_map = {}

        for main_image, (folder_path, image_paths) in folder_path_map.items():
            extracted_data_map[main_image] = []

            for image_path in image_paths:
                if not isinstance(image_path, str):  # Check if image_path is a valid string
                    print(f"⚠️ Skipping invalid image path: {image_path} ({type(image_path)})")
                    continue  # Skip invalid paths

                extracted_data = self.extract_text_with_aws(image_path)
                if extracted_data:
                    extracted_data_map[main_image].append(extracted_data)

        return extracted_data_map
    
    def process_each_image(self, detection_path):
        extracted_map_data = {}

        for img in detection_path:
            extracted_data = self.extract_text_with_aws(img)
            if extracted_data:
                extracted_map_data[img] = extracted_data

        return extracted_map_data
