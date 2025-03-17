import cv2
import os
from typing import List
from dedoc.data_structures import Table
from openpyxl import Workbook
from dedoc.converters import PNGConverter
from dedoc.readers import PdfImageReader

class DedocTableExtractor:

    def __init__(self):
        self.converter = PNGConverter()
        self.reader = PdfImageReader()

    def save_to_excel(self, table: Table, path: str) -> None:
        """Saves a table to an Excel file."""
        cell_text_list = [[cell.get_text() for cell in row] for row in table.cells]
        
        # Create an Excel workbook and add the table data
        workbook = Workbook()
        sheet = workbook.active
        
        for row_data in cell_text_list:
            sheet.append(row_data)  # Append each row to the sheet
        
        workbook.save(path)

    async def extract_tables_from_image(self, image_path: str, excel_path: str) -> None:
        """Extract tables from an image and save to Excel."""
        if not self.reader.can_read(file_path=image_path):
            raise ValueError("Incorrect file format for reading tables")
        
        document = self.reader.read(file_path=image_path)

        for i, table in enumerate(document.tables):
            table_path = excel_path.replace('.xlsx', f'.xlsx')
            self.save_to_excel(table=table, path=table_path)



dedoc_use = DedocTableExtractor()
dedoc_use.extract_tables_from_image(image_path='/home/thinkpalm/vs_projects/table_extraction/TPMAIS10/app/utils/11-58-56.png',
                                    excel_path='output.xlsx')
