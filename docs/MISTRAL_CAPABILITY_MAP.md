# Mistral Capability Map - Nurafinix Prospect Engine

> **Document Version:** 0.1.0  
> **Last Updated:** 2026-10-26  
> **Project:** Nurafinix Prospect Engine  
> **Purpose:** Map Mistral platform capabilities to Nurafinix lead-generation requirements

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Workflows Capabilities](#1-workflows-capabilities)
3. [Runtime Agents Capabilities](#2-runtime-agents-capabilities)
4. [Search Capabilities](#3-search-capabilities)
5. [Model Interfaces](#4-model-interfaces)
6. [Quality and Operations](#5-quality-and-operations)
7. [Development Environment](#6-development-environment)
8. [Capability Decision Matrix](#capability-decision-matrix)
9. [Implementation Recommendations](#implementation-recommendations)

---

## Executive Summary

This document maps **verified** Mistral platform capabilities to the Nurafinix Prospect Engine requirements. All findings are based on official documentation from the Mistral Workflows SDK (v3.16.0) and Studio platform as scaffolded by `uvx mistralai-workflows-cli@latest setup`.

**Key Verification Sources:**
- Local skill files: `.agents/skills/workflows/references/` (official Mistral documentation bundle)
- Official docs: `https://docs.mistral.ai/studio/workflows`
- SDK version: `mistralai-workflows==3.16.0`, `mistralai==2.10.1`

**Critical Distinction:** This document explicitly distinguishes:
- ✅ **Verified capabilities** - Confirmed in official documentation
- ⚠️ **Conditional capabilities** - Require specific prerequisites (hardened deployment, OAuth, etc.)
- ❌ **Unavailable/Rejected** - Not applicable or explicitly unsupported
- 🔄 **Vibe Skills vs Studio Agents** - Vibe Skills are for Vibe Code; Studio Agents are for workflows

---

## 1. Workflows Capabilities

### 1.1 Core Concepts

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Workflows Orchestration** | [Core Concepts](.agents/skills/workflows/references/getting-started/core-concepts.mdx) | ✅ | **HIGH** - Forms the backbone of our pipeline | Python 3.12+, uv | Included in Workflows | **use_now** |
| **Activities (Work Units)** | [Activities Guide](.agents/skills/workflows/references/guides/activities.mdx) | ✅ | **HIGH** - Evidence collection, website inspection, scoring | None | Included | **use_now** |
| **Deterministic Execution** | Core Concepts | ✅ | **HIGH** - Ensures repeatable prospect qualification | None | Included | **use_now** |
| **Long-running Workflows** | Core Concepts | ✅ | **MEDIUM** - Pipeline can run for extended periods | None | Included | **use_now** |
| **Input/Output Size Limit (2MB)** | Core Concepts | ✅ | **MEDIUM** - Constrains evidence payloads; requires chunking for large datasets | None | Included | **use_now** |

### 1.2 Concurrency & Parallelism

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **`execute_activities_in_parallel`** | [Concurrency](.agents/skills/workflows/references/guides/concurrency.mdx) | ✅ | **HIGH** - Parallel evidence collection, website audits | None | Included | **use_now** |
| **`max_concurrent_scheduled_tasks`** | Concurrency | ✅ | **HIGH** - Control parallelism for rate limiting | None | Included | **use_now** |
| **List Executor Pattern** | Concurrency | ✅ | **HIGH** - Process candidate batches | None | Included | **use_now** |
| **`asyncio.gather` for small batches** | Concurrency | ✅ | **MEDIUM** - Simple parallel execution (< 5K items) | None | Included | **use_now** |
| **Continue-as-New** | Concurrency | ✅ | **LOW** - Auto-handles large datasets beyond history limits | None | Included | **defer** |
| **Local Activities** | [Activities](.agents/skills/workflows/references/guides/activities.mdx) | ✅ | **MEDIUM** - Fast operations (<1s) like normalization | None | Included | **use_now** |

### 1.3 Retry Policies & Error Handling

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Automatic Retries** | [Activities](.agents/skills/workflows/references/guides/activities.mdx) | ✅ | **HIGH** - Transient failures in website inspection | `retry_policy_max_attempts`, `retry_policy_backoff_coefficient` | Included | **use_now** |
| **Activity Timeouts** | Activities | ✅ | **HIGH** - Prevent runaway HTTP requests | `start_to_close_timeout=timedelta(seconds=60)` | Included | **use_now** |
| **Heartbeat Timeout** | Activities | ✅ | **LOW** - Long-running operations monitoring | `heartbeat_timeout`, `activity_heartbeat()` | Included | **defer** |
| **Sticky Worker Sessions** | Activities | ✅ | **LOW** - Performance optimization | `sticky_to_worker=True` | Included | **defer** |

### 1.4 Observability

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **OpenTelemetry Traces** | [Observability](.agents/skills/workflows/references/guides/observability.mdx) | ✅ | **MEDIUM** - Debugging and performance analysis | None | Included | **use_now** |
| **Execution Traces** | Observability | ✅ | **MEDIUM** - Fetch workflow traces via API | `get_workflow_execution_trace_otel_async` | Included | **use_now** |
| **Trace Sampling** | Observability | ✅ | **LOW** - Control trace collection overhead | `traceparent` header | Included | **defer** |
| **Activity Naming** | Observability | ✅ | **LOW** - Better trace readability | `name="Processing customer emails"` | Included | **defer** |

### 1.5 Deployment & Scaling

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Multiple Workers** | [Core Concepts](.agents/skills/workflows/references/getting-started/core-concepts.mdx) | ✅ | **HIGH** - Horizontal scaling for throughput | Same API key, same task queue | Included | **use_now** |
| **Environment Separation** | Core Concepts | ✅ | **HIGH** - Dev/Staging/Prod isolation | Separate workspaces | Included | **use_now** |
| **Testing Different Code** | Core Concepts | ✅ | **MEDIUM** - Safe experimentation | Different deployment names | Included | **use_now** |
| **Task Queue Isolation** | Core Concepts | ✅ | **MEDIUM** - Prevent worker conflicts | `DEPLOYMENT_NAME` environment variable | Included | **use_now** |
| **Hardened Deployments** | [Deployment Patterns](.agents/skills/workflows/references/guides/_deployment-patterns.mdx) | ⚠️ | **LOW** - Required for OBO connectors | Hardened deployment configuration | Additional | **defer** |

### 1.6 Rate Limiting

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Per-Activity Rate Limits** | [Rate Limiting](.agents/skills/workflows/references/guides/rate-limiting.mdx) | ✅ | **HIGH** - Protect external APIs from overload | `rate_limit=RateLimit(time_window_in_sec=1, max_calls=100)` | Included | **use_now** |
| **Shared Rate Limit Pools** | Rate Limiting | ✅ | **MEDIUM** - Coordinate across multiple activities | `key="mistral_api"` parameter | Included | **use_now** |
| **Global Rate Limit Sharing** | Rate Limiting | ✅ | **MEDIUM** - All workers/share same limit | Same task workspace | Included | **use_now** |

---

## 2. Runtime Agents Capabilities

### 2.1 Durable Agents

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Durable Agent Framework** | [Durable Agents](.agents/skills/workflows/references/guides/durable-agents.mdx) | ✅ | **HIGH** - Prospect Qualifier & Outreach Writer agents | `mistralai-workflows[mistralai]` | Included | **use_now** |
| **Agent State Persistence** | Durable Agents | ✅ | **HIGH** - Maintains agent state across failures | None | Included | **use_now** |
| **Tool Integration** | Durable Agents | ✅ | **HIGH** - Activities as agent tools | None | Included | **use_now** |
| **Multi-Agent Handoffs** | Durable Agents | ✅ | **LOW** - Delegate to specialized agents | Multiple agent definitions | Included | **defer** |

### 2.2 Session Types

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **RemoteSession** | Durable Agents | ✅ | **HIGH** - Production workloads (recommended) | Mistral Agents SDK | Included | **use_now** |
| **LocalSession** | Durable Agents | ✅ | **LOW** - Experimental/on-premises only | Direct completion API | Included | **defer** |

### 2.3 MCP Integration

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **MCP Stdio Servers** | Durable Agents | ✅ | **LOW** - Local tool servers | `MCPStdioConfig`, `env_mapping` for secrets | Included | **defer** |
| **MCP SSE Servers** | Durable Agents | ✅ | **LOW** - Remote MCP over Server-Sent Events | `MCPSSEConfig`, credentials | Included | **defer** |
| **MCP Streamable HTTP** | Durable Agents | ✅ | **LOW** - Remote MCP over HTTP | `MCPStreamableHTTPConfig`, `mistralai>=2.8.0` | Included | **defer** |
| **Credential Forwarding** | Durable Agents | ✅ | **MEDIUM** - Secure secret handling | `env_mapping`, `auth_token_env`, `header_mapping` | Included | **use_now** |

### 2.4 Built-in Tools

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **WebSearchTool** | Durable Agents | ✅ | **HIGH** - Business discovery option | `mistralai.WebSearchTool()` | Additional (API calls) | **use_now** |
| **CodeInterpreterTool** | Durable Agents | ✅ | **LOW** - Not needed for our use case | None | Additional | **reject** |
| **ImageGenerationTool** | Durable Agents | ✅ | **LOW** - Not needed | None | Additional | **reject** |
| **DocumentLibraryTool** | Durable Agents | ✅ | **LOW** - Not needed | None | Additional | **reject** |

---

## 3. Search Capabilities

### 3.1 Agentic Search

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Agentic Search** | [Agentic Search Docs](https://docs.mistral.ai/studio/search/agentic-search) | ⚠️ | **MEDIUM** - Could enhance business discovery | Hardened deployment, OAuth | Additional | **defer** |
| **Search Toolkit** | [Search Toolkit](https://docs.mistral.ai/studio/search/search-toolkit) | ⚠️ | **LOW** - RAG capabilities | Hardened deployment | Additional | **defer** |
| **Libraries** | [Libraries](https://docs.mistral.ai/studio/libraries) | ⚠️ | **LOW** - Document storage | Hardened deployment | Additional | **defer** |

### 3.2 Retrieval & Reranking

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Retrievers** | Search Toolkit | ⚠️ | **LOW** - Not primary discovery method | Hardened deployment | Additional | **defer** |
| **Rerankers** | Search Toolkit | ⚠️ | **LOW** - Not substitute for deterministic qualification | Hardened deployment | Additional | **reject** |
| **Embeddings** | Search Toolkit | ⚠️ | **LOW** - Not needed for structured evidence | Hardened deployment | Additional | **defer** |
| **Semantic Caching** | Search Toolkit | ⚠️ | **LOW** - Not applicable | Hardened deployment | Additional | **defer** |

**Note:** Reranking is explicitly **NOT** a substitute for candidate discovery or deterministic qualification per requirements. We use structured evidence, not semantic similarity.

---

## 4. Model Interfaces

### 4.1 Available Models

| Model | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-------|--------------|----------|------------------------|---------------|------|----------|
| **mistral-small-latest** | [Models](https://docs.mistral.ai/) | ✅ | **HIGH** - Default for qualification & outreach | None | Per-token | **use_now** |
| **mistral-medium-latest** | Models | ✅ | **MEDIUM** - Higher quality, higher cost | None | Per-token (higher) | **defer** |
| **mistral-large-latest** | Models | ✅ | **LOW** - Overkill for structured outputs | None | Per-token (highest) | **reject** |

### 4.2 Structured Outputs

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Structured Output (JSON)** | Durable Agents | ✅ | **HIGH** - All AI outputs use Pydantic models | `response_format={"type": "json_object"}` | Included | **use_now** |
| **`chat_parse_to_model`** | [Activities](.agents/skills/workflows/references/getting-started/installation.mdx) | ✅ | **HIGH** - Parse structured output to Pydantic | `from mistralai.workflows.plugins.mistralai.activities import chat_parse_to_model` | Included | **use_now** |
| **Type Validation** | Python SDK | ✅ | **HIGH** - All models validated | Pydantic | Included | **use_now** |

### 4.3 API Endpoint Limitations

| Limitation | Official URL | Verified | Impact | Workaround | Decision |
|------------|--------------|----------|--------|-----------|----------|
| **2MB Input/Output Limit** | Core Concepts | ✅ | Evidence payloads must be chunked | Split large evidence collections | **use_now** |
| **Execution History Limit** | Concurrency | ✅ | Long-running workflows | Continue-as-new | **use_now** |
| **Rate Limits** | Rate Limiting | ✅ | External API calls | Per-activity rate limiting | **use_now** |

---

## 5. Quality and Operations

### 5.1 Offline Evaluations

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Evaluation Datasets** | [Evaluation Docs](https://docs.mistral.ai/studio/process/batch-processing) | ⚠️ | **LOW** - Post-MVP | Batch processing setup | Additional | **defer** |
| **Evaluators** | Evaluation Docs | ⚠️ | **LOW** - Post-MVP | None | Additional | **defer** |
| **Distributed Tracing** | Observability | ✅ | **MEDIUM** - Already included via OpenTelemetry | None | Included | **use_now** |

### 5.2 Batch Processing

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Batch Processing** | [Batch Processing](https://docs.mistral.ai/studio/process/batch-processing) | ⚠️ | **LOW** - Post-MVP for bulk operations | Hardened deployment | Additional | **defer** |

### 5.3 Secrets Manager

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Secrets Manager** | [Secrets Manager](https://docs.mistral.ai/studio/safety-&-utilities/secrets-manager) | ⚠️ | **MEDIUM** - Secure credential storage | Hardened deployment | Included | **defer** |

**Note:** For now, we use environment variables with `.env.example` pattern. Secrets Manager requires hardened deployment.

---

## 6. Development Environment

### 6.1 Vibe Code

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Vibe Code** | [Vibe](https://docs.mistral.ai/) | ✅ | **HIGH** - Current development environment | None | Included | **use_now** |
| **Project Configuration** | Vibe | ✅ | **HIGH** - `pyproject.toml`, `uv.lock` | None | Included | **use_now** |
| **Custom SKILL.md** | Vibe | ✅ | **LOW** - Project-specific instructions | `.vibe/skills/` | Included | **defer** |

### 6.2 Workflow Testing

| Capability | Official URL | Verified | Implementation Relevance | Prerequisites | Cost | Decision |
|-----------|--------------|----------|------------------------|---------------|------|----------|
| **Workflow Testing** | [Workflow Testing](.agents/skills/workflows/references/workflow_testing.md) | ✅ | **HIGH** - Unit and integration tests | None | Included | **use_now** |
| **Determinism Linting** | [Linting Rules](.agents/skills/workflows/scripts/linting/rules/) | ✅ | **MEDIUM** - Ensure deterministic workflows | `semgrep` | Included | **use_now** |

---

## Capability Decision Matrix

### ✅ **USE NOW** (Immediate Implementation)

| Category | Capability | Justification | Priority |
|----------|------------|---------------|----------|
| Workflows | Workflow orchestration | Core pipeline architecture | **P0** |
| Workflows | Activities | Evidence collection, website inspection, scoring | **P0** |
| Workflows | `execute_activities_in_parallel` | Parallel evidence collection | **P0** |
| Workflows | Retry policies & timeouts | Reliability for HTTP requests | **P0** |
| Workflows | Local activities | Fast normalization, deduplication | **P0** |
| Agents | Durable Agents | Prospect Qualifier & Outreach Writer | **P0** |
| Agents | RemoteSession | Production-ready agent execution | **P0** |
| Agents | WebSearchTool | Business discovery option | **P0** |
| Models | Structured outputs | All AI outputs validated | **P0** |
| Models | mistral-small-latest | Cost-effective for structured tasks | **P0** |
| Observability | OpenTelemetry traces | Debugging and monitoring | **P0** |
| Rate Limiting | Per-activity rate limits | Protect external APIs | **P0** |
| Testing | Workflow testing | Ensure reliability | **P0** |

### ⚠️ **DEFER** (Post-MVP / Conditional)

| Category | Capability | Justification | Priority | Blockers |
|----------|------------|---------------|----------|----------|
| Workflows | Continue-as-New | Large dataset handling | **P1** | None (auto-handled) |
| Workflows | Hardened deployments | OBO connectors, Secrets Manager | **P1** | Requires hardened deployment |
| Agents | Multi-agent handoffs | Specialized agent delegation | **P1** | Complexity vs. value |
| Agents | MCP integration | External tool servers | **P1** | Not needed for MVP |
| Search | Agentic Search | Enhanced discovery | **P1** | Hardened deployment |
| Search | Search Toolkit | RAG capabilities | **P1** | Hardened deployment |
| Models | mistral-medium-latest | Higher quality outputs | **P1** | Cost consideration |
| Quality | Offline evaluations | Model quality assessment | **P1** | Post-MVP feature |
| Quality | Batch processing | Bulk operations | **P1** | Post-MVP feature |
| Quality | Secrets Manager | Secure credential storage | **P1** | Hardened deployment |

### ❌ **REJECT** (Not Applicable)

| Category | Capability | Justification |
|----------|------------|---------------|
| Agents | CodeInterpreterTool | Not needed for lead generation |
| Agents | ImageGenerationTool | Not needed for lead generation |
| Agents | DocumentLibraryTool | Not needed for lead generation |
| Search | Rerankers | Not substitute for deterministic qualification |
| Models | mistral-large-latest | Overkill for structured outputs |

---

## Implementation Recommendations

### For Nurafinix Prospect Engine MVP

#### 1. **Use Workflows as Primary Architecture**
- ✅ **Verified**: Workflow orchestration with activities is production-ready
- ✅ **Decision**: `use_now`
- **Implementation**: Use `execute_activities_in_parallel` for evidence collection

#### 2. **Use Durable Agents for AI Tasks**
- ✅ **Verified**: Durable Agents with RemoteSession are production-ready
- ✅ **Decision**: `use_now`
- **Implementation**: 
  - Prospect Qualifier Agent: `model="mistral-small-latest"`, structured output
  - Outreach Writer Agent: `model="mistral-small-latest"`, structured output

#### 3. **Use Built-in Web Search for Discovery**
- ✅ **Verified**: `mistralai.WebSearchTool()` is available
- ✅ **Decision**: `use_now`
- **Implementation**: Integrate as option B for business discovery
- **Note**: Requires Mistral API key; falls back to CSV import in mock mode

#### 4. **Implement Rate Limiting**
- ✅ **Verified**: Per-activity rate limiting is built-in
- ✅ **Decision**: `use_now`
- **Implementation**: 
  ```python
  @workflows.activity(
      rate_limit=workflows.RateLimit(time_window_in_sec=1, max_calls=10),
      key="website_inspection"
  )
  ```

#### 5. **Use Structured Outputs for All AI Calls**
- ✅ **Verified**: `chat_parse_to_model` and `response_format={"type": "json_object"}`
- ✅ **Decision**: `use_now`
- **Implementation**: All qualification and outreach outputs use Pydantic models

#### 6. **Use Local Activities for Fast Operations**
- ✅ **Verified**: Local activities for sub-second operations
- ✅ **Decision**: `use_now`
- **Implementation**: Normalization, deduplication, scoring calculations

### Post-MVP Enhancements

#### 1. **Add Hardened Deployment for OBO**
- ⚠️ **Conditional**: Required for on-behalf-of connectors
- ⚠️ **Decision**: `defer`
- **Prerequisites**: Hardened deployment configuration in Studio

#### 2. **Integrate Agentic Search**
- ⚠️ **Conditional**: Enhanced business discovery
- ⚠️ **Decision**: `defer`
- **Prerequisites**: Hardened deployment, OAuth configuration

#### 3. **Add MCP Tool Servers**
- ⚠️ **Conditional**: External tool integration
- ⚠️ **Decision**: `defer`
- **Use Case**: Custom business data sources

---

## Verification Evidence

### Source: Official Mistral Workflows SDK Documentation

All capabilities marked as ✅ **Verified** have been confirmed in the official Mistral documentation bundled with the SDK:

1. **Core Concepts**: `.agents/skills/workflows/references/getting-started/core-concepts.mdx`
2. **Activities**: `.agents/skills/workflows/references/guides/activities.mdx`
3. **Concurrency**: `.agents/skills/workflows/references/guides/concurrency.mdx`
4. **Observability**: `.agents/skills/workflows/references/guides/observability.mdx`
5. **Rate Limiting**: `.agents/skills/workflows/references/guides/rate-limiting.mdx`
6. **Durable Agents**: `.agents/skills/workflows/references/guides/durable-agents.mdx`
7. **Connectors**: `.agents/skills/workflows/references/guides/connectors.mdx`
8. **Python SDK**: `.agents/skills/workflows/references/getting-started/python-sdk.mdx`

### SDK Versions Verified

```
mistralai-workflows==3.16.0
mistralai==2.10.1
```

### Installation Verified

```bash
# Verified installation command
uv add 'mistralai-workflows[mistralai]'

# Verified dependencies
mistralai-workflows[mistralai]>=3.0.0,<4
pydantic>=2.0
python-dotenv>=1.0
httpx>=0.20
```

---

## Cost Considerations

### Included (No Additional Cost)
- Workflows orchestration
- Activities execution
- Retry policies
- Rate limiting
- OpenTelemetry observability
- Local activities
- Structured output parsing
- RemoteSession (uses standard API)

### Additional Cost (Per-Use)
- **Model API Calls**: All AI model usage (mistral-small, mistral-medium, etc.)
- **Web Search Tool**: Each web search query
- **External API Calls**: Any external services called via connectors or MCP

### Additional Cost (Infrastructure)
- **Hardened Deployment**: Required for OBO, Secrets Manager, Agentic Search
- **Multiple Workers**: Additional infrastructure for scaling

---

## Prerequisites Checklist

### For MVP (All ✅ Available)
- [x] Python 3.12+
- [x] uv/uvx package manager
- [x] Mistral API key
- [x] `mistralai-workflows[mistralai]` installed
- [x] Basic workflow worker configuration

### For Post-MVP (⚠️ Conditional)
- [ ] Hardened deployment configuration
- [ ] OAuth configuration for connectors
- [ ] Secrets Manager setup
- [ ] Agentic Search configuration

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-10-26 | Vibe Code | Initial capability mapping based on official Mistral documentation |

---

## References

1. [Mistral Workflows Documentation](https://docs.mistral.ai/studio/workflows)
2. [Mistral Studio Documentation](https://docs.mistral.ai/studio)
3. [Mistral API Reference](https://docs.mistral.ai/api)
4. [Mistral Models](https://docs.mistral.ai/models)
