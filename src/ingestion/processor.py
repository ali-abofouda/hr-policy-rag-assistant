"""05 · processor — Multi-format binary parser converting raw documents to plain text.

Parses PDF, DOCX, and PPTX formats into standardized JSON records.
Implements the "Parse Once to JSON" architectural pattern: heavy binary extraction
is decoupled from downstream RAG indexing, producing clean, uniform JSON payloads.

Cloud Storage (GCS) functions are documented and commented out below, as the project
is configured to run 100% offline and cost-free using the local filesystem.
"""

import glob
import io
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

from docx import Document as DocxReader
from pptx import Presentation
from pypdf import PdfReader

from src.core import config
from src.ingestion.document_loader import extract_policy_category

logger = logging.getLogger(__name__)

# Mapping from raw storage prefixes to processed output prefixes (used in GCS pipeline)
_RAW_TO_PROCESSED: Dict[str, str] = {
    config.GCS_PREFIX: config.PROCESSED_HR_PREFIX,
    config.NOISE_GCS_PREFIX: config.PROCESSED_NOISE_PREFIX,
}


# ============================================================================
# Binary Stream Parsers (Active - Format Specific Text Extractors)
# ============================================================================

def _parse_pdf(raw_bytes: bytes) -> str:
    """Extract plain text from all pages of a PDF document.

    Args:
        raw_bytes: In-memory byte array of the PDF file.

    Returns:
        Consolidated plain text separated by newlines across all pages.
    """
    # Wrap in-memory byte buffer into a seekable file-like object
    reader = PdfReader(io.BytesIO(raw_bytes))
    # Extract text from every page sequentially, defaulting to empty string on blank pages
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_docx(raw_bytes: bytes) -> str:
    """Extract plain text from paragraphs in a Microsoft Word (.docx) document.

    Args:
        raw_bytes: In-memory byte array of the DOCX file.

    Returns:
        Consolidated text from all body paragraphs joined by newlines.
    """
    doc = DocxReader(io.BytesIO(raw_bytes))
    # Collect text content from each paragraph node in the Word XML tree
    return "\n".join(p.text for p in doc.paragraphs)


def _parse_pptx(raw_bytes: bytes) -> str:
    """Extract titles and slide body text frames across all PowerPoint (.pptx) slides.

    Args:
        raw_bytes: In-memory byte array of the PPTX file.

    Returns:
        Consolidated text from slide titles and body shapes joined by newlines.
    """
    prs = Presentation(io.BytesIO(raw_bytes))
    lines = []
    for slide in prs.slides:
        # Extract title shape text first if present
        if slide.shapes.title is not None:
            lines.append(slide.shapes.title.text)
        # Iterate over all remaining slide shapes containing text frames
        for shape in slide.shapes:
            if shape.has_text_frame and shape != slide.shapes.title:
                lines.append(shape.text_frame.text)
    return "\n".join(lines)


# Dispatch table mapping lowercased file extensions to their corresponding parser callable
_PARSERS: Dict[str, Callable[[bytes], str]] = {
    ".pdf": _parse_pdf,
    ".docx": _parse_docx,
    ".pptx": _parse_pptx,
}


# ============================================================================
# Local Filesystem Parsing & Ingestion (Active - Zero-Cost Offline Pipeline)
# ============================================================================

def parse_file(file_path: str) -> str:
    """Parse a single file from local disk based on its extension.

    Handles UTF-8 plain text natively and routes binary extensions (.pdf, .docx, .pptx)
    to specialized byte parsers.

    Args:
        file_path: Absolute or relative path to the local document.

    Returns:
        Extracted plain text content.

    Raises:
        ValueError: If the file extension is not supported in the parser registry.
    """
    ext = os.path.splitext(file_path)[1].lower()
    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    # Plain text files can be decoded directly without third-party binary engines
    if ext == ".txt":
        return raw_bytes.decode("utf-8", errors="replace")

    # Dispatch binary bytes to the registered parser
    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(
            f"No parser registered for file extension {ext!r} ({file_path})"
        )
    return parser(raw_bytes)


def process_local_raw_to_json(
    data_dir: str = "data",
    output_dir: str = os.path.join("data", "processed"),
) -> int:
    """Parse all local raw files (HR policies + noise) and save as JSON records.

    This implements the 'Parse Once to JSON' architectural pattern:
    1. Scans raw HR policies (txt) and noise files (pdf, docx, pptx, txt).
    2. Extracts clean plain text and header metadata.
    3. Serializes each document into an intermediate JSON record in data/processed/.

    Args:
        data_dir: Root directory containing raw input subdirectories ('policies', 'noise').
        output_dir: Target directory where processed JSON records will be written.

    Returns:
        Total number of successfully parsed and saved documents.
    """
    count = 0
    # Directory routing: raw subfolder -> processed destination subfolder
    subdirs = [
        ("policies", os.path.join(output_dir, "hr-policies")),
        ("noise", os.path.join(output_dir, "other-data")),
    ]

    for source_sub, target_sub in subdirs:
        source_path = os.path.join(data_dir, source_sub)
        os.makedirs(target_sub, exist_ok=True)

        for file_path in glob.glob(os.path.join(source_path, "*")):
            if not os.path.isfile(file_path):
                continue

            filename = os.path.basename(file_path)
            try:
                # Extract raw text content through format dispatch
                text = parse_file(file_path)
            except Exception as exc:
                logger.warning("Failed to parse %s: %s", filename, exc)
                continue

            # Standardized intermediate schema decoupling parsing from indexing
            record = {
                "source": filename,
                "policy_category": extract_policy_category(text),
                "text": text,
                "local_path": file_path,
            }

            processed_filename = os.path.splitext(filename)[0] + ".json"
            target_file = os.path.join(target_sub, processed_filename)

            with open(target_file, "w", encoding="utf-8") as out_fp:
                json.dump(record, out_fp, indent=2, ensure_ascii=False)

            logger.info("Processed: %s -> %s", filename, processed_filename)
            count += 1

    return count


def process_raw_to_json(data_dir: str = "data") -> int:
    """Main processing entry point.

    Executes local multi-format parsing, converting all raw files into
    standardized JSON records in data/processed/.

    Args:
        data_dir: Root directory containing raw files.

    Returns:
        Total count of processed JSON files created.
    """
    return process_local_raw_to_json(data_dir=data_dir)


# ============================================================================
# Google Cloud Storage (GCS) Pipeline (Inactive - Requires Cloud Billing)
#
# NOTE: The functions below represent the cloud-native pipeline demonstrated
# in the course video. They require an active Google Cloud Platform project,
# Cloud Storage billing, and service account credentials.
# Because we are running 100% offline and cost-free, these are commented out.
# ============================================================================

# def parse_blob(blob: Any) -> str:
#     """Download a GCS blob and return its extracted plain text.
#
#     Inspects the blob's file extension and routes the downloaded byte array
#     to the appropriate binary parser (_parse_pdf, _parse_docx, _parse_pptx)
#     or reads UTF-8 text directly.
#
#     Args:
#         blob: google.cloud.storage.blob.Blob instance.
#
#     Returns:
#         Extracted plain text content.
#     """
#     ext = "." + blob.name.rsplit(".", 1)[-1].lower() if "." in blob.name else ""
#     if ext == ".txt":
#         return blob.download_as_text()
#     parser = _PARSERS.get(ext)
#     if parser is None:
#         raise ValueError(f"No parser registered for file extension {ext!r} ({blob.name})")
#     return parser(blob.download_as_bytes())


# def process_raw_to_json_gcs(bucket_name: str = config.GCS_BUCKET_NAME) -> int:
#     """Parse raw documents from GCS buckets and upload processed JSON records back to GCS.
#
#     Workflow:
#     1. Connects to GCS bucket via google.cloud.storage.Client.
#     2. Iterates over blobs in raw-hr-policies/ and raw-other-data/.
#     3. Extracts text via parse_blob().
#     4. Enriches record with metadata (source, policy_category, raw_gcs_path).
#     5. Uploads resulting JSON payload to processed-hr-policies/ and processed-other-data/.
#
#     Args:
#         bucket_name: Google Cloud Storage bucket identifier.
#
#     Returns:
#         Number of processed records uploaded to GCS.
#     """
#     from google.cloud import storage
#     client = storage.Client(project=config.PROJECT_ID)
#     bucket = client.bucket(bucket_name)
#
#     count = 0
#     for raw_prefix, processed_prefix in _RAW_TO_PROCESSED.items():
#         for blob in bucket.list_blobs(prefix=raw_prefix):
#             filename = blob.name.rsplit("/", 1)[-1]
#             if "." not in filename:
#                 continue
#             text = parse_blob(blob)
#             record = {
#                 "source": filename,
#                 "policy_category": extract_policy_category(text),
#                 "text": text,
#                 "raw_gcs_path": f"gs://{bucket_name}/{blob.name}",
#             }
#
#             processed_name = filename.rsplit(".", 1)[0] + ".json"
#             processed_blob = bucket.blob(f"{processed_prefix}{processed_name}")
#             processed_blob.upload_from_string(
#                 json.dumps(record, indent=2), content_type="application/json"
#             )
#             logger.info("Uploaded processed: %s -> %s", blob.name, processed_blob.name)
#             count += 1
#     return count
