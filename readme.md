# Table Detection and Extraction

This project detects and extracts tables from PDF files, converting them into Excel format for easy data manipulation and analysis. It uses **FastAPI** for the API layer, **Celery** for task processing, and **Redis** as the message broker.

## Project Structure

```plaintext
app/
│
├── main.py                   # FastAPI app with WebSocket support
├── celery_worker.py          # Starts the Celery worker
├── tasks.py                  # Celery tasks for PDF processing
├── utils/
│   ├── pdf_to_images.py      # Class for processing PDF to image conversion
│   ├── table_detection.py    # Class for table detection
│   ├── textract_extractor.py # Class for textract , have functions for AWS and dedoc
│   ├── using_dedoc.py        # Class for dedoc table extraction and conversion to excel 
│   ├── merge_excel.py        # Function to merge the excel results to a single file (of single PDF) using dedoc
│   └── aws_merge_excel.py  # Function to merge the excel results to a single file (of single PDF) using dedoc
└── services/
    ├── pdf_handler.py        # PDFHandler class for processing PDFs
    └──  connection_manager.py     # Class for WebSocket updates
```
# Getting Started
## Step 1: Clone the Repository
```
mkdir table_extraction

cd table_extarction

git clone http://git.thinkpalm.info/TPMAIS10-GIT/TPMAIS10.git

cd TPMAIS10/

git checkout table_extarction_backend

```
## Step 2: Install Dependencies
Install the required packages listed in the __requirements.txt__ file.
```
pip install -r requirements.txt
```
## Step 3: Run the Project
To start the FastAPI application with Uvicorn, execute the following command from the TPMAIS10/ directory:
```
python -m app.main

```
# Running with Redis and Celery
To enable task processing with Celery and Redis, follow these steps:
### 1. Uncomment Celery Task Invocation
Uncomment the line __process_pdf.delay(filename)__ in __main.py__ under the __/upload-pdf__ endpoint.

### 2. Start Redis
In one terminal, start Redis from the TPMAIS10/ directory:
```
$ redis-server    
```
Note: If you encounter an **'address already in use'** issue, you may need to stop any existing Redis service with:
```
$ sudo systemctl stop redis
$ redis-server 
```
### 3. Monitor Redis (Optional)
To monitor Redis activity, open another terminal and run:
```
$ redis-cli monitor
```
### 4. Run Celery Worker
```
$ celery -A app.celery_app  worker --loglevel=info
```
### 5. Run FastAPI with Uvicorn
Start the FastAPI server again if it's not already running, from the TPMAIS10/ directory:
```
$ python -m app.main
```
