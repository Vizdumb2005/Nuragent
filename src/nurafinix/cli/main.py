"""Main CLI entry point for the Nurafinix Prospect Engine."""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path

from mistralai.workflows import workflow

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nurafinix.models.prospect import CandidateBusiness
from nurafinix.models.pipeline import ProspectingInput
from nurafinix.workflows.prospecting import ProspectingWorkflow


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def print_banner():
    """Print application banner."""
    print("""
  _   _ _____ _____ _   _ _____ ____  _____ _   _
 | \ | |_   _| ____| \ | |_   _|  _ \| ____| \ | |
 |  \| | | | |  _| |  \| | | | | |_) |  _| |  \| |
 | . ` | | | | |___| . ` | | | |  _ <| |___| . ` |
 | |\  |_| |_|_____| |\  |_| |_| |_\_\_____| |\  |_|
 |_| \_|     |_| \_|     |_|   |_| |_|

Nurafinix Prospect Engine v0.1.0
Personal lead-generation system for Nurafinix Labs
""")


def print_stage_progress(stage: str, status: str, message: str = ""):
    """Print stage progress."""
    symbols = {
        "completed": "✓",
        "failed": "✗",
        "skipped": "- ",
        "running": "→",
    }
    symbol = symbols.get(status, "?")
    print(f"  {symbol} {stage}: {message}")


def print_summary(result: dict) -> None:
    """Print execution summary."""
    print("\n" + "=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)
    
    print(f"\nExecution ID: {result.get('execution_id', 'N/A')}")
    print(f"Started: {result.get('started_at', 'N/A')}")
    print(f"Completed: {result.get('completed_at', 'N/A')}")
    
    print(f"\n--- Results ---")
    print(f"Candidates discovered: {result.get('summary', {}).get('total_candidates', 0)}")
    print(f"Evidence collected: {result.get('summary', {}).get('total_evidence', 0)}")
    print(f"Prospects scored: {result.get('summary', {}).get('total_scores', 0)}")
    print(f"Drafts generated: {result.get('summary', {}).get('total_drafts', 0)}")
    
    print(f"\n--- Priority Distribution ---")
    print(f"High priority: {result.get('summary', {}).get('high_priority', 0)}")
    print(f"Medium priority: {result.get('summary', {}).get('medium_priority', 0)}")
    print(f"Low priority: {result.get('summary', {}).get('low_priority', 0)}")
    print(f"Capped scores: {result.get('summary', {}).get('capped_count', 0)}")
    
    if result.get('errors'):
        print(f"\n--- Errors ---")
        for error in result.get('errors', []):
            print(f"  - {error}")
    
    print("\n" + "=" * 60)


def print_candidates(candidates: list[dict], verbose: bool = False) -> None:
    """Print candidate list."""
    if not candidates:
        print("No candidates found.")
        return
    
    print(f"\n{'ID':<18} {'Name':<30} {'Website':<35} {'Score':<8} {'Priority':<10}")
    print("-" * 100)
    
    for c in candidates:
        score = c.get('score', {})
        total = score.get('total_score', 0)
        priority = score.get('priority_level', 'NONE')
        
        name = c.get('name', 'N/A')[:28]
        website = c.get('website', 'N/A')[:33]
        business_id = c.get('business_id', 'N/A')[:16]
        
        print(f"{business_id:<18} {name:<30} {website:<35} {total:<8.1f} {priority:<10}")
    
    print()


def print_evidence(evidence: list[dict], business_id: str | None = None) -> None:
    """Print evidence for a specific business or all."""
    if business_id:
        evidence = [e for e in evidence if e.get('business_id') == business_id]
    
    if not evidence:
        print("No evidence found.")
        return
    
    print(f"\n{'Evidence ID':<18} {'Category':<20} {'Observation':<40} {'Status':<12}")
    print("-" * 100)
    
    for e in evidence:
        print(f"{e.get('evidence_id', 'N/A')[:16]:<18} "
              f"{e.get('category', 'N/A')[:18]:<20} "
              f"{e.get('observation', 'N/A')[:38]:<40} "
              f"{e.get('status', 'N/A'):<12}")
    
    print()


def print_draft(draft: dict) -> None:
    """Print an outreach draft."""
    print(f"\nSubject: {draft.get('subject', 'N/A')}")
    print(f"To: {draft.get('business_name', 'N/A')}")
    print(f"Service: {draft.get('service_offer', 'N/A')}")
    print(f"\n{draft.get('body', '')}")
    print()


def export_results(result: dict, output_dir: str = "./output") -> None:
    """Export results to files."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Export leads CSV
    leads_csv = result.get("summary", {}).get("leads_csv", "")
    if leads_csv:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        leads_path = Path(output_dir) / f"leads_{timestamp}.csv"
        leads_path.write_text(leads_csv)
        print(f"Exported leads to: {leads_path}")
    
    # Export evidence CSV
    evidence_csv = result.get("summary", {}).get("evidence_csv", "")
    if evidence_csv:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        evidence_path = Path(output_dir) / f"evidence_{timestamp}.csv"
        evidence_path.write_text(evidence_csv)
        print(f"Exported evidence to: {evidence_path}")
    
    # Export full JSON
    json_path = Path(output_dir) / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, 'w') as f:
        json.dump(result, f, default=str, indent=2)
    print(f"Exported full results to: {json_path}")


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

async def cmd_run(args) -> int:
    """Run the prospecting workflow."""
    print_banner()
    print(f"\nStarting prospecting workflow...")
    print(f"Input: {args.input if args.input else 'CSV import'}")
    print(f"Batch limit: {args.batch_limit}")
    print(f"Mock mode: {args.mock}")
    print()
    
    # Parse input
    input_data = ProspectingInput(
        csv_path=args.csv,
        csv_content=args.csv_content,
        search_query=args.query,
        search_limit=args.limit,
        service_categories=args.categories or [],
        batch_limit=args.batch_limit,
        mock_mode=args.mock,
    )
    
    # Run workflow
    workflow_instance = ProspectingWorkflow()
    
    try:
        result = await workflow_instance.run(input_data)
        
        # Convert to dict for display
        result_dict = result.model_dump()
        
        # Print summary
        print_summary(result_dict)
        
        # Print stage results
        print("\nSTAGE RESULTS:")
        for stage_result in result_dict.get('stage_results', []):
            status = "completed" if stage_result.get('completed') else "failed"
            error = stage_result.get('error', '')
            message = stage_result.get('data', {}).get('message', '') or \
                     f"{stage_result.get('data', {})}"
            print_stage_progress(
                stage_result.get('stage', 'unknown').value,
                status,
                message if not error else error
            )
        
        # Print candidates
        if args.list:
            candidates = result_dict.get('candidates', [])
            scores = result_dict.get('scores', [])
            
            # Merge candidates with scores
            merged = []
            score_map = {s['business_id']: s for s in scores}
            for c in candidates:
                merged.append({**c, 'score': score_map.get(c['business_id'], {})})
            
            print_candidates(merged, verbose=args.verbose)
        
        # Export if requested
        if args.output:
            export_results(result_dict, args.output)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Workflow failed: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


async def cmd_list(args) -> int:
    """List previous executions or candidates."""
    print_banner()
    print("\nPrevious executions and candidates will be listed here.")
    print("(Feature to be implemented with persistent storage)")
    return 0


async def cmd_show(args) -> int:
    """Show details for a specific candidate or execution."""
    print_banner()
    print(f"\nShowing details for: {args.identifier}")
    print("(Feature to be implemented with persistent storage)")
    return 0


async def cmd_approve(args) -> int:
    """Approve or reject a lead."""
    print_banner()
    print(f"\nApproving lead: {args.identifier}")
    print("(Feature to be implemented with persistent storage)")
    return 0


async def cmd_export(args) -> int:
    """Export results to CSV."""
    print_banner()
    print(f"\nExporting to: {args.output}")
    print("(Feature to be implemented with persistent storage)")
    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="nurafinix",
        description="Nurafinix Prospect Engine - Personal lead-generation system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nurafinix run --csv data/businesses.csv              Import from CSV
  nurafinix run --csv data/businesses.csv --limit 10  Import first 10
  nurafinix run --query "data analytics" --limit 5     Search (future)
  nurafinix run --csv data/businesses.csv --list     Show candidates
  nurafinix run --csv data/businesses.csv --output ./results  Export results
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the prospecting workflow")
    run_parser.add_argument(
        "--csv",
        type=str,
        help="Path to CSV file with business records",
    )
    run_parser.add_argument(
        "--csv-content",
        type=str,
        help="CSV content as string",
    )
    run_parser.add_argument(
        "--query",
        type=str,
        help="Search query for discovery (future)",
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)",
    )
    run_parser.add_argument(
        "--categories",
        type=str,
        nargs="*",
        help="Service categories to filter by",
    )
    run_parser.add_argument(
        "--batch-limit",
        type=int,
        default=5,
        help="Batch processing limit (default: 5)",
    )
    run_parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (no actual API calls)",
    )
    run_parser.add_argument(
        "--list",
        action="store_true",
        help="List candidates after execution",
    )
    run_parser.add_argument(
        "--output",
        type=str,
        help="Output directory for exported files",
    )
    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output",
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List executions or candidates")
    list_parser.add_argument(
        "--all",
        action="store_true",
        help="List all executions",
    )
    list_parser.add_argument(
        "--candidates",
        action="store_true",
        help="List candidates",
    )
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show details")
    show_parser.add_argument(
        "identifier",
        type=str,
        help="Execution ID or business ID",
    )
    show_parser.add_argument(
        "--evidence",
        action="store_true",
        help="Show evidence",
    )
    show_parser.add_argument(
        "--draft",
        action="store_true",
        help="Show outreach draft",
    )
    
    # Approve command
    approve_parser = subparsers.add_parser("approve", help="Approve or reject a lead")
    approve_parser.add_argument(
        "identifier",
        type=str,
        help="Business ID or draft ID",
    )
    approve_parser.add_argument(
        "--approve",
        action="store_true",
        help="Approve the lead",
    )
    approve_parser.add_argument(
        "--reject",
        action="store_true",
        help="Reject the lead",
    )
    approve_parser.add_argument(
        "--reason",
        type=str,
        help="Reason for approval/rejection",
    )
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export results")
    export_parser.add_argument(
        "--output",
        type=str,
        default="./output",
        help="Output directory (default: ./output)",
    )
    export_parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "json"],
        default="csv",
        help="Export format (default: csv)",
    )
    
    return parser


async def main_async(argv: list[str] | None = None) -> int:
    """Async main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    if not args.command:
        parser.print_help()
        return 0
    
    command_handlers = {
        "run": cmd_run,
        "list": cmd_list,
        "show": cmd_show,
        "approve": cmd_approve,
        "export": cmd_export,
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        return await handler(args)
    else:
        parser.print_help()
        return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    return asyncio.run(main_async(argv))


if __name__ == "__main__":
    sys.exit(main())
