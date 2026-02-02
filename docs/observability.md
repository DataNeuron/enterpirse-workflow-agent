# Observability Stack

## Overview

This project includes comprehensive observability with Prometheus and Grafana.

## Metrics Collected

### Workflow Metrics
- \workflows_started_total\ - Total workflows started (by priority, category)
- \workflows_completed_total\ - Total workflows completed
- \workflows_failed_total\ - Total workflows failed (by error type)
- \workflow_duration_seconds\ - Workflow execution duration histogram
- \workflow_retries_total\ - Total retries by step
- \ctive_workflows\ - Currently active workflows (gauge)

### LLM Metrics (AWS Bedrock)
- \edrock_calls_total\ - Total Bedrock API calls (by model, status)
- \edrock_tokens_total\ - Total tokens used (input/output)
- \edrock_cost_usd\ - Total cost in USD
- \edrock_latency_seconds\ - API latency histogram

### Agent Metrics
- \	riage_total\ - Total triage operations
- \	riage_correct_total\ - Correctly classified requests

### MCP Metrics
- \mcp_calls_total\ - Total MCP server calls (by server, action, status)

## Quick Start

### Option 1: Docker Compose (Recommended)

\\\ash
# Start Prometheus and Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
\\\

### Option 2: Manual Installation

**Install Prometheus:**
\\\ash
# Download from https://prometheus.io/download/
# Run with:
prometheus --config.file=monitoring/prometheus/prometheus.yml
\\\

**Install Grafana:**
\\\ash
# Download from https://grafana.com/grafana/download
# Start Grafana server
# Import dashboard from monitoring/grafana/dashboards/workflow-overview.json
\\\

## Accessing Metrics

### Raw Metrics
\\\ash
curl http://localhost:8000/metrics
\\\

### Prometheus UI
- URL: http://localhost:9090
- Query example: \ate(workflows_started_total[5m])\

### Grafana Dashboards
- URL: http://localhost:3000
- Default credentials: admin / admin
- Dashboard: "Enterprise Workflow Automation - Overview"

## Key Dashboard Panels

1. **Workflow Success Rate** - Real-time success percentage
2. **Total Workflows** - Daily workflow count
3. **Average Duration** - Mean workflow execution time
4. **LLM Cost** - Daily Bedrock spending
5. **Workflows by Priority** - P0/P1/P2/P3 distribution
6. **Execution Timeline** - Started/Completed/Failed over time
7. **Classification Accuracy** - Triage agent performance
8. **Retry Rate** - Retries by workflow step
9. **Token Usage** - Bedrock token consumption

## Alerts (Future Enhancement)

Prometheus alerting rules can be added for:
- Success rate < 90%
- Average duration > 5 minutes
- Daily cost > \
- Error rate > 5%

## Cost Tracking

The dashboard shows real-time AWS Bedrock costs:
- Input tokens: \.00 per 1M tokens
- Output tokens: \.00 per 1M tokens

Example calculation:
\\\
Workflow with 100 tokens input, 50 tokens output:
Cost = (100 * 0.000003) + (50 * 0.000015) = \.00105
\\\

## Performance Benchmarks

Target metrics (dev environment):
- Success rate: > 95%
- P95 duration: < 10s
- Daily cost: < \
- Retry rate: < 5%
