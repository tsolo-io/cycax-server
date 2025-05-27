# SPDX-FileCopyrightText: 2025 Tsolo.io
#
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("tests/environment")

# Create the working directory
var = Path(os.environ["CYCAX_VAR_DIR"])
var.mkdir(exist_ok=True, parents=True)
