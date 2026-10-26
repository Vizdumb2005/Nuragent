# Nurafinix Prospect Engine - Architecture Document

> **Version:** 0.1.0  
> **Last Updated:** 2026-10-26  
> **Status:** MVP Implementation Complete (with minor syntax fixes pending)

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Diagram](#component-diagram)
4. [Data Flow](#data-flow)
5. [Pipeline Stages](#pipeline-stages)
6. [Technology Stack](#technology-stack)
7. [Mistral Integration](#mistral-integration)
8. [Safety & Security](#safety--security)
9. [Scalability Considerations](#scalability-considerations)
10. [Error Handling](#error-handling)
11. [Testing Strategy](#testing-strategy)
12. [Deployment](#deployment)

---

## Overview

The **Nurafinix Prospect Engine** is a personal lead-generation system for Nurafinix Labs, built on **Mistral Workflows**. It provides an evidence-based pipeline for discovering, qualifying, scoring, and generating outreach drafts for potential business prospects.

### Key Principles

1. **Evidence-First**: All claims must be backed by verifiable evidence
2. **Deterministic Scoring**: Transparent rubric with explicit caps
3. **Safe Inspection**: Protected website auditing with SSRF prevention
4. **Human-in-the-Loop**: All outreach requires explicit approval
5. **Reproducibility**: Complete pipeline can run in mock mode without API keys

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nurafinix Prospect Engine                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │   CSV Import    │    │  Web Search     │    │   API Key   │  │
│  │   (Primary)     │    │  (Secondary)    │    │  (Optional) │  │
│  └────────┬────────┘    └────────┬────────┘    └──────┬──────┘  │
│           │                      │                     │          │
│           └──────────────┬─────────┘                     │          │
│                          │                                 │          │
│                          ▼                                 │          │
│              ┌─────────────────────────┐                  │          │
│              │   Mistral Workflows     │◄─────────────────┘          │
│              │   Worker Process        │                                  │
│              │                         │                                  │
│              │  ┌───────────────────┐  │                                  │
│              │  │  Prospecting       │  │                                  │
│              │  │  Workflow         │  │                                  │
│              │  │                    │  │                                  │
│              │  │  1. Discovery      │  │                                  │
│              │  │  2. Normalization   │  │                                  │
│              │  │  3. Deduplication   │  │                                  │
│              │  │  4. Evidence        │  │                                  │
│              │  │  5. Website Audit   │  │                                  │
│              │  │  6. Demand Analysis │  │                                  │
│              │  │  7. Qualification   │  │                                  │
│              │  │  8. Scoring         │  │                                  │
│              │  │  9. Draft Gen       │  │                                  │
│              │  │ 10. Evidence Review │  │                                  │
│              │  │ 11. Persistence     │  │                                  │
│              │  │ 12. Export          │  │                                  │
│              │  └───────────────────┘  │                                  │
│              └─────────────────────────┘                                  │
│                          │                                                  │
│              ┌───────────────────────┐                                   │
│              │    Activities Layer    │                                   │
│              │                       │                                   │
│              │  • discover_from_csv   │                                   │
│              │  • normalize_business │                                   │
│              │  • deduplicate_cand.   │                                   │
│              │  • collect_website_ev. │                                   │
│              │  • audit_website       │                                   │
│              │  • analyze_demand      │                                   │
│              │  • qualify_prospect    │                                   │
│              │  • calculate_score     │                                   │
│              │  • generate_draft      │                                   │
│              │  • prepare_review      │                                   │
│              │  • save_*              │                                   │
│              │  • export_*            │                                   │
│              └───────────────────────┘                                   │
│                          │                                                  │
│              ┌───────────────────────┐                                   │
│              │   Mistral AI Layer    │                                   │
│              │                       │                                   │
│              │  • Prospect Qualifier │                                   │
│              │  • Outreach Writer    │                                   │
│              │  • Web Search Tool    │                                   │
│              └───────────────────────┘                                   │
│                          │                                                  │
│              ┌───────────────────────┐                                   │
│              │    Data Layer         │                                   │
│              │                       │                                   │
│              │  • Pydantic Models    │                                   │
│              │  • In-Memory Storage  │                                   │
│              │  • CSV Export         │                                   │
│              └───────────────────────┘                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Component Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                           Presentation Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  • CLI (main entry point)                                          │
│  • CSV Export                                                      │
│  • Progress Reporting                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                          Workflow Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  • ProspectingWorkflow (main)                                     │
│  • 12 Pipeline Stages                                             │
│  • Parallel Execution                                              │
│  • Error Handling & Retries                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                          Activities Layer                               │
├─────────────────────────────────────────────────────────────────┤
│  • Discovery Activities                                           │
│  • Evidence Collection Activities                                  │
│  • Qualification Activities                                        │
│  • Outreach Activities                                             │
│  • Persistence Activities                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                           Models Layer                                  │
├─────────────────────────────────────────────────────────────────┤
│  • Prospect Models (BusinessRecord, CandidateBusiness)            │
│  • Evidence Models (EvidenceRecord, EvidenceCategory)             │
│  • Scoring Models (ProspectScore, ScoreComponents, ScoringRubric) │
│  • Pipeline Models (ProspectingInput, ProspectingResult)          │
│  • Outreach Models (OutreachDraft, ApprovalRequest)               │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                          External Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  • CSV Files (Input)                                               │
│  • Websites (Inspection)                                          │
│  • Mistral API (AI Models)                                        │
│  • Web Search (Optional Discovery)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### End-to-End Flow

```
┌─────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  CSV    │────▶│  Discovery  │────▶│Normalization│────▶│Deduplication │
│  File   │     │  (Stage 1)  │     │  (Stage 2)  │     │  (Stage 3)  │
└─────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                   │
                                                                   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Evidence     │◄────│Website       │     │Demand       │     │Qualification │
│ Collection   │     │Inspection    │     │Analysis      │     │(AI Agent)    │
│ (Stage 4)    │     │(Stage 5)     │     │(Stage 6)     │     │(Stage 7)     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                   │
                                                                   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Scoring     │────▶│ Draft        │────▶│Evidence     │────▶│ Persistence │
│  (Stage 8)   │     │Generation    │     │Review        │     │ (Stage 11)   │
│              │     │(AI Agent)    │     │(Stage 10)    │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                   │
                                                                   ▼
┌──────────────┐     ┌──────────────┐
│   Export     │────▶│   CSV Files  │
│  (Stage 12)  │     │   (Output)   │
└──────────────┘     └──────────────┘
```

### Parallel Execution Points

1. **Evidence Collection (Stage 4)**: All candidates' websites inspected in parallel
   - Max concurrency: 5 (configurable via `max_concurrent_scheduled_tasks`)
   - Each candidate gets independent retry handling

2. **Website Audit (Stage 5)**: All websites audited in parallel
   - Max concurrency: 5
   - Shared rate limiting across all audits

3. **Qualification (Stage 7)**: All prospects qualified in parallel
   - Max concurrency: 3 (AI model rate limits)
   - Each qualification uses Mistral AI

4. **Draft Generation (Stage 9)**: All drafts generated in parallel
   - Max concurrency: 3
   - Each draft uses Mistral AI

---

## Pipeline Stages

### Stage 1: Discovery
- **Purpose**: Import candidate businesses
- **Input**: CSV file path or content
- **Output**: List of `BusinessRecord` objects
- **Implementation**: `discover_from_csv` activity
- **Parallel**: No (sequential CSV parsing)
- **Retry**: 2 attempts with 1.5x backoff

### Stage 2: Normalization
- **Purpose**: Clean and standardize business records
- **Input**: `BusinessRecord` list
- **Output**: List of `CandidateBusiness` objects
- **Implementation**: `normalize_business` activity (per record)
- **Parallel**: No (sequential processing)
- **Retry**: 2 attempts with 1.5x backoff

### Stage 3: Deduplication
- **Purpose**: Remove duplicate candidates
- **Input**: `CandidateBusiness` list
- **Output**: Deduplicated `CandidateBusiness` list
- **Implementation**: `deduplicate_candidates` activity
- **Parallel**: No
- **Retry**: 2 attempts with 1.5x backoff

### Stage 4: Evidence Collection
- **Purpose**: Gather website evidence for each candidate
- **Input**: `CandidateBusiness` list
- **Output**: List of `EvidenceRecord` objects
- **Implementation**: `collect_website_evidence` activity
- **Parallel**: Yes (via `execute_activities_in_parallel`)
- **Max Concurrency**: 5
- **Retry**: 2 attempts with 1.5x backoff per candidate

### Stage 5: Website Audit
- **Purpose**: Comprehensive website inspection
- **Input**: `CandidateBusiness` list
- **Output**: Audit results (converted to evidence)
- **Implementation**: `audit_website` activity
- **Parallel**: Yes (via `execute_activities_in_parallel`)
- **Max Concurrency**: 5
- **Retry**: 2 attempts with 1.5x backoff

### Stage 6: Demand Analysis
- **Purpose**: Identify demand signals from evidence
- **Input**: `CandidateBusiness` + evidence
- **Output**: Demand assessment per candidate
- **Implementation**: `analyze_demand` activity
- **Parallel**: No (sequential per candidate)
- **Retry**: 2 attempts with 1.5x backoff

### Stage 7: Qualification
- **Purpose**: AI-powered prospect qualification
- **Input**: `CandidateBusiness` + evidence
- **Output**: Qualification scores and reasoning
- **Implementation**: `qualify_prospect` activity (uses Mistral AI)
- **Parallel**: Yes (via `execute_activities_in_parallel`)
- **Max Concurrency**: 3
- **Retry**: 2 attempts with 1.5x backoff
- **Model**: mistral-small-latest
- **Structured Output**: JSON with all required fields

### Stage 8: Scoring
- **Purpose**: Calculate priority scores using rubric
- **Input**: `CandidateBusiness` + evidence + qualification
- **Output**: `ProspectScore` per candidate
- **Implementation**: `calculate_score` activity
- **Parallel**: No (sequential per candidate)
- **Retry**: 2 attempts with 1.5x backoff
- **Caps Applied**: 
  - No direct demand: Max 69/100
  - No verified problem: Max 39/100

### Stage 9: Draft Generation
- **Purpose**: Generate personalized outreach drafts
- **Input**: `CandidateBusiness` + evidence + score
- **Output**: `OutreachDraft` per candidate
- **Implementation**: `generate_outreach_draft` activity (uses Mistral AI)
- **Parallel**: Yes (via loop with async calls)
- **Max Concurrency**: 3 (implicit via batch limit)
- **Retry**: 2 attempts with 1.5x backoff
- **Model**: mistral-small-latest
- **Validation**: Checks for unsupported claims
- **Fallback**: Generic draft if AI fails

### Stage 10: Evidence Review
- **Purpose**: Prepare comprehensive review package
- **Input**: `CandidateBusiness` + evidence + score + draft
- **Output**: Review package for human approval
- **Implementation**: `prepare_evidence_review` activity
- **Parallel**: No (sequential per candidate)
- **Retry**: 2 attempts with 1.5x backoff

### Stage 11: Persistence
- **Purpose**: Save all data to storage
- **Input**: All pipeline results
- **Output**: Saved candidates, evidence, scores, drafts
- **Implementation**: `save_*` activities
- **Parallel**: No
- **Retry**: 2 attempts with 1.5x backoff
- **Storage**: In-memory (for MVP)

### Stage 12: Export
- **Purpose**: Generate CSV exports
- **Input**: All pipeline results
- **Output**: CSV files (leads and evidence)
- **Implementation**: `export_to_csv` activity
- **Parallel**: No
- **Retry**: 2 attempts with 1.5x backoff

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Language** | Python | 3.12+ | Primary development language |
| **Package Manager** | uv | Latest | Dependency management |
| **Workflows SDK** | mistralai-workflows | 3.16.0 | Workflow orchestration |
| **Mistral Client** | mistralai | 2.10.1 | AI model access |
| **HTTP Client** | httpx | 0.20+ | Website inspection |
| **Validation** | Pydantic | 2.0+ | Data models and validation |
| **Testing** | pytest | 8.0+ | Unit and integration tests |
| **Async Testing** | pytest-asyncio | 0.23+ | Async test support |
| **Linting** | ruff | 0.11+ | Code quality |
| **Type Checking** | mypy | 1.15+ | Type safety |
| **Security** | semgrep | 1.0+ | Determinism linting |

### Mistral-Specific Dependencies

```python
# Core workflows
mistralai-workflows>=3.0.0,<4

# Mistral AI integration (includes durable agents, connectors)
mistralai-workflows[mistralai]>=3.0.0,<4

# Optional storage (not used in MVP)
# mistralai-workflows[s3]
# mistralai-workflows[azure]
# mistralai-workflows[gcs]
```

---

## Mistral Integration

### Workflows Integration

The system uses **Mistral Workflows** as the primary orchestration engine:

```python
import mistralai.workflows as workflows

@workflows.workflow.define(name="nurafinix-prospect-engine")
class ProspectingWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: ProspectingInput) -> ProspectingResult:
        # Pipeline implementation
        pass

@workflows.activity(
    retry_policy_max_attempts=2,
    retry_policy_backoff_coefficient=1.5,
    start_to_close_timeout=timedelta(seconds=60),
)
async def collect_website_evidence(candidate: CandidateBusiness) -> list[EvidenceRecord]:
    # Activity implementation
    pass
```

### Durable Agents Integration

Two specialized agents are defined:

#### 1. Prospect Qualifier Agent

```python
from mistralai.workflows.plugins.mistralai import Agent, Runner, RemoteSession

qualifier_agent = Agent(
    name="nurafinix-prospect-qualifier",
    model="mistral-small-latest",
    description="Qualifies business prospects based on evidence",
    instructions=PROSPECT_QUALIFIER_PROMPT,
    tools=[],  # Uses structured output, not tools
)
```

**Purpose**: Assess fit, demand, opportunity, and contact scores

**Input**: Business record + collected evidence + service profile

**Output**: Structured JSON with scores, reasoning, and cited evidence

#### 2. Outreach Writer Agent

```python
outreach_agent = Agent(
    name="nurafinix-outreach-writer",
    model="mistral-small-latest",
    description="Writes personalized outreach drafts",
    instructions=OUTREACH_WRITER_PROMPT,
    tools=[],  # Uses structured output, not tools
)
```

**Purpose**: Generate evidence-based, personalized outreach drafts

**Input**: Qualified lead + approved evidence + service offer + company description

**Output**: Structured JSON with subject, body, evidence references, and reasoning

### Built-in Tools

The system uses Mistral's built-in `WebSearchTool` for business discovery:

```python
import mistralai

web_search_tool = mistralai.WebSearchTool()
```

**Purpose**: Alternative discovery method (secondary to CSV import)

**Status**: Available when Mistral API key is present

**Fallback**: CSV import always works, even in mock mode

---

## Safety & Security

### Website Inspection Safety

All website inspection activities implement comprehensive safety measures:

#### 1. SSRF Protection

```python
def _is_safe_url(url: str) -> bool:
    """Check if URL is safe to request."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    
    # Block private IP addresses
    private_ips = ["localhost", "127.0.0.1", "::1", "10.", "192.168.", ...]
    if any(host.startswith(prefix) for prefix in private_ips):
        return False
    
    # Block non-HTTP(S) schemes
    if parsed.scheme not in ("http", "https"):
        return False
    
    return True
```

#### 2. Request Limits

```python
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = timedelta(seconds=30)
USER_AGENT = "Nurafinix-Prospect-Engine/1.0"
```

#### 3. Evidence Integrity

Every evidence record includes:
- `evidence_id`: Deterministic hash-based ID
- `business_id`: Reference to source business
- `source_url`: URL where evidence was collected
- `category`: Type of evidence (HTTPS, mobile, analytics, etc.)
- `observation`: What was observed
- `timestamp`: When it was collected
- `verification_method`: How it was verified (HTTP check, HTML parse, etc.)
- `confidence`: 0-1 confidence score
- `status`: verified, uncertain, contradictory, stale, or unavailable
- `details`: Additional context

### Data Protection

1. **No Secret Logging**: Never logs API keys or credentials
2. **Environment Variables**: Uses `.env.example` pattern for configuration
3. **Input Validation**: All inputs validated via Pydantic models
4. **Structured Outputs**: All AI outputs validated against Pydantic schemas

### Outreach Validation

All outreach drafts are validated for unsupported claims:

```python
def validate_no_unsupported_claims(self) -> list[str]:
    """Check for unsupported claims in the draft."""
    unsupported_patterns = [
        "we have worked together",
        "our previous project",
        "as you know",
        "we achieved",
        "we delivered",
        "our ROI",
        "testimonial",
        "case study",
        "guaranteed",
        "proven results",
        "trusted by",
        "used by",
    ]
    # Check and return issues
```

---

## Scalability Considerations

### Current Limits (MVP)

| Resource | Limit | Rationale |
|----------|-------|-----------|
| Batch Size | 5 | Conservative default for parallel processing |
| Max Concurrent | 5 | Website inspection, audit |
| Max Concurrent (AI) | 3 | Model rate limits |
| Response Size | 10 MB | Prevent oversized payloads |
| Timeout | 30-60s | Prevent runaway requests |

### Horizontal Scaling

The system supports horizontal scaling via multiple workers:

```bash
# Worker 1
MISTRAL_API_KEY=key1 uv run python -m nurafinix.worker

# Worker 2 (same workspace)
MISTRAL_API_KEY=key1 uv run python -m nurafinix.worker

# Worker 3 (different environment)
MISTRAL_API_KEY=key2 uv run python -m nurafinix.worker
```

**Scaling Strategy:**
- Same workspace, same task queue: Tasks distributed automatically
- Different workspaces: Complete isolation (dev/staging/prod)
- Different deployment names: Testing different code versions

### Rate Limiting

Per-activity rate limiting prevents API overload:

```python
@workflows.activity(
    rate_limit=workflows.RateLimit(
        time_window_in_sec=1,
        max_calls=10,
        key="website_inspection"
    )
)
async def inspect_website(url: str) -> dict:
    # Implementation
```

---

## Error Handling

### Retry Policies

All activities have automatic retry policies:

```python
@workflows.activity(
    retry_policy_max_attempts=2,
    retry_policy_backoff_coefficient=1.5,
)
async def my_activity(input: Any) -> Any:
    # Implementation
```

**Behavior:**
- 2 attempts total (1 initial + 1 retry)
- 1.5x backoff between attempts
- Exponential backoff: 0s, 1.5s, 3s, etc.

### Timeout Handling

All external operations have timeouts:

```python
@workflows.activity(
    start_to_close_timeout=timedelta(seconds=60),
)
async def collect_evidence(candidate: CandidateBusiness) -> list[EvidenceRecord]:
    # Implementation with timeout
```

**Timeout Values:**
- CSV import: 30s
- Normalization: 10s
- Website inspection: 60s
- AI qualification: 60s
- Draft generation: 60s
- Scoring: 10s

### Graceful Degradation

The system implements graceful degradation:

1. **Website Unavailable**: Returns `EvidenceStatus.UNAVAILABLE` instead of failing
2. **AI Model Failure**: Falls back to neutral scores or generic drafts
3. **Partial Results**: Continues pipeline with available data
4. **Mock Mode**: Runs entire pipeline without API calls

### Error Reporting

All errors are captured and reported:
- Stage-level errors in `StageResult` objects
- Global errors in `ProspectingResult.errors` list
- Individual activity errors in workflow timeline

---

## Testing Strategy

### Test Coverage

| Category | Tests | Coverage |
|----------|-------|----------|
| Models | 22 | All Pydantic models validated |
| Scoring | 8 | Rubric, caps, priority levels |
| Activities | 6 | CSV import, normalization, deduplication |
| Evidence | 5 | Safety checks, collection |
| **Total** | **41** | **Core functionality** |

### Test Types

#### 1. Unit Tests
- Model validation
- Scoring calculations
- Helper functions

#### 2. Integration Tests
- Activity execution
- Workflow stages
- End-to-end pipeline

#### 3. Mock Tests
- Mock mode execution (no API calls)
- Simulated website responses
- Simulated AI responses

### Test Execution

```bash
# Run all tests
uv run pytest src/tests/

# Run specific test file
uv run pytest src/tests/test_models.py

# Run with verbose output
uv run pytest -v src/tests/

# Run with coverage
uv run pytest --cov=nurafinix src/tests/
```

---

## Deployment

### Local Development

```bash
# Install dependencies
uv sync

# Copy environment file
cp .env.example .env

# Edit .env with your API key
nano .env

# Run tests
uv run pytest src/tests/

# Run CLI
python -m nurafinix.cli.main run --csv data/businesses.csv
```

### Worker Deployment

```bash
# Start worker
uv run python -m nurafinix.worker

# Or use Makefile
make start-worker
```

### Production Deployment

```bash
# Build Docker image
docker build -t nurafinix-prospect-engine .

# Run Docker container
docker run --rm --env-file .env nurafinix-prospect-engine
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MISTRAL_API_KEY` | Yes | None | Mistral API key |
| `MISTRAL_WORKFLOW_WORKSPACE_ID` | No | None | Workspace ID |
| `MISTRAL_MODEL` | No | mistral-small-latest | Model to use |
| `MAX_BATCH_SIZE` | No | 5 | Maximum batch size |
| `MAX_CONCURRENT_REQUESTS` | No | 3 | Concurrent requests |
| `REQUEST_TIMEOUT` | No | 30 | Request timeout (seconds) |
| `OUTPUT_DIR` | No | ./output | Output directory |

---

## File Structure

```
nurafinix-prospect-engine/
├── docs/
│   ├── MISTRAL_CAPABILITY_MAP.md    # This document
│   └── ARCHITECTURE.md              # This document
├── src/
│   ├── nurafinix/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── prospect.py           # Business & evidence models
│   │   │   ├── scoring.py            # Scoring models & rubric
│   │   │   ├── pipeline.py           # Pipeline & workflow models
│   │   │   └── outreach.py           # Outreach & approval models
│   │   ├── workflows/
│   │   │   ├── __init__.py
│   │   │   └── prospecting.py        # Main workflow
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── prospect_qualifier.py # AI agent definition
│   │   │   └── outreach_writer.py    # AI agent definition
│   │   ├── cli/
│   │   │   ├── __init__.py
│   │   │   └── main.py               # CLI entry point
│   │   ├── data/
│   │   │   └── __init__.py           # Sample data
│   │   └── worker.py                 # Worker entry point
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py           # Model tests
│       ├── test_scoring.py          # Scoring tests
│       ├── test_activities.py       # Activity tests
│       └── test_evidence.py         # Evidence tests
├── .agents/                          # Mistral SDK docs (reference)
├── .env.example
├── .gitignore
├── Dockerfile
├── Makefile
├── pyproject.toml
├── README.md
└── uv.lock
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-10-26 | Vibe Code | Initial architecture document |

---

## References

1. [Mistral Workflows Documentation](https://docs.mistral.ai/studio/workflows)
2. [MISTRAL_CAPABILITY_MAP.md](./MISTRAL_CAPABILITY_MAP.md)
3. [README.md](../README.md)
