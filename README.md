# Nurafinix Prospect Engine

Personal lead-generation system for Nurafinix Labs, built on Mistral Workflows.

## Overview

The Nurafinix Prospect Engine is a complete, evidence-based lead generation pipeline that:

1. **Discovers** candidate businesses from CSV imports or web search
2. **Normalizes** and deduplicates business records
3. **Collects** verifiable evidence from websites
4. **Qualifies** prospects using AI-powered analysis
5. **Scores** prospects based on fit, demand, opportunity, and contact criteria
6. **Generates** personalized, evidence-based outreach drafts
7. **Prepares** comprehensive evidence reviews for human approval
8. **Exports** results to CSV for tracking

## Features

- ✅ **CSV Import**: Import businesses from CSV files with flexible schema
- ✅ **Website Inspection**: Comprehensive, safe website auditing
- ✅ **Evidence Collection**: Gathers HTTPS, mobile, analytics, contact form, tech fingerprint, and demand signal evidence
- ✅ **AI Qualification**: Mistral-powered prospect qualification with structured outputs
- ✅ **Transparent Scoring**: Clear scoring rubric with explicit caps
- ✅ **Outreach Drafts**: Personalized, evidence-cited drafts without unsupported claims
- ✅ **Parallel Processing**: Bounded parallel execution for efficiency
- ✅ **Error Handling**: Robust retry policies and error recovery
- ✅ **CSV Export**: Complete data export for external tracking

## Architecture

```
nurafinix-prospect-engine/
├── src/
│   ├── nurafinix/
│   │   ├── models/           # Pydantic models for data structures
│   │   │   ├── __init__.py
│   │   │   ├── prospect.py    # Business and evidence models
│   │   │   ├── scoring.py    # Scoring models and rubric
│   │   │   ├── pipeline.py   # Pipeline and workflow models
│   │   │   └── outreach.py   # Outreach and approval models
│   │   ├── activities/        # Workflow activities
│   │   │   ├── __init__.py
│   │   │   ├── discovery.py  # CSV import and normalization
│   │   │   ├── evidence.py   # Website inspection and evidence collection
│   │   │   ├── qualification.py  # AI qualification and scoring
│   │   │   ├── outreach.py   # Draft generation and review
│   │   │   └── persistence.py # Data storage and export
│   │   ├── agents/            # Mistral Studio agent definitions
│   │   │   ├── __init__.py
│   │   │   ├── prospect_qualifier.py
│   │   │   └── outreach_writer.py
│   │   ├── workflows/         # Workflow definitions
│   │   │   ├── __init__.py
│   │   │   └── prospecting.py  # Main prospecting workflow
│   │   ├── cli/               # Command-line interface
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   ├── data/              # Sample data
│   │   │   └── __init__.py
│   │   └── worker.py          # Worker entry point
│   └── tests/                # Test suite
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_scoring.py
│       ├── test_activities.py
│       └── test_evidence.py
├── .env.example              # Environment configuration template
├── pyproject.toml            # Project configuration
├── Makefile                  # Helper commands
└── README.md                 # This file
```

## Quick Start

### Prerequisites

- Python 3.12+
- uv or uvx for dependency management
- Mistral API key (optional for mock mode)

### Installation

```bash
# Clone or navigate to the project
cd nurafinix-prospect-engine

# Install dependencies
uv sync

# Copy environment file
cp .env.example .env

# Edit .env with your Mistral API key
nano .env
```

### Running the Workflow

```bash
# Run with CSV import
python -m nurafinix.cli.main run --csv data/businesses.csv --list --output ./output

# Run in mock mode (no API calls)
python -m nurafinix.cli.main run --csv data/businesses.csv --mock --list

# Run with custom batch limit
python -m nurafinix.cli.main run --csv data/businesses.csv --batch-limit 10
```

### Using the CLI

```bash
# Show help
python -m nurafinix.cli.main --help

# Run workflow with CSV
python -m nurafinix.cli.main run --csv data/businesses.csv

# List candidates after execution
python -m nurafinix.cli.main run --csv data/businesses.csv --list

# Export results
python -m nurafinix.cli.main run --csv data/businesses.csv --output ./results

# Verbose output
python -m nurafinix.cli.main run --csv data/businesses.csv --verbose
```

### Starting the Worker

```bash
# Start the workflow worker
uv run python -m nurafinix.worker

# Or use the Makefile
make start-worker
```

## CSV Format

The system accepts CSV files with the following columns (all optional except `name`):

```csv
name,website,description,category,size,location,source_url
Acme Corp,https://acme.com,"Tech company looking for data help","Data,Analytics",100-200,San Francisco,https://acme.com
TechStart Inc,https://techstart.com,"Startup needing analytics",Web Development,10-50,Austin,https://techstart.com
```

- `name`: Business name (required)
- `website`: Business website URL
- `description`: Business description
- `category`: Comma-separated service categories
- `size`: Company size (e.g., "10-50", "100-200")
- `location`: Company location
- `source_url`: Source URL for the record

## Scoring Rubric

The system uses a transparent scoring rubric with the following components:

| Component | Max Points | Description |
|-----------|------------|-------------|
| Fit | 25 | How well the business matches our service categories |
| Demand | 30 | Evidence of direct demand for our services |
| Opportunity | 25 | Verified technical or operational opportunity |
| Contact | 10 | Legitimate and relevant contact channel |
| Evidence | 10 | Evidence reliability and recency |
| **Total** | **100** | |

### Score Caps

- **No direct demand evidence**: Maximum score is 69/100
- **No verified problem or demand**: Maximum score is 39/100

These caps ensure that prospects without genuine need are not over-prioritized.

### Priority Levels

- **HIGH**: 80+ points
- **MEDIUM**: 60-79 points
- **LOW**: 40-59 points
- **NONE**: Below 40 points

## Evidence Types

The system collects the following types of evidence:

| Category | Description | Verification Method | Confidence |
|----------|-------------|---------------------|------------|
| Website HTTPS | HTTPS status | HTTP check | High |
| Website Mobile | Mobile viewport meta tag | HTML parse | High |
| Contact Form | Contact form detection | HTML parse | Medium |
| Analytics Script | Analytics tool detection | HTML parse | Medium |
| Tech Fingerprint | Technology stack detection | HTML parse | Medium |
| Demand Signal | Job listings, RFPs, etc. | HTML parse | Medium |
| Broken Links | Internal broken links | HTTP check | Medium |
| Project Request | Explicit project requests | HTML parse | High |

Each evidence record includes:
- Business ID
- Source URL
- Observation
- Timestamp
- Verification method
- Confidence score (0-1)
- Status (verified, uncertain, contradictory, stale, unavailable)

## AI Agents

The system uses two specialized Mistral AI agents:

### 1. Prospect Qualifier Agent

**Purpose**: Assess whether a business is a good fit and has genuine demand.

**Input**:
- Business record (name, website, description, categories)
- Collected evidence
- Service profile

**Output**:
- Fit score (0-25)
- Demand score (0-30)
- Opportunity score (0-25)
- Contact score (0-10)
- Evidence strength assessment
- Relevant opportunities
- Uncertainty level
- Recommended next action
- Cited evidence IDs
- Detailed reasoning

**Rules**:
- Only use provided evidence
- Cite evidence IDs and source URLs
- Do NOT invent evidence
- Be conservative with uncertainty

### 2. Outreach Writer Agent

**Purpose**: Generate personalized, evidence-based outreach drafts.

**Input**:
- Qualified lead
- Approved evidence
- Service offer
- Company description

**Output**:
- Subject line
- Email body
- Service offer
- Evidence references
- Source URLs
- Reasoning

**Rules**:
- Only use information from provided evidence
- Reference actual observations with source URLs
- Explain relevance to our services
- Propose low-pressure next step
- Do NOT invent personal familiarity
- Do NOT claim ROI or testimonials
- Keep under 200 words

## Pipeline Stages

The workflow executes the following stages:

1. **Discovery**: Import candidates from CSV or search
2. **Normalization**: Clean and standardize business records
3. **Deduplication**: Remove duplicate candidates
4. **Evidence Collection**: Gather website evidence (parallel)
5. **Website Audit**: Comprehensive website inspection (parallel)
6. **Demand Analysis**: Identify demand signals
7. **Qualification**: AI-powered prospect qualification (parallel)
8. **Scoring**: Calculate priority scores
9. **Draft Generation**: Create personalized outreach drafts (parallel)
10. **Evidence Review**: Prepare for human approval
11. **Persistence**: Save all data
12. **Export**: Generate CSV exports

## Parallel Execution

The system uses bounded parallelism for efficiency:

- **Evidence Collection**: Up to 5 concurrent website requests
- **Website Audit**: Up to 5 concurrent audits
- **Qualification**: Up to 3 concurrent AI calls
- **Draft Generation**: Up to 3 concurrent AI calls

All parallel execution includes:
- Automatic retries (2 attempts with backoff)
- Timeout protection (30-60 seconds per task)
- Error handling and partial results

## Safety Features

The system includes comprehensive safety measures:

### Website Inspection
- **SSRF Protection**: Blocks private IP addresses and localhost
- **Scheme Validation**: Only allows HTTP/HTTPS URLs
- **Response Size Limits**: Maximum 10MB per response
- **Redirect Limits**: Maximum 5 redirects
- **Timeout Protection**: 30-second timeout per request
- **Safe User Agent**: Identifies as bot

### Evidence Integrity
- **Deterministic IDs**: Hash-based evidence IDs
- **Confidence Scoring**: Explicit confidence levels
- **Status Tracking**: Clear evidence status
- **Citation Requirements**: All AI outputs must cite evidence

### Data Protection
- **No Secret Logging**: Never logs API keys or credentials
- **Environment Variables**: Uses .env for configuration
- **Input Validation**: Validates all inputs and outputs

## Testing

Run the test suite:

```bash
# Install test dependencies
uv sync --all-extras

# Run all tests
pytest src/tests/

# Run specific test file
pytest src/tests/test_models.py

# Run with verbose output
pytest -v src/tests/

# Run with coverage
pytest --cov=nurafinix src/tests/
```

## Development

### Adding New Features

1. **New Evidence Type**: Add to `EvidenceCategory` enum and update collection logic
2. **New Scoring Component**: Add to `ScoreComponents` and update calculation
3. **New Activity**: Add to `activities/` directory and register in `__init__.py`
4. **New Workflow**: Add to `workflows/` directory and register in worker

### Agent Configuration

Agents are defined in `src/nurafinix/agents/` and can be configured in Mistral Studio:

1. Create a new agent in Studio
2. Use the system prompt from the agent class
3. Configure the input/output schema
4. Update the workflow to use the Studio agent

## Configuration

Environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `MISTRAL_API_KEY` | Mistral API key | Yes |
| `MISTRAL_WORKFLOW_WORKSPACE_ID` | Workspace ID | No |
| `MISTRAL_MODEL` | Model to use | No (default: mistral-small-latest) |
| `MAX_BATCH_SIZE` | Maximum batch size | No (default: 5) |
| `MAX_CONCURRENT_REQUESTS` | Concurrent requests | No (default: 3) |
| `REQUEST_TIMEOUT` | Request timeout | No (default: 30) |
| `OUTPUT_DIR` | Output directory | No (default: ./output) |

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are installed with `uv sync`
2. **API key errors**: Verify `MISTRAL_API_KEY` is set in environment
3. **CSV import errors**: Check CSV format and file path
4. **Website inspection errors**: Verify URLs are valid and accessible
5. **Timeout errors**: Increase `REQUEST_TIMEOUT` or reduce batch size

### Debug Mode

Enable verbose output:

```bash
python -m nurafinix.cli.main run --csv data.csv --verbose
```

### Mock Mode

Run without API calls:

```bash
python -m nurafinix.cli.main run --csv data.csv --mock
```

## License

This project is proprietary software of Nurafinix Labs.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Acknowledgments

- Built with [Mistral Workflows](https://docs.mistral.ai/studio/workflows)
- Inspired by the Focalyn architecture
- Powered by Mistral AI models
