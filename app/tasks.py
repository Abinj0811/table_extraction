# tasks.py
# from app.celery_app import celery_app
from app.services.pdf_handler import PDFHandler
from app.utils.textract_extractor import TextractExtractor
from fastapi.websockets import WebSocket
from app.services.connection_manager import manager  # Import the WebSocket manager for connection handling
import asyncio
import logging
import os

# Configure the logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Check if logger already has handlers to avoid duplicate logs
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

@celery_app.task
def process_pdf(filename: str):
    """Processes a PDF and sends progress updates to WebSocket clients."""
    try:
        logger.info(f"Starting PDF processing for {filename}")
        pdf_handler = PDFHandler(filename)
        
        # Step 1: Convert PDF to images
        images = pdf_handler.convert_pdf_to_images()
        if not images:
            logger.error(f"Image conversion failed or returned empty list for {filename}")
            raise ValueError("PDF to image conversion returned no images.")

        total_pages = len(images)
        
        # Send initial progress status via WebSocket
        asyncio.run(manager.send_json({
            "filename": filename,
            "status": "PDF to images conversion complete",
            "total_pages": total_pages,
            "detected_pages":0,
            "current_page": 0
        }))

        if not pdf_handler.pages_to_show:
            table_bbs_dict = pdf_handler.detect_tables()
            if not table_bbs_dict:
                logger.info(f"No tables detected in PDF {filename}.")
                asyncio.run(manager.send_json({
                    "filename": filename,
                    "status": "No tables detected.",
                    "total_pages": total_pages,
                    "detected_pages" : len(table_bbs_dict),
                    "current_page": 0
                }))
                return
            
            # Step 2: Run Textract extraction with WebSocket updates
            extractor = TextractExtractor(table_bbs_dict, filename, total_pages, yolo_done=True)
            extractor.get_table_xlsx_results()
        
        else:
            sorted_image_files = sorted(
                images,
                key=lambda x: int(os.path.basename(x).split('_')[-1].split('.')[0])
            )
            extractor = TextractExtractor(sorted_image_files, filename, total_pages, yolo_done=False)
            extractor.get_table_xlsx_results()


    except Exception as e:
        # Error handling
        logger.error(f"Error in processing PDF {filename}: {e}")
        asyncio.run(manager.send_json({
            "filename": filename,
            "status": "error",
            "detail": str(e)
        }))
        raise e
