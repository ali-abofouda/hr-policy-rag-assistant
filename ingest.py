"""16 · ingest.py — Command-line interface (CLI) to run the data ingestion pipeline.

This script orchestrates the end-to-end ingestion of HR policy documents into Qdrant:
    1. Reads documents directly from local disk (data/policies and data/processed).
    2. Splits documents into optimized, overlapping text chunks.
    3. Computes dense embeddings (Jina) and sparse vectors (BM25 via FastEmbed).
    4. Upserts vectors and metadata into Qdrant vector database.

Zero-Cloud / Cost-Free Architecture:
    Runs 100% on the local filesystem without Google Cloud Storage (GCS) or GCP billing.

CLI Usage Examples:
    python ingest.py               # Ingest clean HR policies (skips if already populated)
    python ingest.py --force       # Rebuild collections from scratch
    python ingest.py --hr-only     # Ingest only the clean HR policies collection
    python ingest.py --noisy-only  # Ingest only the mixed/noisy benchmark collection
"""

import argparse
import sys

from src.ingestion.ingestion import run_ingestion
from src.core.logging import configure_logging


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command-line options for the ingestion pipeline.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild Qdrant collections from scratch even if points already exist.",
    )

    # Mutually exclusive group for target collection scope
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument(
        "--hr-only",
        action="store_true",
        help="Ingest only the clean HR policy collection (default behaviour).",
    )
    scope_group.add_argument(
        "--noisy-only",
        action="store_true",
        help="Ingest only the mixed HR + noise benchmark collection.",
    )

    # Kept for backward compatibility with course scripts (no-op in local mode)
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Legacy flag. Cloud upload is disabled by default in local mode.",
    )

    return parser.parse_args()


def main() -> None:
    """Main execution entry point."""
    configure_logging()
    args = parse_arguments()

    # Determine collection targets based on CLI flags
    if args.noisy_only:
        hr = False
        noisy = True
    elif args.hr_only:
        hr = True
        noisy = False
    else:
        # Default: ingest clean HR policies
        hr = True
        noisy = False

    try:
        run_ingestion(
            force=args.force,
            hr=hr,
            noisy=noisy,
        )
        print("\n[SUCCESS] Ingestion pipeline finished successfully.")
    except Exception as exc:
        print(f"\n[ERROR] Ingestion failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
