"""04 · document_loader — Extract and load documents into LangChain Document instances.

Provides loaders for local filesystem operations, wrapping text records with clean
metadata schema (source, policy_category, local_path) into standard LangChain Document objects.

Cloud Storage (GCS) functions are documented and commented out below, as the project
is configured to run 100% offline and cost-free using the local filesystem.
"""

import glob
import json
import logging
import os
from typing import List, Optional, Tuple

from langchain_core.documents import Document

from hr_assistant import config

logger = logging.getLogger(__name__)


# ============================================================================
# Metadata Extraction Utilities (Active)
# ============================================================================

def extract_policy_category(text: str) -> str:
    """Extract policy category from the document header lines.

    Inspects the first 5 lines for 'Policy Category: X' or 'Category: X'.
    This enables dynamic metadata tagging directly from file text.

    Args:
        text: Raw text content of the document.

    Returns:
        The extracted category string, or 'Unknown' if no matching header is found.
    """
    for line in text.splitlines()[:5]:
        stripped = line.strip().lower()
        if stripped.startswith("policy category:"):
            return line.split(":", 1)[1].strip()
        if stripped.startswith("category:"):
            return line.split(":", 1)[1].strip()
    return "Unknown"


# ============================================================================
# Local Filesystem Document Loaders (Active - Zero-Cost Offline Pipeline)
# ============================================================================

def load_documents_from_local(
    policies_dir: str = os.path.join("data", "policies"),
) -> List[Document]:
    """Load raw .txt policies directly from local filesystem.

    Reads all .txt files from the specified directory, extracts the policy category
    from header lines, and packages each into a LangChain Document instance.

    Args:
        policies_dir: Path to directory containing raw policy .txt files.

    Returns:
        List of LangChain Document instances with populated metadata.
    """
    documents: List[Document] = []
    pattern = os.path.join(policies_dir, "*.txt")

    for file_path in glob.glob(pattern):
        if not os.path.isfile(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        filename = os.path.basename(file_path)
        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": filename,
                    "policy_category": extract_policy_category(text),
                    "local_path": file_path,
                },
            )
        )

    logger.info("Loaded %d raw documents from %s", len(documents), policies_dir)
    return documents


def load_processed_documents_from_local(
    subdirs: Tuple[str, ...] = ("hr-policies", "other-data"),
    processed_dir: str = os.path.join("data", "processed"),
) -> List[Document]:
    """Read processed JSON records written by the processor module from local disk.

    Each JSON file contains pre-extracted text and metadata generated during
    the multi-format binary parsing phase.

    Args:
        subdirs: Subdirectories inside processed_dir to load records from.
        processed_dir: Root directory of processed JSON files.

    Returns:
        List of LangChain Document objects reconstructed from JSON records.
    """
    documents: List[Document] = []

    for subdir in subdirs:
        folder_path = os.path.join(processed_dir, subdir)
        if not os.path.exists(folder_path):
            logger.warning("Processed directory not found: %s", folder_path)
            continue

        for file_path in glob.glob(os.path.join(folder_path, "*.json")):
            with open(file_path, "r", encoding="utf-8") as fp:
                record = json.load(fp)

            documents.append(
                Document(
                    page_content=record["text"],
                    metadata={
                        "source": record["source"],
                        "policy_category": record.get("policy_category", "Unknown"),
                        "local_path": record.get("local_path", file_path),
                    },
                )
            )

    logger.info("Loaded %d processed documents from %s", len(documents), processed_dir)
    return documents


# ============================================================================
# Google Cloud Storage (GCS) Loaders (Inactive - Requires Cloud Billing)
#
# NOTE: The functions below represent the cloud-native loaders demonstrated
# in the course video. They require an active Google Cloud Platform project,
# Cloud Storage billing, and service account credentials.
# Because we are running 100% offline and cost-free, these are commented out.
# ============================================================================

# def load_documents_from_gcs(
#     bucket_name: str = config.GCS_BUCKET_NAME,
#     prefix: str = config.GCS_PREFIX,
# ) -> List[Document]:
#     """Download and wrap .txt files under given GCS prefix into LangChain Documents.
#
#     Connects to Google Cloud Storage using google.cloud.storage.Client,
#     lists all .txt blobs matching the prefix, downloads their text,
#     and constructs LangChain Document objects with GCS URI metadata.
#
#     Args:
#         bucket_name: Name of the Google Cloud Storage bucket.
#         prefix: Blob prefix / folder path inside the bucket.
#
#     Returns:
#         List of LangChain Document instances.
#     """
#     from google.cloud import storage
#     client = storage.Client(project=config.PROJECT_ID)
#     bucket = client.bucket(bucket_name)
#
#     documents: List[Document] = []
#     for blob in bucket.list_blobs(prefix=prefix):
#         if not blob.name.endswith(".txt"):
#             continue
#         text = blob.download_as_text()
#         filename = blob.name.rsplit("/", 1)[-1]
#         documents.append(
#             Document(
#                 page_content=text,
#                 metadata={
#                     "source": filename,
#                     "policy_category": extract_policy_category(text),
#                     "gcs_path": f"gs://{bucket_name}/{blob.name}",
#                 },
#             )
#         )
#     return documents


# def load_processed_documents_from_gcs(
#     bucket_name: str = config.GCS_BUCKET_NAME,
#     prefixes: Tuple[str, ...] = (config.PROCESSED_HR_PREFIX, config.PROCESSED_NOISE_PREFIX),
# ) -> List[Document]:
#     """Read processed JSON records written by the processor module from GCS.
#
#     Downloads pre-parsed JSON records from cloud buckets, extracting the plain text
#     and source metadata into LangChain Document instances for indexing.
#
#     Args:
#         bucket_name: Name of the Google Cloud Storage bucket.
#         prefixes: Tuple of GCS prefixes to search for processed JSON files.
#
#     Returns:
#         List of LangChain Document instances.
#     """
#     from google.cloud import storage
#     client = storage.Client(project=config.PROJECT_ID)
#     bucket = client.bucket(bucket_name)
#
#     documents: List[Document] = []
#     for prefix in prefixes:
#         for blob in bucket.list_blobs(prefix=prefix):
#             if not blob.name.endswith(".json"):
#                 continue
#             record = json.loads(blob.download_as_text())
#             documents.append(
#                 Document(
#                     page_content=record["text"],
#                     metadata={
#                         "source": record["source"],
#                         "policy_category": record.get("policy_category", "Unknown"),
#                         "gcs_path": record.get("raw_gcs_path", ""),
#                     },
#                 )
#             )
#     return documents
