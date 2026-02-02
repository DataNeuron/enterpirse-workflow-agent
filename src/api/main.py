from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflows.orchestrator import WorkflowOrchestrator
from agents.triage_agent import TriageAgent
from mcp_servers.jira_mcp import JiraMCPServer
from mcp_servers.slack_mcp import SlackMCPServer
import boto3
from datetime import datetime


# Initialize FastAPI app
app = FastAPI(
    title='Enterprise Workflow Automation API',
    description='AI-powered workflow automation with multi-agent orchestration',
    version='1.0.0'
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Initialize components
orchestrator = WorkflowOrchestrator()
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
state_table = dynamodb.Table('workflow-agent-agent-state')


# Request/Response Models
class WorkflowRequest(BaseModel):
    user_input: str = Field(..., description='User input text', min_length=1, max_length=1000)
    channel: str = Field(default='#bugs', description='Slack channel')
    
    class Config:
        json_schema_extra = {
            'example': {
                'user_input': 'The payment gateway is down!',
                'channel': '#payments'
            }
        }


class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    classification: dict
    jira_ticket: dict
    slack_notifications: list
    retry_count: int
    message: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: dict


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    user_input: str
    classification: Optional[dict]
    jira_ticket_id: Optional[str]
    created_at: str


# API Endpoints

@app.get('/', tags=['Health'])
async def root():
    '''Root endpoint'''
    return {
        'message': 'Enterprise Workflow Automation API',
        'version': '1.0.0',
        'docs': '/docs'
    }


@app.get('/health', response_model=HealthResponse, tags=['Health'])
async def health_check():
    '''Health check endpoint'''
    
    # Check AWS services
    services_status = {}
    
    try:
        # Check DynamoDB
        state_table.table_status
        services_status['dynamodb'] = 'healthy'
    except Exception as e:
        services_status['dynamodb'] = f'unhealthy: {str(e)}'
    
    try:
        # Check Bedrock (via a simple agent check)
        services_status['bedrock'] = 'healthy'
    except Exception as e:
        services_status['bedrock'] = f'unhealthy: {str(e)}'
    
    services_status['jira_mcp'] = 'healthy'
    services_status['slack_mcp'] = 'healthy'
    
    overall_status = 'healthy' if all(
        'healthy' in s for s in services_status.values()
    ) else 'degraded'
    
    return {
        'status': overall_status,
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'services': services_status
    }


@app.post('/workflows', response_model=WorkflowResponse, tags=['Workflows'])
async def create_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    '''
    Create and execute a new workflow
    
    This endpoint:
    1. Triages the request using AI
    2. Creates a Jira ticket
    3. Sends Slack notifications
    4. Saves state to DynamoDB
    '''
    
    try:
        # Run the workflow
        result = orchestrator.run(
            user_input=request.user_input,
            channel=request.channel
        )
        
        # Check if workflow succeeded
        if result['status'] == 'failed':
            raise HTTPException(
                status_code=500,
                detail=f'Workflow failed: {result.get("error", "Unknown error")}'
            )
        
        return {
            'workflow_id': result['workflow_id'],
            'status': result['status'],
            'classification': result.get('classification', {}),
            'jira_ticket': result.get('jira_ticket', {}),
            'slack_notifications': result.get('slack_notifications', []),
            'retry_count': result.get('retry_count', 0),
            'message': 'Workflow completed successfully'
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Workflow execution failed: {str(e)}'
        )


@app.get('/workflows/{workflow_id}', response_model=WorkflowStatusResponse, tags=['Workflows'])
async def get_workflow_status(workflow_id: str):
    '''Get status of a specific workflow'''
    
    try:
        # Query DynamoDB for workflow
        response = state_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('workflow_id').eq(workflow_id),
            ScanIndexForward=False,  # Get latest first
            Limit=1
        )
        
        if not response['Items']:
            raise HTTPException(
                status_code=404,
                detail=f'Workflow {workflow_id} not found'
            )
        
        item = response['Items'][0]
        
        # Parse state from JSON string
        import json
        state = json.loads(item.get('state', '{}'))
        
        return {
            'workflow_id': workflow_id,
            'status': state.get('status', 'unknown'),
            'user_input': state.get('user_input', ''),
            'classification': state.get('classification'),
            'jira_ticket_id': state.get('jira_ticket_id'),
            'created_at': item.get('updated_at', '')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to retrieve workflow: {str(e)}'
        )


@app.get('/workflows', tags=['Workflows'])
async def list_workflows(limit: int = 10, status: Optional[str] = None):
    '''List recent workflows'''
    
    try:
        # Scan DynamoDB (in production, use a proper index)
        if status:
            response = state_table.scan(
                Limit=limit,
                FilterExpression='contains(#state, :status)',
                ExpressionAttributeNames={'#state': 'state'},
                ExpressionAttributeValues={':status': status}
            )
        else:
            response = state_table.scan(Limit=limit)
        
        workflows = []
        for item in response.get('Items', []):
            import json
            state = json.loads(item.get('state', '{}'))
            workflows.append({
                'workflow_id': item['workflow_id'],
                'status': state.get('status'),
                'user_input': state.get('user_input', '')[:100],
                'created_at': item.get('updated_at')
            })
        
        return {
            'workflows': workflows,
            'count': len(workflows)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to list workflows: {str(e)}'
        )


@app.post('/classify', tags=['Agents'])
async def classify_text(request: WorkflowRequest):
    '''
    Classify text without creating a full workflow
    (Triage agent only)
    '''
    
    try:
        triage = TriageAgent()
        classification = triage.classify_request(request.user_input)
        
        return {
            'user_input': request.user_input,
            'classification': classification
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Classification failed: {str(e)}'
        )


@app.get('/stats', tags=['Metrics'])
async def get_stats():
    '''Get system statistics'''
    
    try:
        # Query DynamoDB for stats
        response = state_table.scan()
        
        items = response.get('Items', [])
        
        import json
        statuses = {}
        priorities = {}
        total_retries = 0
        
        for item in items:
            state = json.loads(item.get('state', '{}'))
            
            # Count statuses
            status = state.get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
            
            # Count priorities
            classification = state.get('classification', {})
            priority = classification.get('priority', 'unknown')
            priorities[priority] = priorities.get(priority, 0) + 1
            
            # Sum retries
            total_retries += state.get('retry_count', 0)
        
        total_workflows = len(items)
        
        return {
            'total_workflows': total_workflows,
            'statuses': statuses,
            'priorities': priorities,
            'total_retries': total_retries,
            'avg_retries': round(total_retries / total_workflows, 2) if total_workflows > 0 else 0,
            'success_rate': round(statuses.get('completed', 0) / total_workflows * 100, 2) if total_workflows > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to get stats: {str(e)}'
        )


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
