"""
Image preprocessing module for preparing images for OCR.
"""

import cv2
import pytesseract
import numpy as np
import os
from pytesseract import TesseractError

class ImageProcessor:
    def __init__(self):
        """Initialize the ImageProcessor."""
        pass


    def detect_and_rotate_if_landscape(self, img, output_path):
        try:
            # Use Tesseract's orientation detection (get the rotation info)
            ocr_data = pytesseract.image_to_osd(img)
            rotation = int(ocr_data.split("Rotate:")[1].split("\n")[0].strip())


            if rotation in [90, 270]:  # Rotate only if 90° or 270°
                
                # Correct orientation to 0°
                if rotation == 270:
                    rotated_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                    cv2.imwrite(output_path, rotated_img) 
                     # Save the rotated image
                else:  # rotation == 270
                    rotated_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                    cv2.imwrite(output_path, rotated_img)  
            else:
                # If the image is already in portrait mode, just save it without rotating
                cv2.imwrite(output_path, img)

        except TesseractError as e:
            print(f"TesseractError occurred: {str(e)}. Saving the original image without rotation.")
            # Save the original image without rotation if an error occurs
            cv2.imwrite(output_path, img)

        except Exception as e:
            print(f"Unexpected error: {str(e)}. Saving the original image without rotation.")
            # Save the original image without rotation for any other unexpected error
            cv2.imwrite(output_path, img)

    
# preproc = ImageProcessor()
# img = cv2.imread("app/images/pdf_img/A42-V4430000-GALLEY & LAUNDRY EQUIPMENT_removed_page-0002.jpg")
# preproc.detect_and_rotate_if_landscape(img,"app/images/pdf_img/A42-V4430000-GALLEY & LAUNDRY EQUIPMENT_removed_page-0002.jpg")
    