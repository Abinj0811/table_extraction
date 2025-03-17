import os
import cv2
import numpy as np
import tensorflow as tf
import pandas as pd
from pathlib import Path

class Custom_OCR:
    def __init__(self):
        self.sub_image = None
        self.extracted_data_list = {}
        self.sub_image_basename = None

    async def process_image_data(self, sub_image, extracted_data_list, writer):
        """Process a set of extracted data for a single image to create an Excel file."""
        print(f"Processing image: {sub_image}")
        print(f"Number of extracted data items: {len(extracted_data_list)}")
        self.sub_image = sub_image
        self.extracted_data_list = extracted_data_list
        sub_image_basename =Path(self.sub_image).stem
        self.sub_image_basename = sub_image_basename
        self.writer = writer
        # Debug: Check if extracted_data_list contains data
        if not self.extracted_data_list:
            print("⚠️ No extracted data to process!")
            return
     
        # Check the first item in the list to verify structure
        if "text_lines" not in self.extracted_data_list:
            print(f"⚠️ Missing 'text_lines' in extracted data. Keys: {list(self.extracted_data_list.keys())}")
            return
       
        if not self.extracted_data_list["text_lines"]:
            print("⚠️ 'text_lines' list is empty!")
        
            
        # Verify the bbox format
        if self.extracted_data_list["text_lines"]:
            sample_line = self.extracted_data_list["text_lines"][0]
            print(f"Sample text line: {sample_line['text']}")
            print(f"Sample bbox: {sample_line['bbox']}")
            print(f"Bbox type: {type(sample_line['bbox'])}, length: {len(sample_line['bbox'])}")

        
        await self.handle_table_or_maker()
    
    async def handle_table_or_maker(self):
        """Default implementation for handling tables (if any)."""
        print("No table processing in the base class.")
