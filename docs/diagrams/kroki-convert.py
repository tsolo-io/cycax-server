#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Tsolo.io
#
# SPDX-License-Identifier: Apache-2.0

# Convert diagram source files to image files.

import base64
import hashlib
import json
import logging
import sys
import zlib
from pathlib import Path

import httpx

KROKI_ORIGIN = "http://localhost:8866"
KROKI_TSOLO = "https://kroki.tu.tsolo.net"
KROKI_IO = "https://kroki.io"

FORMATS = (
    "BlockDiag",
    "SeqDiag",
    "ActDiag",
    "NwDiag",
    "PacketDiag",
    "RackDiag",
    "BPMN",
    "Bytefield",
    "D2",
    "DBML",
    "Ditaa",
    "Erd",
    "Excalidraw",
    "GraphViz",
    "Mermaid",
    "Nomnoml",
    "Pikchr",
    "PlantUML",
    "Structurizr",
    "SvgBob",
    "Symbolator",
    "TikZ",
    "UMLet",
    "Vega",
    "Vega-Lite",
    "WaveDrom",
    "WireViz",
)

FILE_PREFIX_TO_FORMAT_MAP = {name.lower(): name.lower() for name in FORMATS}
FILE_PREFIX_TO_FORMAT_MAP["puml"] = "plantuml"
FILE_PREFIX_TO_FORMAT_MAP["c4"] = "plantuml"

IMG_FORMAT = "svg"

logging.getLogger().setLevel(logging.INFO)


class ReproccessChecker:
    """Check if the diagrams should be created.

    A file in the source directory stores the MD5 of the source files,
    if the files MD5 is different to the stored MD5 then the image is created.
    If there are no image file the image file will be created.

    Attributes:
        source_dir: The path where the reference file is stored.
    """

    def __init__(self, source_dir: Path):
        self.reference_file = source_dir / ".kroki_remember"
        self.reference = self.load()
        self._temp_ref = {}

    def load(self):
        """Load the file references."""
        if not self.reference_file.exists():
            return {}
        return json.loads(self.reference_file.read_text())

    def save(self):
        """Save the file references."""
        self.reference_file.write_text(json.dumps(self.reference))

    def need_update(self, source_file: Path, target_file: Path) -> bool:
        """Check if there is an update necessary.

        Args:
            source_file: The diagram source file.
            target_file: The target image file.
        """
        if not target_file.exists():
            logging.warn("There is no target file, thus update is required.")
            return True
        real_value = hashlib.md5(source_file.read_bytes()).hexdigest()  # noqa: S324
        self._temp_ref[str(source_file)] = real_value
        ref_value = self.reference.get(str(source_file))
        if not ref_value:
            logging.warn("There is no entry in reference for this file, thus update is required.")
            return True

        if real_value == ref_value:
            return False
        else:
            logging.warn("The file has changed, thus update is required.")
            return True

    def updated(self, source_file: Path):
        """Update the reference for the source_file.

        This does not save the references.

        Args:
            source_file: The diagram source file.
        """
        real_val = self._temp_ref.get(str(source_file))
        if real_val:
            self.reference[str(source_file)] = real_val
        else:
            logging.error("There is no value for %s in temp_val %s", source_file, self._temp_ref)


def get_path(no: int) -> Path:
    """Get a path from the command line as a positional argument.

    Args:
        no: The position of the argument. Starting at 1.

    Returns:
        The absolute and expanded path.
    """
    _dir = sys.argv[no]
    if _dir:
        dir_path = Path(_dir).expanduser().resolve().absolute()
        return dir_path


def fetch_image(address, source_format: str, data_file: Path, image_file: Path) -> bool:
    """Reads a data file and convert it to an image with Kroki.

    Args:
        address: Address of the Kroki server.
        source_format: The format of the data_file.
        data_file: The source file for the diagram.
        image_file: Where the image should be stored.
    """
    data = data_file.read_text().encode()
    b64data = base64.urlsafe_b64encode(zlib.compress(data, 9)).decode("ascii")

    for _ in range(4):
        try:
            reply = httpx.get(f"{address}/{source_format}/{IMG_FORMAT}/{b64data}")
        except httpx.ConnectError as error:
            raise error
        except httpx.HTTPError as error:
            logging.error(error)

        if reply.status_code == httpx.codes.OK:
            image_file.write_bytes(reply.content)
            logging.info(f"Read {data_file} -> Write {image_file}")
            return True
    return False


if __name__ == "__main__":
    source_dir = get_path(1)
    target_dir = get_path(2)

    logging.info("Reading diagrams source files from %s", source_dir)
    logging.info("Over writing diagrams image files in %s", target_dir)
    check = ReproccessChecker(source_dir)
    kroki_address = [KROKI_ORIGIN, KROKI_TSOLO, KROKI_IO]
    try:
        while kroki_address:
            try:
                for file in source_dir.iterdir():
                    src_format = FILE_PREFIX_TO_FORMAT_MAP.get(file.suffix.strip("."))
                    if src_format:
                        image = target_dir / f"{file.name}.{IMG_FORMAT}"
                        if check.need_update(file, image):
                            saved = fetch_image(kroki_address[0], src_format, file, image)
                            if saved:
                                check.updated(file)
            except httpx.ConnectError:
                addr = kroki_address.pop(0)
                logging.error("Cannot connect to %s", addr)
            else:
                # Exit the while loop if we are finished with all the files.
                break
    except Exception:
        msg = f"File {file}"
        logging.exception(msg)
    check.save()
