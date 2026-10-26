"""
Activities for the Nurafinix Prospect Engine.

All external work (HTTP requests, AI calls, file I/O) is performed in activities.
"""

from .discovery import (
    DiscoveryConfig,
    import_csv,
    normalize_businesses,
    deduplicate_businesses,
    batch_candidates,
)

from .evidence import (
    InspectionConfig,
    InspectionResult,
    inspect_website,
    collect_evidence,
    verify_evidence,
)

from .qualification import (
    QualificationConfig,
    calculate_score,
    qualify_prospect,
    batch_qualify,
)

from .outreach import (
    OutreachConfig,
    generate_outreach_draft,
    review_evidence,
    batch_outreach,
)

from .persistence import (
    PersistenceConfig,
    ExportResult,
    save_results,
    export_csv,
    export_summary_csv,
)

__all__ = [
    # Discovery
    "DiscoveryConfig",
    "import_csv",
    "normalize_businesses",
    "deduplicate_businesses",
    "batch_candidates",
    # Evidence
    "InspectionConfig",
    "InspectionResult",
    "inspect_website",
    "collect_evidence",
    "verify_evidence",
    # Qualification
    "QualificationConfig",
    "calculate_score",
    "qualify_prospect",
    "batch_qualify",
    # Outreach
    "OutreachConfig",
    "generate_outreach_draft",
    "review_evidence",
    "batch_outreach",
    # Persistence
    "PersistenceConfig",
    "ExportResult",
    "save_results",
    "export_csv",
    "export_summary_csv",
]
