"""
Persistence activities for saving results and exporting data.
"""

import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import mistralai.workflows as workflows

from ..models.prospect import (
    CandidateBusiness,
    EvidenceRecord,
)
from ..models.scoring import ProspectScore
from ..models.outreach import OutreachDraft, ApprovalRequest
from ..models.pipeline import ProspectingResult

logger = logging.getLogger(__name__)


@dataclass
class PersistenceConfig:
    """Configuration for persistence."""
    output_dir: str = "./output"
    csv_dir: str = "./output/csv"
    json_dir: str = "./output/json"
    
    # CSV export options
    include_all_evidence: bool = True
    include_raw_data: bool = False


@dataclass
class ExportResult:
    """Result of an export operation."""
    path: str
    records_count: int
    success: bool
    error: str | None = None


def _flatten_evidence(evidence: list[EvidenceRecord]) -> dict[str, Any]:
    """Flatten evidence record for CSV export."""
    return {
        "evidence_id": evidence[0].id if evidence else "",
        "evidence_count": len(evidence),
        "evidence_categories": ", ".join(e.category.value for e in evidence[:3]),
        "evidence_summary": "; ".join(e.observation for e in evidence[:3]),
    }


def _flatten_score(score: ProspectScore | None) -> dict[str, Any]:
    """Flatten score for CSV export."""
    if not score:
        return {
            "score": 0,
            "score_customer_fit": 0,
            "score_demand": 0,
            "score_opportunity": 0,
            "score_contact": 0,
            "score_reliability": 0,
            "has_direct_demand": False,
            "has_verified_problem": False,
        }
    
    return {
        "score": score.total,
        "score_customer_fit": score.components.customer_fit,
        "score_demand": score.components.demand_evidence,
        "score_opportunity": score.components.opportunity,
        "score_contact": score.components.contact_channel,
        "score_reliability": score.components.evidence_reliability,
        "has_direct_demand": score.has_direct_demand,
        "has_verified_problem": score.has_verified_problem,
    }


@workflows.activity.define(
    name="save_results",
    retry_policy=workflows.RetryPolicy(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=60,
)
async def save_results(
    result: ProspectingResult,
    config: PersistenceConfig | None = None,
) -> list[ExportResult]:
    """
    Save prospecting results to disk.
    
    Saves:
    - Full JSON result
    - Individual JSON files for each candidate
    - Summary CSV
    """
    if config is None:
        config = PersistenceConfig()
    
    # Create output directories
    output_dir = Path(config.output_dir)
    csv_dir = Path(config.csv_dir)
    json_dir = Path(config.json_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    # Save full JSON
    json_path = output_dir / f"prospecting_result_{timestamp}.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2, default=str)
        
        results.append(ExportResult(
            path=str(json_path),
            records_count=len(result.candidates),
            success=True,
        ))
        logger.info(f"Saved full JSON to: {json_path}")
    except Exception as e:
        logger.error(f"Failed to save JSON: {e}")
        results.append(ExportResult(
            path=str(json_path),
            records_count=0,
            success=False,
            error=str(e),
        ))
    
    # Save individual candidate JSONs
    for candidate in result.candidates:
        candidate_path = json_dir / f"{candidate.id}.json"
        try:
            candidate_data = {
                "candidate": candidate.model_dump(),
                "evidence": [e.model_dump() for e in result.evidence_map.get(candidate.id, [])],
                "score": result.score_map.get(candidate.id).model_dump() if result.score_map.get(candidate.id) else None,
                "draft": result.draft_map.get(candidate.id).model_dump() if result.draft_map.get(candidate.id) else None,
                "approval_request": result.approval_map.get(candidate.id).model_dump() if result.approval_map.get(candidate.id) else None,
            }
            
            with open(candidate_path, "w", encoding="utf-8") as f:
                json.dump(candidate_data, f, indent=2, default=str)
            
            logger.info(f"Saved candidate JSON to: {candidate_path}")
        except Exception as e:
            logger.error(f"Failed to save candidate JSON for {candidate.id}: {e}")
    
    return results


@workflows.activity.define(
    name="export_csv",
    retry_policy=workflows.RetryPolicy(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=120,
)
async def export_csv(
    result: ProspectingResult,
    config: PersistenceConfig | None = None,
) -> list[ExportResult]:
    """
    Export results to CSV files.
    
    Exports:
    - candidates.csv: All candidate information
    - evidence.csv: All evidence records
    - scores.csv: All scores
    - drafts.csv: All outreach drafts
    - approvals.csv: All approval requests
    """
    if config is None:
        config = PersistenceConfig()
    
    csv_dir = Path(config.csv_dir)
    csv_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    # Export candidates
    candidates_path = csv_dir / f"candidates_{timestamp}.csv"
    try:
        with open(candidates_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Header
            header = [
                "candidate_id", "name", "website", "domain", "industry", "location",
                "size", "description", "source", "imported_at", "normalized_at",
                "status", "score", "has_direct_demand", "has_verified_problem",
                "qualified_at", "tags",
            ]
            
            # Add score fields
            score_fields = [
                "score", "score_customer_fit", "score_demand", "score_opportunity",
                "score_contact", "score_reliability",
            ]
            header.extend(score_fields)
            
            # Add evidence fields
            evidence_fields = [
                "evidence_id", "evidence_count", "evidence_categories", "evidence_summary",
            ]
            header.extend(evidence_fields)
            
            writer.writerow(header)
            
            # Data rows
            for candidate in result.candidates:
                score = result.score_map.get(candidate.id)
                evidence = result.evidence_map.get(candidate.id, [])
                
                score_data = _flatten_score(score)
                evidence_data = _flatten_evidence(evidence)
                
                row = [
                    candidate.id,
                    candidate.name,
                    candidate.website,
                    candidate.domain,
                    candidate.industry or "",
                    candidate.location or "",
                    candidate.size or "",
                    candidate.description or "",
                    candidate.source,
                    candidate.imported_at,
                    candidate.normalized_at,
                    candidate.status.value if candidate.status else "",
                    score.total if score else 0,
                    score.has_direct_demand if score else False,
                    score.has_verified_problem if score else False,
                    candidate.qualified_at or "",
                    "; ".join(candidate.tags) if candidate.tags else "",
                ]
                
                # Add score fields
                row.extend([
                    score_data["score"],
                    score_data["score_customer_fit"],
                    score_data["score_demand"],
                    score_data["score_opportunity"],
                    score_data["score_contact"],
                    score_data["score_reliability"],
                ])
                
                # Add evidence fields
                row.extend([
                    evidence_data["evidence_id"],
                    evidence_data["evidence_count"],
                    evidence_data["evidence_categories"],
                    evidence_data["evidence_summary"],
                ])
                
                writer.writerow(row)
        
        results.append(ExportResult(
            path=str(candidates_path),
            records_count=len(result.candidates),
            success=True,
        ))
        logger.info(f"Exported {len(result.candidates)} candidates to: {candidates_path}")
    except Exception as e:
        logger.error(f"Failed to export candidates CSV: {e}")
        results.append(ExportResult(
            path=str(candidates_path),
            records_count=0,
            success=False,
            error=str(e),
        ))
    
    # Export evidence
    evidence_path = csv_dir / f"evidence_{timestamp}.csv"
    try:
        all_evidence = []
        for candidate_id, evidence_list in result.evidence_map.items():
            for evidence in evidence_list:
                all_evidence.append({
                    "candidate_id": candidate_id,
                    **evidence.model_dump(),
                })
        
        if all_evidence:
            with open(evidence_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "candidate_id", "id", "category", "observation", 
                    "source_url", "timestamp", "verification_method",
                    "confidence", "status", "details",
                ])
                writer.writeheader()
                
                for item in all_evidence:
                    row = {k: v for k, v in item.items() if k in writer.fieldnames}
                    # Convert enum to string
                    if "category" in row and hasattr(row["category"], "value"):
                        row["category"] = row["category"].value
                    if "status" in row and hasattr(row["status"], "value"):
                        row["status"] = row["status"].value
                    if "verification_method" in row and hasattr(row["verification_method"], "value"):
                        row["verification_method"] = row["verification_method"].value
                    
                    # Convert details dict to string
                    if "details" in row and isinstance(row["details"], dict):
                        row["details"] = json.dumps(row["details"])
                    
                    writer.writerow(row)
            
            results.append(ExportResult(
                path=str(evidence_path),
                records_count=len(all_evidence),
                success=True,
            ))
            logger.info(f"Exported {len(all_evidence)} evidence records to: {evidence_path}")
    except Exception as e:
        logger.error(f"Failed to export evidence CSV: {e}")
        results.append(ExportResult(
            path=str(evidence_path),
            records_count=0,
            success=False,
            error=str(e),
        ))
    
    # Export scores
    scores_path = csv_dir / f"scores_{timestamp}.csv"
    try:
        all_scores = []
        for candidate_id, score in result.score_map.items():
            all_scores.append({
                "candidate_id": candidate_id,
                **score.model_dump(),
            })
        
        if all_scores:
            with open(scores_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "candidate_id", "total", "has_direct_demand", 
                    "has_verified_problem", "uncertainty", "reasons",
                    "supporting_evidence", "calculated_at",
                    "components_customer_fit", "components_demand_evidence",
                    "components_opportunity", "components_contact_channel",
                    "components_evidence_reliability",
                ])
                writer.writeheader()
                
                for item in all_scores:
                    row = {}
                    row["candidate_id"] = item.get("candidate_id", "")
                    row["total"] = item.get("total", 0)
                    row["has_direct_demand"] = item.get("has_direct_demand", False)
                    row["has_verified_problem"] = item.get("has_verified_problem", False)
                    row["uncertainty"] = item.get("uncertainty", "")
                    row["reasons"] = "; ".join(item.get("reasons", []))
                    row["supporting_evidence"] = ", ".join(item.get("supporting_evidence", []))
                    row["calculated_at"] = item.get("calculated_at", "")
                    
                    components = item.get("components", {})
                    if isinstance(components, dict):
                        row["components_customer_fit"] = components.get("customer_fit", 0)
                        row["components_demand_evidence"] = components.get("demand_evidence", 0)
                        row["components_opportunity"] = components.get("opportunity", 0)
                        row["components_contact_channel"] = components.get("contact_channel", 0)
                        row["components_evidence_reliability"] = components.get("evidence_reliability", 0)
                    
                    writer.writerow(row)
            
            results.append(ExportResult(
                path=str(scores_path),
                records_count=len(all_scores),
                success=True,
            ))
            logger.info(f"Exported {len(all_scores)} scores to: {scores_path}")
    except Exception as e:
        logger.error(f"Failed to export scores CSV: {e}")
        results.append(ExportResult(
            path=str(scores_path),
            records_count=0,
            success=False,
            error=str(e),
        ))
    
    # Export drafts
    drafts_path = csv_dir / f"drafts_{timestamp}.csv"
    try:
        all_drafts = []
        for candidate_id, draft in result.draft_map.items():
            all_drafts.append({
                "candidate_id": candidate_id,
                **draft.model_dump(),
            })
        
        if all_drafts:
            with open(drafts_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "candidate_id", "id", "service_category", "subject",
                    "content", "status", "evidence_used", "created_at",
                    "updated_at", "version", "validation_errors",
                ])
                writer.writeheader()
                
                for item in all_drafts:
                    row = {k: v for k, v in item.items() if k in writer.fieldnames}
                    
                    # Convert status enum to string
                    if "status" in row and hasattr(row["status"], "value"):
                        row["status"] = row["status"].value
                    
                    # Convert evidence_used list to string
                    if "evidence_used" in row and isinstance(row["evidence_used"], list):
                        row["evidence_used"] = ", ".join(row["evidence_used"])
                    
                    # Convert validation_errors list to string
                    if "validation_errors" in row and isinstance(row["validation_errors"], list):
                        row["validation_errors"] = "; ".join(row["validation_errors"])
                    
                    writer.writerow(row)
            
            results.append(ExportResult(
                path=str(drafts_path),
                records_count=len(all_drafts),
                success=True,
            ))
            logger.info(f"Exported {len(all_drafts)} drafts to: {drafts_path}")
    except Exception as e:
        logger.error(f"Failed to export drafts CSV: {e}")
        results.append(ExportResult(
            path=str(drafts_path),
            records_count=0,
            success=False,
            error=str(e),
        ))
    
    # Export approvals
    approvals_path = csv_dir / f"approvals_{timestamp}.csv"
    try:
        all_approvals = []
        for candidate_id, approval in result.approval_map.items():
            all_approvals.append({
                "candidate_id": candidate_id,
                **approval.model_dump(),
            })
        
        if all_approvals:
            with open(approvals_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "candidate_id", "id", "candidate_name", "candidate_website",
                    "score", "status", "evidence_summary", "draft_id",
                    "draft_preview", "requested_at", "requested_by", "notes",
                    "approved_at", "approved_by", "decision", "decision_notes",
                ])
                writer.writeheader()
                
                for item in all_approvals:
                    row = {k: v for k, v in item.items() if k in writer.fieldnames}
                    
                    # Convert status enum to string
                    if "status" in row and hasattr(row["status"], "value"):
                        row["status"] = row["status"].value
                    
                    # Convert decision enum to string if present
                    if "decision" in row and hasattr(row.get("decision"), "value"):
                        row["decision"] = row["decision"].value
                    
                    writer.writerow(row)
            
            results.append(ExportResult(
                path=str(approvals_path),
                records_count=len(all_approvals),
                success=True,
            ))
            logger.info(f"Exported {len(all_approvals)} approvals to: {approvals_path}")
    except Exception as e:
        logger.error(f"Failed to export approvals CSV: {e}")
        results.append(ExportResult(
            path=str(approvals_path),
            records_count=0,
            success=False,
            error=str(e),
        ))
    
    return results


@workflows.activity.define(
    name="export_summary_csv",
    retry_policy=workflows.RetryPolicy(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0,
        backoff_coefficient=2.0,
    ),
    timeout_seconds=60,
)
async def export_summary_csv(
    result: ProspectingResult,
    config: PersistenceConfig | None = None,
) -> ExportResult:
    """
    Export a summary CSV with just the essential fields.
    """
    if config is None:
        config = PersistenceConfig()
    
    csv_dir = Path(config.csv_dir)
    csv_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    summary_path = csv_dir / f"summary_{timestamp}.csv"
    
    try:
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Simple header
            header = [
                "candidate_id", "name", "website", "score", "status",
                "has_demand", "has_problem", "evidence_count",
                "draft_subject", "approval_status",
            ]
            writer.writerow(header)
            
            for candidate in result.candidates:
                score = result.score_map.get(candidate.id)
                evidence = result.evidence_map.get(candidate.id, [])
                draft = result.draft_map.get(candidate.id)
                approval = result.approval_map.get(candidate.id)
                
                row = [
                    candidate.id,
                    candidate.name,
                    candidate.website,
                    score.total if score else 0,
                    candidate.status.value if candidate.status else "",
                    score.has_direct_demand if score else False,
                    score.has_verified_problem if score else False,
                    len(evidence),
                    draft.subject if draft else "",
                    approval.status.value if approval and approval.status else "",
                ]
                
                writer.writerow(row)
        
        return ExportResult(
            path=str(summary_path),
            records_count=len(result.candidates),
            success=True,
        )
    except Exception as e:
        logger.error(f"Failed to export summary CSV: {e}")
        return ExportResult(
            path=str(summary_path),
            records_count=0,
            success=False,
            error=str(e),
        )
