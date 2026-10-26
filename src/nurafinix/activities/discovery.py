"""
Discovery activities for candidate business import and normalization.
"""

import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import mistralai.workflows as workflows

from ..models.prospect import BusinessRecord, CandidateBusiness

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryConfig:
    """Configuration for discovery activities."""
    csv_path: str | None = None
    csv_content: str | None = None
    batch_size: int = 10
    max_candidates: int = 100


@workflows.activity.define(
    name="import_csv",
    retry_policy=workflows.RetryPolicy(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=300,
)
async def import_csv(config: DiscoveryConfig) -> list[BusinessRecord]:
    """
    Import business records from a CSV file.
    
    Expected CSV columns:
    - name (required): Business name
    - website (required): Business website URL
    - industry (optional): Industry category
    - location (optional): Physical location
    - size (optional): Company size
    - description (optional): Business description
    - source (optional): Source of the record
    """
    logger.info(f"Importing CSV from: {config.csv_path}")
    
    content = config.csv_content
    if config.csv_path:
        path = Path(config.csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {config.csv_path}")
        content = path.read_text(encoding="utf-8")
    
    if not content:
        logger.warning("No CSV content provided")
        return []
    
    records = []
    try:
        reader = csv.DictReader(StringIO(content))
        for row_num, row in enumerate(reader, start=2):  # start=2 for 1-indexed line numbers
            # Validate required fields
            name = row.get("name", "").strip()
            website = row.get("website", "").strip()
            
            if not name:
                logger.warning(f"Row {row_num}: Skipping record with empty name")
                continue
            if not website:
                logger.warning(f"Row {row_num}: Skipping record '{name}' with empty website")
                continue
            
            # Clean website URL
            website = website.rstrip("/")
            if not website.startswith(("http://", "https://")):
                website = f"https://{website}"
            
            record = BusinessRecord(
                id=f"csv-{row_num}",
                name=name,
                website=website,
                industry=row.get("industry", "").strip() or None,
                location=row.get("location", "").strip() or None,
                size=row.get("size", "").strip() or None,
                description=row.get("description", "").strip() or None,
                source=row.get("source", "csv_import").strip(),
                imported_at=datetime.utcnow().isoformat() + "Z",
                raw_data=row,
            )
            records.append(record)
            
            if len(records) >= config.max_candidates:
                logger.info(f"Reached max candidates limit: {config.max_candidates}")
                break
        
        logger.info(f"Imported {len(records)} records from CSV")
        
    except csv.Error as e:
        logger.error(f"CSV parsing error: {e}")
        raise
    
    return records


@workflows.activity.define(
    name="normalize_businesses",
    retry_policy=workflows.RetryPolicy(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=60,
)
async def normalize_businesses(records: list[BusinessRecord]) -> list[CandidateBusiness]:
    """
    Normalize business records into candidate format.
    
    Normalization includes:
    - Standardizing website URLs
    - Cleaning up whitespace
    - Extracting domain names
    - Setting default values
    """
    logger.info(f"Normalizing {len(records)} business records")
    
    candidates = []
    for record in records:
        # Extract domain from website
        website = record.website.rstrip("/")
        domain = website.replace("https://", "").replace("http://", "").split("/")[0].lower()
        
        candidate = CandidateBusiness(
            id=record.id,
            name=record.name.strip(),
            website=website,
            domain=domain,
            industry=record.industry,
            location=record.location,
            size=record.size,
            description=record.description,
            source=record.source,
            imported_at=record.imported_at,
            normalized_at=datetime.utcnow().isoformat() + "Z",
            status="new",
            tags=[],
        )
        candidates.append(candidate)
    
    logger.info(f"Normalized {len(candidates)} candidates")
    return candidates


@workflows.activity.define(
    name="deduplicate_businesses",
    retry_policy=workflows.RetryPolicy(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=60,
)
async def deduplicate_businesses(candidates: list[CandidateBusiness]) -> list[CandidateBusiness]:
    """
    Deduplicate candidates based on domain.
    
    When duplicates are found:
    - Keep the first occurrence
    - Merge any additional data from subsequent occurrences
    - Log the deduplication
    """
    logger.info(f"Deduplicating {len(candidates)} candidates")
    
    seen_domains: dict[str, CandidateBusiness] = {}
    duplicates_found = 0
    
    for candidate in candidates:
        domain = candidate.domain.lower()
        
        if domain in seen_domains:
            duplicates_found += 1
            existing = seen_domains[domain]
            
            # Merge additional data if present
            if candidate.industry and not existing.industry:
                existing.industry = candidate.industry
            if candidate.location and not existing.location:
                existing.location = candidate.location
            if candidate.size and not existing.size:
                existing.size = candidate.size
            if candidate.description and not existing.description:
                existing.description = candidate.description
            
            logger.info(
                f"Duplicate found: {candidate.name} ({domain}) "
                f"- merged with existing {existing.name}"
            )
            continue
        
        seen_domains[domain] = candidate
    
    deduplicated = list(seen_domains.values())
    logger.info(
        f"Deduplicated: {len(candidates)} -> {len(deduplicated)} "
        f"({duplicates_found} duplicates removed)"
    )
    
    return deduplicated


@workflows.activity.define(
    name="batch_candidates",
    retry_policy=workflows.RetryPolicy(
        max_attempts=2,
        initial_delay=0.5,
        max_delay=5.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=30,
)
async def batch_candidates(
    candidates: list[CandidateBusiness],
    batch_size: int = 5,
) -> list[list[CandidateBusiness]]:
    """
    Split candidates into batches for parallel processing.
    """
    logger.info(f"Batching {len(candidates)} candidates into groups of {batch_size}")
    
    batches = [
        candidates[i : i + batch_size]
        for i in range(0, len(candidates), batch_size)
    ]
    
    logger.info(f"Created {len(batches)} batches")
    return batches
