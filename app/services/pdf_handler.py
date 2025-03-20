
# services/pdf_handler.py
from app.utils.pdf_to_images import PDFToImages
from app.utils.table_detection import TableDetection
from app.utils.textract_extractor import TextractExtractor
import os
import logging
import asyncio
from app.services.connection_manager import manager
from app.utils.detector import TableDetector


# Configure the logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Check if logger already has handlers to avoid duplicate logs
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class PDFHandler:
    def __init__(self, pdf_path, pages_to_show = None):
        self.pdf_path = pdf_path
        self.pdf_name = os.path.basename(pdf_path)
        self.pages_to_show = pages_to_show
        self.image_dir = None
        self.table_boxes = None
        self.total_pages =0

    def convert_pdf_to_images(self):
        # Initialize PDFToImages with the PDF path
        try:
            pdf_to_images = PDFToImages(self.pdf_path)
            images, self.image_dir = pdf_to_images.gs_pdf_to_jpg(self.pages_to_show)
            self.total_pages = len(images)
            return images
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise
        
    async def detect_tables(self):
        if self.image_dir is None:
            raise ValueError("Images not generated. Run convert_pdf_to_images first.")
        
        # table_detector = TableDetection("/home/thinkpalm/MachineLearning/Table_extraction/app/best_mod.pt")  # Update with your YOLO model path
        # detected_tables = table_detector.detect_tables_in_directory(self.image_dir)
        table_detector = TableDetector("app/models/best_tables.pt", "app/models/best_makers.pt",self.pdf_name,self.total_pages)

        detected_tables =await table_detector.process_folder(self.image_dir)


        # Log the detected tables structure to verify its format
        logger.debug(f"Detected tables: {detected_tables}")

        # If detected_tables is a dictionary, set it directly
        if isinstance(detected_tables, dict):
            self.table_boxes = detected_tables
        else:
            raise ValueError("Unexpected format for detected tables")

        return self.table_boxes
    
    def do_textract(self, images_list, yolo_done=True):
        """ Run Textract to extract tables from images. """
        extractor = TextractExtractor(images_list, self.pdf_path, total_pages=self.total_pages, yolo_done=yolo_done)
        # exc_path = extractor.get_table_xlsx_results()
        exc_path = extractor.get_info_image()
        return exc_path
    
    async def async_convert_pdf_to_images(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.convert_pdf_to_images)

    async def process_pdf(self):
        try:
            await self.async_convert_pdf_to_images()
            # image_files_list = self.convert_pdf_to_images()
            if not self.pages_to_show:
                table_bbs_dict = await self.detect_tables()
                # Check detection results
                if table_bbs_dict:
                    exc_path = await self.do_textract(table_bbs_dict, yolo_done=True)
                    # exc_path = self.do_textract(table_bbs_dict, yolo_done=True)
                else:
                    logger.info("No tables detected.")
                    exc_path = None
            else:
                sorted_image_files = sorted(
                    self.image_files_list,
                    key=lambda x: int(os.path.basename(x).split('_')[-1].split('.')[0])
                )
                exc_path = await self.do_textract(sorted_image_files, yolo_done=False)
                # exc_path = self.do_textract(sorted_image_files, yolo_done=False)
            return exc_path
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return None
    
async def process_multiple_pdfs(pdf_paths):
    """
    Processes multiple PDFs by iterating over the list of pdf_paths.
    """
    exc_paths = {}
    for pdf_path in pdf_paths:
        handler = PDFHandler(pdf_path)
        # print(f"Processing PDF: {pdf_path}")
        logging.info(f"Processing PDF: {pdf_path}")
        await manager.send_json({"status": False, "filename": handler.pdf_name, "current_page": 0, "total_pages":100})
        exc_path = await handler.process_pdf()
        # exc_path = handler.process_pdf()
         # Capture result paths
        exc_paths[pdf_path] = exc_path if exc_path else False

    return exc_paths


# Example usage
# if __name__ == "__main__":
#     try:
#         pdf_handler = PDFHandler("/home/thinkpalm/vs_projects/table_extraction/TPMAIS10/app/uploaded_pdfs/HF27-LIFE BOAT.pdf")
#         image_files_list = pdf_handler.convert_pdf_to_images()

#         if not pdf_handler.pages_to_show:
#             table_bbs_dict = pdf_handler.detect_tables()
#             # print(table_bbs_dict)
#             # Check detection results
#             if table_bbs_dict:
#                 print(1111111111111111111111111111111111111)
#                 exc_path = pdf_handler.do_textract(table_bbs_dict, yolo_done=True)
#             else:
#                 logging.info("No tables detected.")
#         else:
#             sorted_image_files = sorted(
#                 image_files_list,
#                 key=lambda x: int(os.path.basename(x).split('_')[-1].split('.')[0])
#             )
#             exc_path = pdf_handler.do_textract(sorted_image_files, yolo_done=False)
#     except Exception as e:
#         logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    async def main():
        try:
            pdf_handler = PDFHandler("/home/thinkpalm/vs_projects/table_extraction/TPMAIS10/app/uploaded_pdfs/HF27-LIFE BOAT.pdf")
            await pdf_handler.async_convert_pdf_to_images()

            if not pdf_handler.pages_to_show:
                table_bbs_dict = await pdf_handler.detect_tables()
                if table_bbs_dict:
                    exc_path = await pdf_handler.do_textract(table_bbs_dict, yolo_done=True)
                else:
                    logging.info("No tables detected.")
            else:
                sorted_image_files = sorted(
                    pdf_handler.image_files_list,
                    key=lambda x: int(os.path.basename(x).split('_')[-1].split('.')[0])
                )
                exc_path = await pdf_handler.do_textract(sorted_image_files, yolo_done=False)
        except Exception as e:
            logging.error(f"An error occurred: {e}")

    asyncio.run(main())