import os
from pathlib import Path

# Default paths
DEFAULT_TABLE_MODEL_PATH = os.path.join(Path(__file__).parent.parent, "models", "best_tables.pt")
DEFAULT_MAKERS_MODEL_PATH = os.path.join(Path(__file__).parent.parent, "models", "best_makers.pt")

# Output directories
OUTPUT_BASE_DIR = "output"
# JSON_OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "json_output")
# EXCEL_OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "excel_output")
DETECTION_OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "detection_out")

# Create output directories if they don't exist
for directory in [OUTPUT_BASE_DIR,DETECTION_OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)

# Processing parameters
DEFAULT_SIMILARITY_PERCENTAGE = 90
DEFAULT_REMOVAL_PERCENTAGE = 50