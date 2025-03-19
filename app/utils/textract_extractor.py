#app/utils/textract_extractor.py
import os
import re
import boto3
from openpyxl import Workbook
from PIL import Image
import pandas as pd
import io
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError, EndpointConnectionError
import logging
from app.services.connection_manager import manager
import asyncio
import cv2
# from app.utils.using_dedoc import DedocTableExtractor
import base64
from app.utils.merge_excel import merge_excel_dedoc
from app.utils.extractor import TextExtractor
from app.utils.table_processor import Table_Processor
from app.utils.maker_processor import Maker_Processor

class TextractExtractor:
    def __init__(self, image_bounding_boxes, pdf_path, total_pages, yolo_done=True):
        """ Initialize with a dictionary of image paths and bounding boxes. """
        self.image_bounding_boxes = image_bounding_boxes
        self.pdf_path = pdf_path
        self.pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        self.yolo_done = yolo_done
        self.total_pages = total_pages
        self.detected_pages = 0

        # self.dedoc_extractor = DedocTableExtractor()
        self.custom_extractor = TextExtractor()
        self.table_processor = Table_Processor()
        self.maker_processor = Maker_Processor()
    

    def read_image_data(self, image_path):
        try:
            with open(image_path, 'rb') as file:
                img_test = file.read()
                bytes_test = bytearray(img_test)
                logging.info('Image loaded', image_path)
                return bytes_test

        except FileNotFoundError:
            logging.warning(f"Error: The file {image_path} was not found.")
            return None
        
        except IOError as e:
            logging.warning(f"Error: Unable to open the file {image_path}. {e}")
            return None


    def crop_table_from_image(self, image_path, bounding_box, output_path):
        """ Crop a table from the original image using the bounding box and save it to the output path. """
        with Image.open(image_path) as img:
            width, height = img.size
            left = int(bounding_box['Left'] * width)
            top = int(bounding_box['Top'] * height)
            right = int((bounding_box['Left'] + bounding_box['Width']) * width)
            bottom = int((bounding_box['Top'] + bounding_box['Height']) * height)
            
            cropped_img = img.crop((left, top, right, bottom))
            cropped_img.save(output_path)

    def  crop_yolo_table(self, bbs, image_path, page_dir_pth):
        yolo_crop_paths = []
        for i, bb in enumerate(bbs):
            xmin = bb['xmin']
            ymin = bb['ymin']
            xmax = bb['xmax']
            ymax = bb['ymax']

            page_name = os.path.basename(page_dir_pth)  
            image = cv2.imread(image_path)
            yolo_cropped_image = image[int(ymin):int(ymax), int(xmin):int(xmax)]
            cropped_file_path = f"{page_dir_pth}/{page_name}_{i}_table.png"
            cv2.imwrite(cropped_file_path, yolo_cropped_image)
            yolo_crop_paths.append(cropped_file_path)
        return yolo_crop_paths


    def get_text(self, result, blocks_map):
        text = ''
        if 'Relationships' in result:
            for relationship in result['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        word = blocks_map[child_id]
                        if word['BlockType'] == 'WORD':
                            if "," in word['Text'] and word['Text'].replace(",", "").isnumeric():
                                text += '"' + word['Text'] + '"' + ' '
                            else:
                                text += word['Text'] + ' '
                        if word['BlockType'] == 'SELECTION_ELEMENT':
                            if word['SelectionStatus'] =='SELECTED':
                                text +=  'X '
        return text

    def get_rows_columns_map(self, table_result, blocks_map):
        rows = {}
        scores = []
        for relationship in table_result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    cell = blocks_map[child_id]
                    if cell['BlockType'] == 'CELL':
                        row_index = cell['RowIndex']
                        col_index = cell['ColumnIndex']
                        if row_index not in rows:
                            # create new row
                            rows[row_index] = {}
                        
                        # get confidence score
                        scores.append(str(cell['Confidence']))
                            
                        # get the text value
                        rows[row_index][col_index] = self.get_text(cell, blocks_map)
        return rows, scores

    def generate_table_xlsx(self,table_result, blocks_map, worksheet):
        rows, _ = self.get_rows_columns_map(table_result, blocks_map)

        for row_index, cols in rows.items():
            for col_index, text in cols.items():
                worksheet.cell(row=row_index, column=col_index, value=text)

    def call_aws_textract(self, image_path, page_dir, current_page):

                                # Send progress update via WebSocket

            # Read image data for Textract
            img_data = self.read_image_data(image_path)

            try:
                # Call Textract
                textract = boto3.client('textract')
                response = textract.analyze_document(
                    Document={'Bytes': img_data}, 
                    FeatureTypes=['TABLES']
                )
                workbook = Workbook()

                # Process the response here
                workbook, exc_save_path = self.process_textract_response(image_path, page_dir, response, workbook)
                try:
                    workbook.save(exc_save_path)
                    logging.info(f'XLSX output saved: {exc_save_path}')
                except IOError as e:
                    logging.warning(f"Error saving XLSX file: {e}")
                finally:
                    workbook.close()

                

            except (NoCredentialsError, PartialCredentialsError) as e:
                logging.warning(f"Error with AWS credentials: {e}")
            
            except ClientError as e:
                if e.response['Error']['Code'] == 'AccessDeniedException':
                    logging.warning("Error: Access denied. Check AWS permissions.")
                if e.response['Error']['Code'] == 'LimitExceededException':
                    logging.warning('API call limit exceeded; backing off and retrying...')
                else:
                    logging.warning(f"ClientError: {e.response['Error']['Message']}")
            except EndpointConnectionError:
                logging.warning("Error: Unable to connect to AWS endpoint. Check network or endpoint configuration.")
            except Exception as e:
                logging.warning(f"Unexpected error: {e}")


    async def call_dedoc(self, image_path, page_dir_pth, current_page, bbs):
        # cropped_file_name = f"{page_dir_pth}/{page_name}_{index}_table.png"
        # self.crop_table_from_image(file_path, bounding_box, cropped_file_name)
        cropped_yolo_pthlst = self.crop_yolo_table(bbs, image_path,page_dir_pth)
        # Process each cropped image and save as Excel
        for cropped_path in cropped_yolo_pthlst:
            excel_path = cropped_path.replace('.png', '.xlsx')
            logging.info(f"Processing cropped image: {cropped_path} -> Saving to Excel: {excel_path}")
            await self.dedoc_extractor.extract_tables_from_image(image_path=cropped_path, excel_path=excel_path)       


    
    async def get_table_xlsx_results(self):
        """ Process each image to extract tables and save them to an XLSX file. """
        # print(111111111111111111111111111111111111111111111111111111111111111)
        # self.detected_pages = len(self.image_bounding_boxes) if self.yolo_done else len(list(enumerate(self.image_bounding_boxes)))
        current_page = 0
        for image_path, bounding_boxes in self.image_bounding_boxes.items() if self.yolo_done else enumerate(self.image_bounding_boxes):
            page_dir = image_path.split('.jpg')[0]
            number = re.search(r'(\d+)$', page_dir).group(1)
            current_page = str(int(number)) 
            logging.info({
                "filename": self.pdf_name,
                "current_page": int(current_page),
                "total_pages": int(self.total_pages),
                "status": False,
                "exc_link": 'null'})

            # await manager.send_json({
            #     "filename": self.pdf_name,
            #     "current_page": int(current_page),
            #     "total_pages": int(self.total_pages),
            #     "status": False,
            #     "exc_link": 'null'
            # })

            if self.yolo_done and not bounding_boxes:
                logging.info(f"No Tables found for {image_path}")
                continue
            
            # await asyncio.sleep(0)

            os.makedirs(page_dir, exist_ok=True)
            # self.call_aws_textract(image_path, page_dir, current_page)
            # await self.call_dedoc(image_path, page_dir, current_page, bounding_boxes)
            # asyncio.create_task(self.call_dedoc(image_path, page_dir, current_page, bounding_boxes))
            
        '''abins portion- return single pdf exc path'''
        pdf_img_dir = os.path.join(f'./app/images/{self.pdf_name}')
        out_pdfexcel_dir = './app/out_excel'
        os.makedirs(out_pdfexcel_dir, exist_ok=True)
        out_pdf_excel = os.path.join(out_pdfexcel_dir, self.pdf_name+'.xlsx')
        merge_excel_dedoc(pdf_img_dir, out_pdf_excel)
        # After you have created out_pdf_excel
        if os.path.exists(out_pdf_excel):
            # Read the Excel file in binary mode and encode it as Base64
            with open(out_pdf_excel, "rb") as file:
                excel_data = file.read()
                base64_excel_data = base64.b64encode(excel_data).decode("utf-8")

            # Send the Base64 data over WebSocket
            # await manager.send_json({
            #     "filename": self.pdf_name,
            #     "current_page": int(current_page),
            #     "total_pages": int(self.total_pages),
            #     "status": True,
            #     "exc_link": base64_excel_data  # Encoded blob as a string
            # })
            logging.info({
                "filename": self.pdf_name,
                "current_page": int(current_page),
                "total_pages": int(self.total_pages),
                "status": True,
                "exc_link": base64_excel_data})
        else:
            # File does not exist, so send an error or status update
            # await manager.send_json({
            #     "filename": self.pdf_name,
            #     "current_page": int(current_page),
            #     "total_pages": int(self.total_pages),
            #     "status": True,
            #     "exc_link": 'null'
            # })

            logging.info({
                "filename": self.pdf_name,
                "current_page": int(current_page),
                "total_pages": int(self.total_pages),
                "status": True,
                "exc_link": 'null'})
        return out_pdf_excel
        
    

    async def get_info_image(self):
        current_page = 0
        self.image_bounding_boxes = dict(sorted(self.image_bounding_boxes.items()))


        for image_path, result in self.image_bounding_boxes.items():
            page_dir = image_path.split('.jpg')[0]
            number = re.search(r'(\d+)$', page_dir).group(1)
            current_page = str(int(number)) 
            logging.info("....................current page number ........................", current_page)
            await manager.send_json({
                "filename": self.pdf_name,
                "current_page": int(current_page),
                "total_pages": int(self.total_pages),
                "status": False,
                "exc_link": 'null'
            })

            await asyncio.sleep(0)
            # Get the folder path for this image
            image_folder = os.path.dirname(image_path)
            # Collect tables
            tables = result.get('tables', [])

            # Collect makers components
            makers_components = result.get('components', [])

            

            # Combine all detections
            all_detections = tables + makers_components

            if all_detections:

                png_image_path = self.custom_extractor.process_each_image(all_detections)
                

                basename = os.path.basename(image_path)
            
                filename = os.path.splitext(basename)[0]

                excel_filename = os.path.join(image_folder, f"{filename}.xlsx")
                writer = pd.ExcelWriter(excel_filename, engine='xlsxwriter')
                for sub_image, extracted_data_list in png_image_path.items():
                    if extracted_data_list:
                        if '_table' in os.path.basename(sub_image):
                            await self.table_processor.process_image_data(sub_image, extracted_data_list, writer)
                            # asyncio.create_task(self.table_processor.process_image_data(sub_image, extracted_data_list, writer))
                        else:
                            await self.maker_processor.process_image_data(sub_image, extracted_data_list, writer)
                            # asyncio.create_task(self.maker_processor.process_image_data(sub_image, extracted_data_list, writer))
                        
                writer.close()
        
        pdf_img_dir = os.path.join(f'./app/images/{self.pdf_name}')
        out_pdfexcel_dir = './app/out_excel'
        os.makedirs(out_pdfexcel_dir, exist_ok=True)
        out_pdf_excel = os.path.join(out_pdfexcel_dir, self.pdf_name+'.xlsx')
        merge_excel_dedoc(pdf_img_dir, out_pdf_excel)
        if os.path.exists(out_pdf_excel):
            # Read the Excel file in binary mode and encode it as Base64
            with open(out_pdf_excel, "rb") as file:
                excel_data = file.read()
                base64_excel_data = base64.b64encode(excel_data).decode("utf-8")

            # Send the Base64 data over WebSocket
            await manager.send_json({
                "filename": self.pdf_name,
                "current_page": int(current_page),
                "total_pages": int(self.total_pages),
                "status": True,
                "exc_link": base64_excel_data  # Encoded blob as a string
            })

        else:
            # File does not exist, so send an error or status update
            await manager.send_json({
                "filename": self.pdf_name,
                "current_page": int(current_page),
                "total_pages": int(self.total_pages),
                "status": True,
                "exc_link": 'null'
            })
        return out_pdf_excel





    def process_textract_response(self, file_path, page_dir_pth, response, workbook):
        """ Process the Textract response to extract tables and save them into the workbook. """
        # Get the text blocks from the response
        blocks = response['Blocks']

        blocks_map = {}
        table_blocks = []

        for block in blocks:
            blocks_map[block['Id']] = block
            if block['BlockType'] == "TABLE":
                table_blocks.append(block)
        
        if len(table_blocks) <= 0:
            logging.info("<b> NO Table FOUND </b>")
            return None
        page_name = os.path.basename(page_dir_pth)        
        for index, table in enumerate(table_blocks):

            ws = workbook.create_sheet(title=f'{page_name}_{index}_table')
            self.generate_table_xlsx(table, blocks_map, ws)
            
            bounding_box = table.get('Geometry', {}).get('BoundingBox', {})
            cropped_file_name = f"{page_dir_pth}/{page_name}_{index}_table.png"
            self.crop_table_from_image(file_path, bounding_box, cropped_file_name)
            # Remove the default sheet created by openpyxl
        if 'Sheet' in workbook.sheetnames:
            workbook.remove(workbook['Sheet'])
        
        exc_save_path = os.path.join(page_dir_pth, f"{page_name}.xlsx")
        
        return workbook, exc_save_path

        

            
            
            


# Example usage
# if __name__ == "__main__":

# # Example usage
# image_bounding_yolo_boxes = {
#     'path/to/page_001.jpg': [{'xmin': 163, 'ymin': 325, 'xmax': 945, 'ymax': 1299}],
#     'path/to/page_002.jpg': [{'xmin': 131, 'ymin': 232, 'xmax': 888, 'ymax': 1232}],
#     'path/to/page_003.jpg': [{'xmin': 122, 'ymin': 155, 'xmax': 896, 'ymax': 1251}],
#     # Add other image paths and bounding boxes...
# }

# image_paths_without_yolo = [
#     'path/to/page_001.jpg',
#     'path/to/page_002.jpg',
#     'path/to/page_003.jpg',
# ]

# pdf_name = 'HF27-LIFE BOAT'
# extractor = TextractExtractor(image_bounding_yolo_boxes, pdf_name=pdf_name, yolo_done=True)
# extractor.get_table_xlsx_results()

# extractor_without_yolo = TextractExtractor(image_paths_without_yolo, pdf_name=pdf_name, yolo_done=False)
# workbook_no_yolo = extractor_without_yolo.get_table_xlsx_results()
