import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s]: %(message)s')

project_name = "app"

list_of_files = [
    f"{project_name}/__init__.py",
    f"{project_name}/main.py",
    f"{project_name}/routes.py",
    f"{project_name}/db_helper.py",
    f"{project_name}/whisper_helper.py",
    f"{project_name}/image_processor.py",
    f"{project_name}/langchain_helper.py",
    f"{project_name}/utils.py",
    f"{project_name}/config.py",
    "data/uploads/.gitkeep",              # To keep empty folders in Git
    "data/sample_inputs/.gitkeep",
    "sql/schema.sql",
    "tests/test_endpoints.py",
    "research/trials.ipynb",
    ".env",
    "requirements.txt",
    "README.md"
]

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Creating directory: {filedir} for the file: {filename}")

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass
        logging.info(f"Creating empty file: {filepath}")
    else:
        logging.info(f"{filename} already exists")
