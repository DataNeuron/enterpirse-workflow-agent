from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Workflow metrics
workflows_started = Counter(
    'workflows_started_total',
    'Total workflows started',
    ['priority', 'category']
)

workflows_completed = Counter(
    'workflows_completed_total',
    'Total workflows completed',
    ['priority', 'category']
)

workflows_failed = Counter(
    'workflows_failed_total',
    'Total workflows failed',
    ['priority', 'category', 'error_type']
)

workflow_duration = Histogram(
    'workflow_duration_seconds',
    'Workflow execution duration',
    ['priority', 'category'],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

workflow_retries = Counter(
    'workflow_retries_total',
    'Total workflow retries',
    ['step']
)

# LLM metrics
bedrock_calls = Counter(
    'bedrock_calls_total',
    'Total Bedrock API calls',
    ['model', 'status']
)

bedrock_tokens = Counter(
    'bedrock_tokens_total',
    'Total tokens used',
    ['model', 'type']
)

bedrock_cost = Counter(
    'bedrock_cost_usd',
    'Total Bedrock cost in USD',
    ['model']
)

bedrock_latency = Histogram(
    'bedrock_latency_seconds',
    'Bedrock API latency',
    ['model'],
    buckets=[0.5, 1, 2, 5, 10, 30]
)

# Agent metrics
triage_total = Counter(
    'triage_total',
    'Total triage operations'
)

triage_correct = Counter(
    'triage_correct_total',
    'Correctly classified requests'
)

# MCP metrics
mcp_calls = Counter(
    'mcp_calls_total',
    'Total MCP server calls',
    ['server', 'action', 'status']
)

# System metrics
active_workflows = Gauge(
    'active_workflows',
    'Currently active workflows'
)


def get_metrics():
    '''Get Prometheus metrics'''
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


class MetricsCollector:
    '''Helper class to collect metrics'''
    
    @staticmethod
    def record_workflow_start(priority: str, category: str):
        workflows_started.labels(priority=priority, category=category).inc()
        active_workflows.inc()
    
    @staticmethod
    def record_workflow_complete(priority: str, category: str, duration: float):
        workflows_completed.labels(priority=priority, category=category).inc()
        workflow_duration.labels(priority=priority, category=category).observe(duration)
        active_workflows.dec()
    
    @staticmethod
    def record_workflow_failure(priority: str, category: str, error_type: str):
        workflows_failed.labels(priority=priority, category=category, error_type=error_type).inc()
        active_workflows.dec()
    
    @staticmethod
    def record_bedrock_call(model: str, tokens_input: int, tokens_output: int, 
                           latency: float, cost: float, success: bool):
        status = 'success' if success else 'error'
        bedrock_calls.labels(model=model, status=status).inc()
        bedrock_tokens.labels(model=model, type='input').inc(tokens_input)
        bedrock_tokens.labels(model=model, type='output').inc(tokens_output)
        bedrock_cost.labels(model=model).inc(cost)
        bedrock_latency.labels(model=model).observe(latency)
    
    @staticmethod
    def record_retry(step: str):
        workflow_retries.labels(step=step).inc()
    
    @staticmethod
    def record_mcp_call(server: str, action: str, success: bool):
        status = 'success' if success else 'error'
        mcp_calls.labels(server=server, action=action, status=status).inc()
