#utils/pdf_to_images.py
import os
import pdfplumber
import subprocess
import logging

class PDFToImages:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        self.img_dir = os.path.join('./app/images', self.pdf_name)
        logging.info(f"Images will be saved in directory: {self.img_dir}")
        os.makedirs(self.img_dir, exist_ok=True)

    def get_pdf_page_count(self) -> int:
        with pdfplumber.open(self.pdf_path) as pdf:
            return len(pdf.pages)
        
    
    def gs_pdf_to_jpg(self, pages_to_show: list = None) -> list:
        if pages_to_show is None:
            pages_to_show = list(range(1, self.get_pdf_page_count() + 1))

        converted_images = []
        total_pages = self.get_pdf_page_count()

        for page_num in pages_to_show:
            if page_num <= total_pages:
                output_file_path = os.path.join(self.img_dir, f"page_{page_num:03d}.jpg")
                if not os.path.exists(output_file_path):
                    gs_command = [
                        "gs",
                        "-dNOPAUSE",
                        "-dBATCH",
                        "-sDEVICE=jpeg",
                        "-r300",
                        "-dUseCropBox",
                        f"-dFirstPage={page_num}",
                        f"-dLastPage={page_num}",
                        f"-sOutputFile={output_file_path}",
                        self.pdf_path
                    ]
                    try:
                        subprocess.run(gs_command, check=True)
                        converted_images.append(output_file_path)
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Failed to convert page {page_num} to image: {str(e)}")
            else:
                logging.error(f"Page {page_num} is out of range. The document has {total_pages} pages.")

        return converted_images, self.img_dir
        
