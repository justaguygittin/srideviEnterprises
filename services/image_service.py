"""
=========================================================
Project : Sridevi Enterprises
File    : image_service.py
Purpose : Product image validation, storage, and cleanup.

Author  : Srikar
=========================================================
"""

import os
import shutil
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
MIN_IMAGES = 1
MAX_IMAGES = 10

_UPLOAD_SUBPATH = os.path.join("uploads", "products")


def validate_image_files(files: list[FileStorage]) -> str | None:
    """Return the first validation error for a product's image uploads, or None."""

    submitted_files = [file for file in files if file and file.filename]

    if len(submitted_files) < MIN_IMAGES:
        return "Please attach at least one product image."
    if len(submitted_files) > MAX_IMAGES:
        return f"You can upload at most {MAX_IMAGES} images per product."

    for file in submitted_files:
        extension = _get_extension(file.filename)
        if extension not in ALLOWED_EXTENSIONS:
            return f"'{file.filename}' is not a supported image type (JPG, JPEG, PNG, WEBP only)."

        if _file_size(file) > MAX_IMAGE_SIZE_BYTES:
            return f"'{file.filename}' exceeds the 10MB size limit."

    return None


def save_product_images(product_id: int, files: list[FileStorage]) -> list[str]:
    """Save validated image files to disk and return their static-relative paths."""

    submitted_files = [file for file in files if file and file.filename]

    product_folder = os.path.join(current_app.static_folder, _UPLOAD_SUBPATH, str(product_id))
    os.makedirs(product_folder, exist_ok=True)

    saved_paths = []
    for file in submitted_files:
        extension = _get_extension(file.filename)
        filename = secure_filename(f"{product_id}_{uuid4().hex}.{extension}")
        file.save(os.path.join(product_folder, filename))
        saved_paths.append(f"uploads/products/{product_id}/{filename}")

    return saved_paths


def delete_product_folder(product_id: int) -> None:
    """Remove a product's entire upload folder, ignoring a missing folder."""

    product_folder = os.path.join(current_app.static_folder, _UPLOAD_SUBPATH, str(product_id))
    shutil.rmtree(product_folder, ignore_errors=True)


def _get_extension(filename: str) -> str:
    """Return a filename's lowercased extension without the leading dot."""

    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _file_size(file: FileStorage) -> int:
    """Return a FileStorage's byte size without consuming its stream."""

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    return size
