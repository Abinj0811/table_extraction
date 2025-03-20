import os
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.styles import PatternFill, Alignment, Font
import re
import warnings
import logging
from openpyxl import load_workbook
from io import BytesIO
from PIL import Image as PILImage

# Configure the logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

warnings.filterwarnings('ignore')

def check_directory_exists(directory):
    return os.path.exists(directory)

def read_jpg_images(pdf_img_dir):
    images = []
    for root, dirs, files in os.walk(pdf_img_dir):
        for file in files:
            if file.lower().endswith(".jpg"):
                image_path = os.path.join(root, file)
                images.append(image_path)
    return images

def read_existing_excels(pdf_img_dir):
    excel_files = []
    for root, dirs, files in os.walk(pdf_img_dir):
        for file in files:
            if file.lower().endswith(".xlsx"):
                excel_path = os.path.join(root, file)
                excel_files.append(excel_path)
    return excel_files

def read_png_images(pdf_img_dir):
    png_images = {}
    for root, dirs, files in os.walk(pdf_img_dir):
        for file in files:
            if file.lower().endswith(".png"):
                image_path = os.path.join(root, file)
                image_name = os.path.splitext(file)[0]
                png_images[image_name] = image_path
    return png_images

def append_excel_data_with_heading(sheet, df, heading, image_path):
    fill_color = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    left_alignment = Alignment(horizontal="left")

    # Insert heading for the Excel file (table name)
    sheet.append([f"Data from {heading}"])

    heading_row = sheet.max_row
    
    for cell in sheet[heading_row]:
        cell.fill = fill_color
        cell.alignment = left_alignment
    
    # Add 1 empty row after the heading
    sheet.append([])

    # Append DataFrame rows and align all cells left
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        sheet.append(row)
        for cell in sheet[sheet.max_row]:
            cell.alignment = left_alignment
            if r_idx == 1:
                cell.font = Font(bold=True)
    
    last_col = sheet.max_column
    img_col = openpyxl.utils.get_column_letter(last_col + 3)
    img_position = f"{img_col}{heading_row}"

    # Insert the corresponding image if it matches the heading
    makers_list = "dwg_no,mk_name,title"
    makers = makers_list.split(',')
    matches = bool([maker for maker in makers if re.search(re.escape(maker), os.path.basename(image_path))])

    if image_path and os.path.exists(image_path):
        with PILImage.open(image_path) as pil_img:
            # Resize to half the original size
            width, height = pil_img.size
            resized_img = pil_img.resize((width // 2, height // 2))
            
            # Convert to bytes
            img_bytes = BytesIO()
            resized_img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            # Create an OpenpyxlImage from the resized bytes
            img = OpenpyxlImage(img_bytes)
            img.anchor = img_position
            sheet.add_image(img)

    # Add 3 empty rows for separation between tables
    for _ in range(3):
        sheet.append([])

def extract_page_number(file_path):
    match = re.search(r'page_(\d+)', file_path)
    return int(match.group(1)) if match else 0

def merge_excel_dedoc(pdf_img_dir, out_pdf_excel):
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)

    excel_files = sorted(read_existing_excels(pdf_img_dir))
    png_images = read_png_images(pdf_img_dir)
    print(9999999999999999,png_images)
    images = read_jpg_images(pdf_img_dir)
    sorted_images = sorted(images, key=extract_page_number)

    # for image_path in sorted_images:
    #     print(444444444, image_path)
    #     image_file_name = os.path.basename(image_path)
    #     sheet_name, _ = os.path.splitext(image_file_name)
    #     sheet = workbook.create_sheet(sheet_name)

    #     # Find all Excel files that match the sheet name
    #     matching_excel_files = [excel_file for excel_file in excel_files if sheet_name in excel_file]

    #     for excel_file in matching_excel_files:
    #         # Read all sheets from the Excel file
    #         excel_data = pd.read_excel(excel_file, sheet_name=None)  # Read all sheets
    #         for sheet_name_in_excel, df in excel_data.items():
    #             heading = f"{sheet_name_in_excel}"
    #             corresponding_png = png_images.get(heading, None)
    #             append_excel_data_with_heading(sheet, df, heading, corresponding_png)

    for image_path in sorted_images:
        if image_path is None:
            continue

        image_file_name = os.path.basename(image_path)
        sheet_name, _ = os.path.splitext(image_file_name)
        sheet = workbook.create_sheet(sheet_name)

        # Find all Excel files that match the sheet name
        matching_excel_files = [excel_file for excel_file in excel_files if sheet_name in excel_file]

        for excel_file in matching_excel_files:
            # Read all sheets from the Excel file
            excel_data = pd.read_excel(excel_file, sheet_name=None)
            for sheet_name_in_excel, df in excel_data.items():
                heading = f"{sheet_name_in_excel}"
                corresponding_png = png_images.get(heading, None)
                if corresponding_png:
                    append_excel_data_with_heading(sheet, df, heading, corresponding_png)


    workbook.save(out_pdf_excel)
    workbook = load_workbook(out_pdf_excel)
    
    # Check each sheet for content and remove if empty
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        
        # Check if the sheet is empty by examining its cells
        if all(cell.value is None for row in sheet.iter_rows() for cell in row):
            workbook.remove(sheet)

    # Save the workbook after removing empty sheets
    workbook.save(out_pdf_excel)

    logger.info(f"Successfully created Excel file: {out_pdf_excel}")

def main():
    pdf_name = 'HF27-LIFE BOAT'  # Specify the PDF name here
    
    pdf_img_dir = os.path.join(f'image_1/{pdf_name}')
    out_pdfexcel_dir = 'out_excel'
    os.makedirs(out_pdfexcel_dir, exist_ok=True)
    out_pdf_excel = os.path.join(out_pdfexcel_dir, pdf_name + '.xlsx')

    if check_directory_exists(pdf_img_dir):
        merge_excel_dedoc(pdf_img_dir, out_pdf_excel)
    else:
        print("The specified directory does not exist.")

