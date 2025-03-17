"""
Table processing module for converting extracted text into structured tables.
"""

import os
import cv2
import numpy as np
import tensorflow as tf
import pandas as pd
from pathlib import Path
from app.utils.custom_ocr import Custom_OCR

DEFAULT_SIMILARITY_PERCENTAGE = 90
DETECTION_OUTPUT = "./app/detection_out"

class Table_Processor(Custom_OCR):
    def __init__(self, similarity_percentage=DEFAULT_SIMILARITY_PERCENTAGE):
        """Initialize the TableProcessor."""
        self.similarity_percentage = similarity_percentage
        # self.removal_percentage = removal_percentage
        super().__init__() 

    def table_structure(self, extracted_data):
        """Extract text, bounding boxes, and confidence scores from the extracted data."""
        texts = [entry["text"] for entry in extracted_data["text_lines"]]
        boxes = [entry["bbox"] for entry in extracted_data["text_lines"]]
        probabilities = [entry["confidence"] for entry in extracted_data["text_lines"]]

        return boxes, texts, probabilities

    def intersection(self, box_1, box_2):
        """Compute the intersection of two boxes."""
        return [box_2[0], box_1[1], box_2[2], box_1[3]]

    def iou(self, box_1, box_2):
        """Compute Intersection over Union between two boxes."""
        x_1 = max(box_1[0], box_2[0])
        y_1 = max(box_1[1], box_2[1])
        x_2 = min(box_1[2], box_2[2])
        y_2 = min(box_1[3], box_2[3])

        inter = abs(max((x_2 - x_1, 0)) * max((y_2 - y_1), 0))
        if inter == 0:
            return 0

        box_1_area = abs((box_1[2] - box_1[0]) * (box_1[3] - box_1[1]))
        box_2_area = abs((box_2[2] - box_2[0]) * (box_2[3] - box_2[1]))

        return inter / float(box_1_area + box_2_area - inter)
    
    def merge_columns(self, df):
        """
        Merge or remove columns based on similarity percentage, ignoring blank data cells.
        :param df: Input DataFrame.
        :return: Modified DataFrame and merged column pairs.
        """
        merged_columns_info = []  # Track merged column pairs
        column_names = list(df.columns)  # Keep track of column names dynamically
        i = len(column_names) - 2
        
        while i >= 0:  # Iterate dynamically from right to left over adjacent columns
            col1 = column_names[i]  # Left column
            col2 = column_names[i + 1]  # Right column
            
            # Count non-blank cells in both columns for comparison
            valid_rows = df[[col1, col2]].notna().all(axis=1)
            total_non_blank = valid_rows.sum()
            
            if total_non_blank == 0:
                print(f"No valid data for comparison between '{col1}' and '{col2}', skipping.")
                i -= 1
                continue
            
            # Calculate similarity percentage only on rows where both values are present
            filtered_df = df[valid_rows]
            match_count = sum(
                str(val1).strip() == str(val2).strip()
                for val1, val2 in zip(filtered_df[col1], filtered_df[col2])
            )
            
            similarity = (match_count / total_non_blank) * 100 if total_non_blank > 0 else 0
            print(f"Similarity between '{col1}' and '{col2}': {similarity:.2f}%")
            
            # Remove the mismatch check and base decision purely on similarity percentage
            if similarity >= self.similarity_percentage:
                print(f"Merging '{col2}' into '{col1}' (Similarity: {similarity:.2f}%).")
                
                # Improved merging logic: prioritize non-blank values from either column
                # First take col1 values where available
                merged_values = df[col1].copy()
                # Then fill remaining NaN values with col2 values
                merged_values = merged_values.fillna(df[col2])
                
                # Update col1 with merged values
                df[col1] = merged_values
                
                # Drop col2 from the DataFrame
                df.drop(columns=[col2], inplace=True)
                column_names.pop(i + 1)  # Remove col2 from the column list dynamically
                merged_columns_info.append((col1, col2))
            else:
                print(f"Keeping both columns '{col1}' and '{col2}' unchanged (Similarity below threshold).")
            
            i -= 1  # Move to the next column on the left
        
        return df, merged_columns_info

    async def handle_table_or_maker(self):
        sheet_data = {}
        # Extract data from extracted_data
        boxes, texts, probabilities = self.table_structure(self.extracted_data_list)
        print(f"Extracted {len(boxes)} boxes, {len(texts)} texts, {len(probabilities)} probabilities")
        
        if not boxes:
            print("⚠️ No bounding boxes found in extracted data!")

        # Read image for drawing
        image_boxes = cv2.imread(self.sub_image)
        if image_boxes is None:
            print(f"Failed to read image: {self.sub_image}, skipping...")

        image_height, image_width = image_boxes.shape[:2]

        # Draw bounding boxes
        for bbox, text in zip(boxes, texts):
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(image_boxes, (x1, y1), (x2, y2), (0, 0, 255), 2)

        # Save the detection output
        output_img_path = os.path.join(DETECTION_OUTPUT, f'Detections_{self.sub_image_basename}.jpg')
        cv2.imwrite(output_img_path, image_boxes)

        # Reconstructing table
        im = image_boxes.copy()
        vert_boxes, horiz_boxes = [], []

        for box in boxes:
            x1, y1, x2, y2 = map(int, box)
            x_h, x_v = 0, int(x1)
            y_h, y_v = int(y1), 0

            width_h, width_v = image_width, int(x2 - x1)
            height_h, height_v = int(y2 - y1), image_height

            horiz_boxes.append([x_h, y_h, x_h + width_h, y_h + height_h])
            vert_boxes.append([x_v, y_v, x_v + width_v, y_v + height_v])

            cv2.rectangle(im, (x_h, y_h), (x_h + width_h, y_h + height_h), (0, 255, 0), 1)
            cv2.rectangle(im, (x_v, y_v), (x_v + width_v, y_v + height_v), (255, 0, 0), 1)

        output_hv_path = os.path.join(DETECTION_OUTPUT, f'Detections_H_V_boxes_{self.sub_image_basename}.jpg')
        cv2.imwrite(output_hv_path, im)

        # Use TensorFlow non-max suppression to find key lines
        if boxes:  # Check if we have any boxes
            # Convert to tensors (TF doesn't like empty tensors)
            horiz_boxes_tensor = tf.convert_to_tensor(horiz_boxes, dtype=tf.float32)
            vert_boxes_tensor = tf.convert_to_tensor(vert_boxes, dtype=tf.float32)
            probabilities_tensor = tf.convert_to_tensor(probabilities, dtype=tf.float32)

            horiz_out = tf.image.non_max_suppression(
                horiz_boxes_tensor, probabilities_tensor,
                max_output_size=1000, iou_threshold=0.05, score_threshold=float('-inf')
            )
            vert_out = tf.image.non_max_suppression(
                vert_boxes_tensor, probabilities_tensor,
                max_output_size=1000, iou_threshold=0.1, score_threshold=float('-inf')
            )

            horiz_lines = np.sort(np.array(horiz_out))
            vert_lines = np.sort(np.array(vert_out))

            # Visualization for debugging
            im_nms = image_boxes.copy()
            for val in horiz_lines:
                cv2.rectangle(im_nms, (int(horiz_boxes[val][0]), int(horiz_boxes[val][1])),
                            (int(horiz_boxes[val][2]), int(horiz_boxes[val][3])), (0, 0, 255), 1)
            for val in vert_lines:
                cv2.rectangle(im_nms, (int(vert_boxes[val][0]), int(vert_boxes[val][1])),
                            (int(vert_boxes[val][2]), int(vert_boxes[val][3])), (255, 0, 0), 5)

            output_nms_path = os.path.join(DETECTION_OUTPUT, f'im_nms_{self.sub_image_basename}.jpg')
            cv2.imwrite(output_nms_path, im_nms)

            # Table reconstruction
            if len(horiz_lines) > 0 and len(vert_lines) > 0:
                out_array = [["" for _ in range(len(vert_lines))] for _ in range(len(horiz_lines))]
                unordered_boxes = [vert_boxes[i][0] for i in vert_lines]
                ordered_boxes = np.argsort(unordered_boxes)

                for i in range(len(horiz_lines)):
                    for j in range(len(vert_lines)):
                        resultant = self.intersection(horiz_boxes[horiz_lines[i]],
                                                    vert_boxes[vert_lines[ordered_boxes[j]]])

                        for b in range(len(boxes)):
                            if self.iou(resultant, boxes[b]) > 0.0:
                                out_array[i][j] = texts[b]

                # Convert the table to a DataFrame
                table_df = pd.DataFrame(out_array)

                # Append the table to the sheet data
                sheetname = self.sub_image_basename  
                # Truncate sheet name if too long (Excel limitation)
                if len(sheetname) > 31:
                    sheetname = sheetname[:31]
                    
                if sheetname not in sheet_data:
                    sheet_data[sheetname] = table_df  # Initialize the sheet with the first table

        # Save all sheets to Excel (only if we have any data)
        if sheet_data:
            for s_name, df in sheet_data.items():
                
                # Apply column merging
                df,_ = self.merge_columns(df)
                df.to_excel(self.writer, sheet_name=s_name, index=False, header=False)

        else:
            print("⚠️ No valid table data was found, no Excel file was created.")



