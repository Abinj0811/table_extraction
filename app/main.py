#main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import shutil
import os
import asyncio
# from celery import shared_task
import logging
from app.services.pdf_handler import PDFHandler , process_multiple_pdfs
# from app.tasks import process_pdf
from app.services.connection_manager import manager
import websockets
import logging

# Configure the logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Check if logger already has handlers to avoid duplicate logs
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
app = FastAPI()

# Allow all origins with necessary methods and headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)



UPLOAD_DIRECTORY = "./app/uploaded_pdfs"
IMAGE_DIRECTORY = "./app/images"
EXCEL_DIRECTORY = "./app/out_excel"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
ALLOWED_FILE_TYPES = ["application/pdf"]
DETECTION_OUTPUT = "./app/detection_out"

def clear_directories():
    """Deletes specified directories if they exist."""
    for directory in [UPLOAD_DIRECTORY, IMAGE_DIRECTORY, EXCEL_DIRECTORY,DETECTION_OUTPUT]:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory, exist_ok=True)

# Helper function to save files
def save_file(file: UploadFile):
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return file_path


# @app.websocket("/ws/progress")
# async def websocket_endpoint(websocket: WebSocket):
#     await manager.connect(websocket)
#     try:
#         while True:
#             data = await websocket.receive_text()  # Keep connection open
#             if data == 'Success':
#                 try:
#                     pdf_path_list = [os.path.join(UPLOAD_DIRECTORY, files) for files in os.listdir(UPLOAD_DIRECTORY)]
#                     await process_multiple_pdfs(pdf_path_list)
                        
#                 except Exception as e:
#                     logger.error(f"An error occurred: {e}")

#     except WebSocketDisconnect:
#         manager.disconnect(websocket)

task_complete = False
async def heartbeat(websocket: WebSocket, interval: int = 20):
    try:
        while not task_complete:
            try:
                await websocket.send_json({"msg": "ping"})
            except websockets.exceptions.ConnectionClosedError:
                # Handle the case when connection is already closed
                logger.warning("Connection closed while sending ping.")
                break
            except Exception as e:
                logger.warning(f"Heartbeat exception: {e}")
                break  # Break out of the loop in case of other errors
            await asyncio.sleep(interval)
    except websockets.exceptions.ConnectionClosedError as e:
        # Handle WebSocket closure errors
        logger.error(f"WebSocket connection closed: {e}")
    except asyncio.exceptions.CancelledError:
        # Handle task cancellation gracefully
        logger.warning("Heartbeat task was canceled.")
    except Exception as e:
        logger.error(f"Heartbeat exception: {e}")


@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    heartbeat_task = asyncio.create_task(heartbeat(websocket, interval=10))

    try:
        while True:
            try:
                data = await websocket.receive_text()
                if data == 'Success':
                    try:
                        pdf_path_list = [os.path.join(UPLOAD_DIRECTORY, files) for files in os.listdir(UPLOAD_DIRECTORY)]
                        await process_multiple_pdfs(pdf_path_list)
                        global task_complete
                        task_complete = True 
                        logger.info("PDF processing completed.")
                    except Exception as e:
                        logger.error(f"PDF processing error: {e}")
            except Exception as e:
                logger.warning(f"Data receive error: {e}")
                break  # Break to close connection on repeated issues
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed by client.")
    finally:
        manager.disconnect(websocket)
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            logger.info("Heartbeat task cancelled.")



@app.post("/upload-pdfs/")
async def upload_files(files: List[UploadFile]):
    clear_directories()
    file_names = []
    for file in files:
        logger.info(f"Received file: {file.filename}")  # Debug line
        filename = save_file(file)
        file_names.append(filename)
        # process_pdf.delay(filename)  # This should queue the task , use only when celery and redis is used.
        logger.info(f"Task queued for processing: {filename}")  # Debug line
    return {"message": "Success", "files": file_names}



# Endpoint to start PDF processing with Celery
@app.post("/start-pdf-processing/")
async def start_pdf_processing(filename: str):
    """Trigger PDF processing with Celery."""
    try:
        # Trigger the Celery task
        task = process_pdf.delay(filename)
        return JSONResponse(content={"task_id": task.id, "status": "Task started"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

# Endpoint to get the task status
@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Check the status of a Celery task."""
    task = process_pdf.AsyncResult(task_id)
    if task.state == "PENDING":
        return {"status": "Pending"}
    elif task.state == "PROGRESS":
        return {"status": "In progress", "progress": task.info}
    elif task.state == "SUCCESS":
        return {"status": "Completed", "result": task.result}
    else:
        return {"status": task.state, "info": str(task.info)}
    

@app.get("/ok")
def ok_upload():
    try:
        pdf_path_list = [os.path.join(UPLOAD_DIRECTORY, files) for files in os.listdir(UPLOAD_DIRECTORY)]
        print(pdf_path_list)
        process_multiple_pdfs(pdf_path_list)

    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
        ws_ping_interval=20,   # Interval between pings in seconds
        ws_ping_timeout=60,      # Timeout before considering connection inactive
        timeout_keep_alive=60  # Timeout for keeping a connection alive
    )   

