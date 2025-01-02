import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("tests/environment")

# Create the working directory
var = Path(os.environ["CYCAX_VAR_DIR"])
var.mkdir(exist_ok=True, parents=True)
