import sys
import os
import uuid
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agents.triage_agent import TriageAgent
from mcp_servers.slack_mcp import SlackMCPServer


def run_workflow(user_input: str, channel: str = '#bugs'):
    '''Complete workflow: Receive message -> Triage -> Send to Slack'''
    
    workflow_id = str(uuid.uuid4())[:8]
    
    print('='*60)
    print(f'WORKFLOW: {workflow_id}')
    print('='*60)
    print(f'Input: {user_input}')
    print(f'Channel: {channel}')
    print()
    
    # Step 1: Triage the request
    print('STEP 1: Triaging request...')
    triage = TriageAgent()
    classification = triage.classify_request(user_input)
    
    print(f'  Category: {classification["category"]}')
    print(f'  Priority: {classification["priority"]}')
    print(f'  Reasoning: {classification["reasoning"]}')
    print()
    
    # Step 2: Save state to DynamoDB
    print('STEP 2: Saving workflow state...')
    triage.save_state(workflow_id, {
        'user_input': user_input,
        'classification': classification,
        'status': 'triaged'
    })
    print()
    
    # Step 3: Send notification to Slack
    print('STEP 3: Sending Slack notification...')
    slack = SlackMCPServer()
    
    # Determine channel based on priority
    if classification['priority'] in ['P0', 'P1']:
        notification_channel = '#alerts'
    else:
        notification_channel = channel
    
    message = f'''🚨 New {classification["category"].upper()} - {classification["priority"]}
Issue: {user_input}
Workflow ID: {workflow_id}
Classification: {classification["reasoning"]}'''
    
    result = slack.execute('send_message', {
        'channel': notification_channel,
        'text': message
    })
    
    print(f'  Message sent to {notification_channel}')
    print(f'  Message ID: {result["message_id"]}')
    print()
    
    print('✅ WORKFLOW COMPLETE')
    print('='*60)
    print()
    
    return {
        'workflow_id': workflow_id,
        'classification': classification,
        'slack_result': result
    }


# Run test workflows
print('ENTERPRISE WORKFLOW AUTOMATION DEMO')
print('='*60)
print()

# Test Case 1: Critical incident
print('TEST CASE 1: Critical Incident')
result1 = run_workflow(
    'Site is completely down! Getting 500 errors on all pages. Customers cannot access anything.'
)

# Test Case 2: Feature request
print('TEST CASE 2: Feature Request')
result2 = run_workflow(
    'Can we add a dark mode option to the settings page?'
)

# Test Case 3: Bug report
print('TEST CASE 3: Bug Report')
result3 = run_workflow(
    'The checkout button is not responding when I click it on mobile.'
)

print('='*60)
print('SUMMARY')
print('='*60)
print(f'Workflows processed: 3')
print(f'Critical incidents: {sum(1 for r in [result1, result2, result3] if r["classification"]["priority"] == "P0")}')
print(f'High priority: {sum(1 for r in [result1, result2, result3] if r["classification"]["priority"] == "P1")}')
print()
print('✅ All workflows completed successfully!')
