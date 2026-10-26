"""Main prospecting workflow for Nurafinix Labs."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import mistralai.workflows as workflows
from mistralai.workflows import workflow

from ..models.prospect import CandidateBusiness, EvidenceRecord
from ..models.scoring import ProspectScore
from ..models.pipeline import ProspectingInput, ProspectingResult, PipelineStage, StageResult
from ..models.outreach import OutreachDraft, ApprovalRequest
from ..activities.discovery import (
    DiscoveryConfig,
    import_csv,
    normalize_businesses,
    deduplicate_businesses,
)
from ..activities.evidence import (
    InspectionConfig,
    InspectionResult,
    inspect_website,
    collect_evidence,
    verify_evidence,
)
from ..activities.qualification import (
    QualificationConfig,
    calculate_score,
    qualify_prospect,
    batch_qualify,
)
from ..activities.outreach import (
    OutreachConfig,
    generate_outreach_draft,
    review_evidence,
    batch_outreach,
)
from ..activities.persistence import (
    PersistenceConfig,
    save_results,
    export_csv,
    export_summary_csv,
)

logger = logging.getLogger(__name__)


@workflows.workflow.define(
    name="nurafinix-prospect-engine",
    workflow_display_name="Nurafinix Prospect Engine",
    workflow_description=(
        "Personal lead-generation system for Nurafinix Labs. "
        "Discovers, qualifies, scores, and generates outreach drafts for prospects."
    ),
)
class ProspectingWorkflow:
    """Orchestrates the complete prospecting pipeline.
    
    Pipeline stages:
    1. Discovery: Import candidates from CSV
    2. Normalization: Clean and standardize business records
    3. Deduplication: Remove duplicate candidates
    4. Evidence Collection: Gather website evidence (parallel)
    5. Qualification: AI-powered prospect qualification (parallel)
    6. Scoring: Calculate priority scores
    7. Draft Generation: Create personalized outreach drafts (parallel)
    8. Evidence Review: Prepare for human review (parallel)
    9. Persistence: Save results and export CSV
    """

    @workflows.workflow.entrypoint
    async def run(self, input: ProspectingInput) -> ProspectingResult:
        """Execute the complete prospecting pipeline."""
        execution_id = workflows.workflow.info().workflow_id
        started_at = datetime.utcnow()
        
        stage_results: list[StageResult] = []
        errors: list[str] = []
        
        # ------------------------------------------------------------------
        # Stage 1: Discovery - Import from CSV
        # ------------------------------------------------------------------
        logger.info("Stage 1: Discovery - Importing from CSV")
        try:
            stage_start = datetime.utcnow()
            
            discovery_config = DiscoveryConfig(
                csv_path=input.csv_path,
                csv_content=input.csv_content,
                batch_size=input.batch_size,
                max_candidates=input.batch_limit,
            )
            
            records = await import_csv(discovery_config)
            
            stage_duration = (datetime.utcnow() - stage_start).total_seconds()
            stage_results.append(StageResult(
                stage=PipelineStage.DISCOVERY,
                completed=True,
                data={"record_count": len(records)},
                timestamp=stage_start.isoformat() + "Z",
                duration_seconds=stage_duration,
            ))
            logger.info(f"Discovered {len(records)} records")
        except Exception as e:
            error_msg = f"Discovery failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            stage_results.append(StageResult(
                stage=PipelineStage.DISCOVERY,
                completed=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + "Z",
                duration_seconds=None,
            ))
            records = []
        
        # ------------------------------------------------------------------
        # Stage 2: Normalization
        # ------------------------------------------------------------------
        logger.info("Stage 2: Normalization")
        try:
            stage_start = datetime.utcnow()
            
            candidates = await normalize_businesses(records)
            
            stage_duration = (datetime.utcnow() - stage_start).total_seconds()
            stage_results.append(StageResult(
                stage=PipelineStage.NORMALIZATION,
                completed=True,
                data={"candidate_count": len(candidates)},
                timestamp=stage_start.isoformat() + "Z",
                duration_seconds=stage_duration,
            ))
            logger.info(f"Normalized {len(candidates)} candidates")
        except Exception as e:
            error_msg = f"Normalization failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            stage_results.append(StageResult(
                stage=PipelineStage.NORMALIZATION,
                completed=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + "Z",
                duration_seconds=None,
            ))
            candidates = []
        
        # ------------------------------------------------------------------
        # Stage 3: Deduplication
        # ------------------------------------------------------------------
        logger.info("Stage 3: Deduplication")
        try:
            stage_start = datetime.utcnow()
            
            candidates = await deduplicate_businesses(candidates)
            
            stage_duration = (datetime.utcnow() - stage_start).total_seconds()
            stage_results.append(StageResult(
                stage=PipelineStage.DEDUPLICATION,
                completed=True,
                data={"unique_count": len(candidates)},
                timestamp=stage_start.isoformat() + "Z",
                duration_seconds=stage_duration,
            ))
            logger.info(f"Deduplicated to {len(candidates)} unique candidates")
        except Exception as e:
            error_msg = f"Deduplication failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            stage_results.append(StageResult(
                stage=PipelineStage.DEDUPLICATION,
                completed=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + "Z",
                duration_seconds=None,
            ))
        
        # ------------------------------------------------------------------
        # Stage 4: Evidence Collection (parallel)
        # ------------------------------------------------------------------
        logger.info("Stage 4: Evidence Collection")
        evidence_map: dict[str, list[EvidenceRecord]] = {}
        inspection_config = InspectionConfig()
        
        try:
            stage_start = datetime.utcnow()
            
            # Collect evidence for all candidates in parallel
            inspection_results = await workflows.execute_activities_in_parallel(
                activity=inspect_website,
                items=[(c, inspection_config) for c in candidates],
                max_concurrent_scheduled_tasks=min(len(candidates), 5),
            )
            
            # Process results
            for candidate, result in zip(candidates, inspection_results):
                if result and result.success and result.evidence:
                    evidence_map[candidate.id] = result.evidence
                else:
                    evidence_map[candidate.id] = []
                    if result and result.error:
                        logger.warning(f"Evidence collection failed for {candidate.name}: {result.error}")
            
            total_evidence = sum(len(e) for e in evidence_map.values())
            stage_duration = (datetime.utcnow() - stage_start).total_seconds()
            stage_results.append(StageResult(
                stage=PipelineStage.EVIDENCE_COLLECTION,
                completed=True,
                data={"evidence_count": total_evidence, "candidates_with_evidence": len(evidence_map)},
                timestamp=stage_start.isoformat() + "Z",
                duration_seconds=stage_duration,
            ))
            logger.info(f"Collected {total_evidence} evidence records from {len(candidates)} candidates")
        except Exception as e:
            error_msg = f"Evidence collection failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            stage_results.append(StageResult(
                stage=PipelineStage.EVIDENCE_COLLECTION,
                completed=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + "Z",
                duration_seconds=None,
            ))
            # Initialize empty evidence map
            evidence_map = {c.id: [] for c in candidates}
        
        # ------------------------------------------------------------------
        # Stage 5: Qualification (parallel)
        # ------------------------------------------------------------------
        logger.info("Stage 5: Qualification")
        score_map: dict[str, ProspectScore] = {}
        qualified_candidates: dict[str, CandidateBusiness] = {}
        
        try:
            stage_start = datetime.utcnow()
            
            qualification_config = QualificationConfig()
            
            # Qualify prospects in parallel
            qualification_results = await workflows.execute_activities_in_parallel(
                activity=qualify_prospect,
                items=[
                    (c, evidence_map.get(c.id, []), qualification_config, input.mock_mode)
                    for c in candidates
                ],
                max_concurrent_scheduled_tasks=min(len(candidates), 3),
            )
            
            # Process results
            for candidate, (score, qualified_candidate) in zip(candidates, qualification_results):
                score_map[candidate.id] = score
                qualified_candidates[candidate.id] = qualified_candidate
            
            stage_duration = (datetime.utcnow() - stage_start).total_seconds()
            stage_results.append(StageResult(
                stage=PipelineStage.QUALIFICATION,
                completed=True,
                data={"qualified_count": len(qualification_results)},
                timestamp=stage_start.isoformat() + "Z",
                duration_seconds=stage_duration,
            ))
            logger.info(f"Qualified {len(qualification_results)} candidates")
        except Exception as e:
            error_msg = f"Qualification failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            stage_results.append(StageResult(
                stage=PipelineStage.QUALIFICATION,
                completed=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + "Z",
                duration_seconds=None,
            ))
            # Initialize empty maps
            score_map = {}
            qualified_candidates = {}
        
        # Update candidates with qualified versions
        for c in candidates:
            if c.id in qualified_candidates:
                qualified_candidates[c.id].tags = c.tags
        
        # Use qualified candidates going forward
        candidates = list(qualified_candidates.values())
        
        # ------------------------------------------------------------------
        # Stage 6: Scoring
        # ------------------------------------------------------------------
        logger.info("Stage 6: Scoring")
        try:
            stage_start = datetime.utcnow()
            
            # Recalculate scores deterministically
            for candidate in candidates:
                if candidate.id not in score_map:
                    candidate_evidence = evidence_map.get(candidate.id, [])
                    score = calculate_score(
                        candidate, candidate_evidence, QualificationConfig()
                    )
                    score_map[candidate.id] = score
            
            stage_duration = (datetime.utcnow() - stage_start).total_seconds()
            stage_results.append(StageResult(
                stage=PipelineStage.SCORING,
                completed=True,
                data={"scored_count": len(score_map)},
                timestamp=stage_start.isoformat() + "Z",
                duration_seconds=stage_duration,
            ))
            logger.info(f"Scored {len(score_map)} candidates")
        except Exception as e:
            error_msg = f"Scoring failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            stage_results.append(StageResult(
                stage=PipelineStage.SCORING,
                completed=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + "Z",
                duration_seconds=None,
            ))
        
        # ------------------------------------------------------------------
        # Stage 7: Draft Generation (parallel)
        # ------------------------------------------------------------------
        logger.info("Stage 7: Draft Generation")
        draft_map: dict[str, OutreachDraft] = {}
        
        try:
            stage_start = datetime.utcnow()
            
            outreach_config = OutreachConfig()
            
            # Generate drafts in parallel
            draft_results = await workflows.execute_activities_in_parallel(
                activity=generate_outreach_draft,
                items=[
                    (c, evidence_map.get(c.id, []), score_map.get(c.id), outreach_config, input.mock_mode)
                    for c in candidates
                ],
                max_concurrent_scheduled_tasks=min(len(candidates), 3),
            )
            
            # Process results
            for candidate, draft in zip(candidates, draft_results):
                if draft:
                    draft_map[candidate.id] = draft
            
            stage_duration = (datetime.utcnow() - stage_start).total_seconds()
            stage_results.append(StageResult(
                stage=PipelineStage.DRAFT_GENERATION,
                completed=True,
                data={"draft_count": len(draft_map)},
                timestamp=stage_start.isoformat() + "Z",
                duration_seconds=stage_duration,
            ))
            logger.info(f"Generated {len(draft_map)} outreach drafts")
        except Exception as e:
            error_msg = f"Draft generation failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            stage_results.append(StageResult(
                stage=PipelineStage.DRAFT_GENERATION,
                completed=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + "Z",
                duration_seconds=None,
            ))
        
        # ------------------------------------------------------------------
        # Stage 8: Evidence Review Preparation (parallel)
        # ------------------------------------------------------------------
        logger.info("Stage 8: Evidence Review")
        approval_map: dict[str, ApprovalRequest] = {}
        
        try:
            stage_start = datetime.utcnow()
            
            # Prepare evidence review for each candidate in parallel
            review_results = await workflows.execute_activities_in_parallel(
                activity=review_evidence,
                items=[
                    (c, evidence_map.get(c.id, []), score_map.get(c.id), draft_map.get(c.id))
                    for c in candidates
                ],
                max_concurrent_scheduled_tasks=min(len(candidates), 3),
            )
            
            # Process results
            for candidate, approval in zip(candidates, review_results):
                if approval:
                    approval_map[candidate.id] = approval
            
            stage_duration = (datetime.utcnow() - stage_start).total_seconds()
            stage_results.append(StageResult(
                stage=PipelineStage.EVIDENCE_REVIEW,
                completed=True,
                data={"approval_count": len(approval_map)},
                timestamp=stage_start.isoformat() + "Z",
                duration_seconds=stage_duration,
            ))
            logger.info(f"Prepared {len(approval_map)} approval requests")
        except Exception as e:
            error_msg = f"Evidence review failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            stage_results.append(StageResult(
                stage=PipelineStage.EVIDENCE_REVIEW,
                completed=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + "Z",
                duration_seconds=None,
            ))
        
        # ------------------------------------------------------------------
        # Stage 9: Persistence and Export
        # ------------------------------------------------------------------
        logger.info("Stage 9: Persistence and Export")
        persistence_config = PersistenceConfig()
        
        try:
            stage_start = datetime.utcnow()
            
            # Build complete result
            result = ProspectingResult(
                execution_id=execution_id,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                input=input,
                candidates=candidates,
                evidence_map=evidence_map,
                score_map=score_map,
                draft_map=draft_map,
                approval_map=approval_map,
                stage_results=stage_results,
                errors=errors,
            )
            
            # Save results
            await save_results(result, persistence_config)
            
            # Export CSV
            await export_csv(result, persistence_config)
            
            # Export summary
            await export_summary_csv(result, persistence_config)
            
            stage_duration = (datetime.utcnow() - stage_start).total_seconds()
            stage_results.append(StageResult(
                stage=PipelineStage.LEAD_TRACKING,
                completed=True,
                data={"saved": True, "exported": True},
                timestamp=stage_start.isoformat() + "Z",
                duration_seconds=stage_duration,
            ))
            logger.info("Results saved and exported")
        except Exception as e:
            error_msg = f"Persistence/export failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            stage_results.append(StageResult(
                stage=PipelineStage.LEAD_TRACKING,
                completed=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat() + "Z",
                duration_seconds=None,
            ))
        
        # ------------------------------------------------------------------
        # Build final result
        # ------------------------------------------------------------------
        final_result = ProspectingResult(
            execution_id=execution_id,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            input=input,
            candidates=candidates,
            evidence_map=evidence_map,
            score_map=score_map,
            draft_map=draft_map,
            approval_map=approval_map,
            stage_results=stage_results,
            errors=errors,
        )
        
        # Calculate summary
        total_score = sum(s.total for s in score_map.values())
        avg_score = total_score / len(score_map) if score_map else 0
        
        high_priority = sum(1 for s in score_map.values() if s.total >= 70)
        medium_priority = sum(1 for s in score_map.values() if 50 <= s.total < 70)
        low_priority = sum(1 for s in score_map.values() if 30 <= s.total < 50)
        not_qualified = sum(1 for s in score_map.values() if s.total < 30)
        
        capped_no_demand = sum(1 for s in score_map.values() if not s.has_direct_demand and s.total >= 69)
        capped_no_problem = sum(1 for s in score_map.values() if not s.has_verified_problem and s.total >= 39)
        
        final_result.summary = {
            "execution_id": execution_id,
            "total_candidates": len(candidates),
            "total_evidence": sum(len(e) for e in evidence_map.values()),
            "total_drafts": len(draft_map),
            "total_approvals": len(approval_map),
            "average_score": round(avg_score, 2),
            "high_priority": high_priority,
            "medium_priority": medium_priority,
            "low_priority": low_priority,
            "not_qualified": not_qualified,
            "capped_no_demand": capped_no_demand,
            "capped_no_problem": capped_no_problem,
            "errors": errors,
        }
        
        logger.info(f"Workflow complete: {len(candidates)} candidates processed")
        
        return final_result
