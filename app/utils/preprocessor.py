# """
# Image preprocessing module for preparing images for OCR.
# """

# import cv2
# import pytesseract
# import numpy as np
# import os
# from pytesseract import TesseractError

# class ImageProcessor:
#     def __init__(self):
#         """Initialize the ImageProcessor."""
#         pass


#     def detect_and_rotate_if_landscape(self, img, output_path):
#         try:
#             # Use Tesseract's orientation detection (get the rotation info)
#             ocr_data = pytesseract.image_to_osd(img)
#             rotation = int(ocr_data.split("Rotate:")[1].split("\n")[0].strip())



#             if rotation in [90, 270]:  # Rotate only if 90° or 270°
                
#                 # Correct orientation to 0°
#                 if rotation == 270:
#                     rotated_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
#                     cv2.imwrite(output_path, rotated_img) 
#                      # Save the rotated image
#                 else:  # rotation == 270
#                     rotated_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
#                     cv2.imwrite(output_path, rotated_img)  
#             else:
#                 # If the image is already in portrait mode, just save it without rotating
#                 cv2.imwrite(output_path, img)

#         except TesseractError as e:
#             print(f"TesseractError occurred: {str(e)}. Saving the original image without rotation.")
#             # Save the original image without rotation if an error occurs
            
#             cv2.imwrite(output_path, img)

#         except Exception as e:
#             print(f"Unexpected error: {str(e)}. Saving the original image without rotation.")
#             # Save the original image without rotation for any other unexpected error
#             cv2.imwrite(output_path, img)

    
# # preproc = ImageProcessor()
# # img = cv2.imread("app/images/pdf_img/A42-V4430000-GALLEY & LAUNDRY EQUIPMENT_removed_page-0002.jpg")
# # preproc.detect_and_rotate_if_landscape(img,"app/images/pdf_img/A42-V4430000-GALLEY & LAUNDRY EQUIPMENT_removed_page-0002.jpg")
    



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
        """
        Detects if an image is in landscape orientation and rotates it to portrait.
        Scales the image for OCR processing but saves the rotated result in original size.
        
        Args:
            img: Input image as numpy array
            output_path: Path to save the output image
        """
        try:
            # Check if image is valid
            if img is None or img.size == 0:
                print(f"Invalid image. Skipping processing.")
                return
            
            # Make a copy of the original image for saving later
            original_img = img.copy()
            
            # Get DPI info if available
            dpi_x, dpi_y = self._get_image_dpi(img)
            
            # If DPI is too low or couldn't be determined, scale up the image for better OCR
            scale_percent = 300  # Default scale up by 300%
            
            # Only scale if DPI is below 300 or couldn't be determined
            if dpi_x is None or dpi_x < 300 or dpi_y is None or dpi_y < 300:
                # Scale the image for OCR processing
                width = int(img.shape[1] * scale_percent / 100)
                height = int(img.shape[0] * scale_percent / 100)
                dim = (width, height)
                scaled_img = cv2.resize(img, dim, interpolation=cv2.INTER_CUBIC)
            else:
                # If DPI is sufficient, use original image for OCR
                scaled_img = img
            
            # Use Tesseract's orientation detection on the scaled image
            ocr_data = pytesseract.image_to_osd(scaled_img)
            rotation = int(ocr_data.split("Rotate:")[1].split("\n")[0].strip())
            
            # Determine if rotation is needed
            if rotation in [90, 270]:
                # Rotate the ORIGINAL image (not the scaled one)
                if rotation == 90:
                    rotated_img = cv2.rotate(original_img, cv2.ROTATE_90_CLOCKWISE)
                else:  # rotation == 270
                    rotated_img = cv2.rotate(original_img, cv2.ROTATE_90_CLOCKWISE)
                # Save the rotated image in original resolution
                cv2.imwrite(output_path, rotated_img)
                print(f"Rotated image saved: {output_path}")
            else:
                # If the image is already in portrait mode, just save the original
                cv2.imwrite(output_path, original_img)
                print(f"Image already in portrait orientation: {output_path}")
                
        except TesseractError as e:
            print(f"TesseractError occurred: {str(e)}. Saving the original image without rotation.")
            # Save the original image without rotation if an error occurs
            cv2.imwrite(output_path, original_img if 'original_img' in locals() else img)
            
        except Exception as e:
            print(f"Unexpected error: {str(e)}. Saving the original image without rotation.")
            # Save the original image without rotation for any other unexpected error
            cv2.imwrite(output_path, original_img if 'original_img' in locals() else img)
    
    def _get_image_dpi(self, img):
        """
        Attempts to determine the DPI of an image.
        Returns (None, None) if DPI cannot be determined.
        
        Args:
            img: Input image as numpy array
            
        Returns:
            tuple: (dpi_x, dpi_y) or (None, None) if not found
        """
        try:
            # Save a temporary copy of the image to check metadata
            temp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "temp_dpi_check.png")
            cv2.imwrite(temp_path, img)
            
            # Try to get DPI information from the image file
            from PIL import Image
            with Image.open(temp_path) as pil_img:
                dpi = pil_img.info.get('dpi')
                
                # Clean up the temporary file
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
                if dpi:
                    return dpi[0], dpi[1]
                    
            return None, None
            
        except Exception as e:
            print(f"Could not determine image DPI: {str(e)}")
            # Try to clean up the temporary file if it exists
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
            return None, None