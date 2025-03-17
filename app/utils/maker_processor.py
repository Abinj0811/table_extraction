
import os
import pandas as pd
import re
from pathlib import Path
from app.utils.custom_ocr import Custom_OCR

# Mapping for row names
COLUMN_MAPPING = {
    "title": "Title",
    "mk_name": "Maker Name",
    "dwg_no": "Drawing No"
}

# Words to exclude from values
EXCLUDE_WORDS = {
    "title": ["title", "TITLE", "SUBJECT"],
    "dwg_no": ["dwg_no", "drawing number", "DWG_NO", "DWG. NU", ".","DRAWING NO."],
    "mk_name": ["- "]
}

class Maker_Processor(Custom_OCR):
    def __init__(self):
        super().__init__()
        
    def clean_text(self, field, text):
        """Remove unwanted words from text."""
        if field in EXCLUDE_WORDS:
            for word in EXCLUDE_WORDS[field]:
                text = re.sub(rf'\b{word}\b', '', text, flags=re.IGNORECASE).strip()
        return text
    

    async def handle_table_or_maker(self):
        # Debug: Check if extracted_data_list contains data
        if not self.extracted_data_list:
            print(f"⚠️ No extracted data to process for {self.sub_image_basename}")
            return
        
        # Determine the class label based on the filename
        class_label = None
        filename = self.sub_image_basename.lower()  # Convert filename to lowercase for case-insensitive comparison
        
        # Check if any COLUMN_MAPPING key is present in the filename
        for key, value in COLUMN_MAPPING.items():
            if key.lower() in filename:
                class_label = value
                break
        
        if not class_label:
            print(f"⚠️ No matching class label found in filename: {filename}")
            return
        
        # Extract and clean all text values from text_lines
        cleaned_values = []
        for entry in self.extracted_data_list.get("text_lines", []):
            text = entry.get("text", "").strip()
            if text:
                cleaned_text = self.clean_text(class_label.lower(), text)
                cleaned_values.append(cleaned_text)
        
        # Combine all cleaned values into a single string
        combined_value = " ".join(cleaned_values)
        
        # Create a single row of data
        extracted_data = [[class_label, combined_value]]
        
        # If we have extracted data, write it to Excel
        if extracted_data:
            # Create DataFrame
            df = pd.DataFrame(extracted_data, columns=["Field", "Value"])
            
            # Generate Excel sheet name (limited to 31 chars)
            sheet_name = self.sub_image_basename
            if len(sheet_name) > 31:
                sheet_name = sheet_name[:31]
            
            # Append "_info" to distinguish from table sheets
            maker_sheet_name = f"{sheet_name}"
            if len(maker_sheet_name) > 31:
                maker_sheet_name = sheet_name[:26] 
            
            # Write to Excel
            df.to_excel(self.writer, sheet_name=maker_sheet_name, index=False)
            print(f"✅ Maker information saved to sheet: {maker_sheet_name}")
        else:
            print(f"⚠️ No maker information extracted for {self.sub_image_basename}")