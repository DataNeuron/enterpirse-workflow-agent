from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from agents.triage_agent import TriageAgent
from mcp_servers.slack_mcp import SlackMCPServer
from mcp_servers.jira_mcp import JiraMCPServer
import uuid
from datetime import datetime


# Define the state that flows through the workflow
class WorkflowState(TypedDict):
    workflow_id: str
    user_input: str
    channel: str
    classification: dict
    jira_ticket: dict
    slack_notifications: list
    status: str
    error: str


class WorkflowOrchestrator:
    '''Orchestrates multi-agent workflow using LangGraph'''
    
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.slack_mcp = SlackMCPServer()
        self.jira_mcp = JiraMCPServer()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        '''Build the LangGraph workflow'''
        
        # Create the graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes (steps in the workflow)
        workflow.add_node('triage', self._triage_step)
        workflow.add_node('create_jira', self._create_jira_step)
        workflow.add_node('notify_slack', self._notify_slack_step)
        workflow.add_node('finalize', self._finalize_step)
        
        # Define the flow
        workflow.set_entry_point('triage')
        workflow.add_edge('triage', 'create_jira')
        workflow.add_edge('create_jira', 'notify_slack')
        workflow.add_edge('notify_slack', 'finalize')
        workflow.add_edge('finalize', END)
        
        return workflow.compile()
    
    def _triage_step(self, state: WorkflowState) -> WorkflowState:
        '''Step 1: Classify the request'''
        print('[Orchestrator] Step 1: Triaging request...')
        
        classification = self.triage_agent.classify_request(state['user_input'])
        
        state['classification'] = classification
        state['status'] = 'triaged'
        
        return state
    
    def _create_jira_step(self, state: WorkflowState) -> WorkflowState:
        '''Step 2: Create Jira ticket'''
        print('[Orchestrator] Step 2: Creating Jira ticket...')
        
        classification = state['classification']
        
        # Create ticket
        result = self.jira_mcp.execute('create_ticket', {
            'title': state['user_input'][:100],  # Truncate if too long
            'description': f'''User Report: {state['user_input']}

Classification:
- Category: {classification['category']}
- Priority: {classification['priority']}
- Reasoning: {classification['reasoning']}

Workflow ID: {state['workflow_id']}''',
            'priority': classification['priority'],
            'ticket_type': classification['category'].capitalize()
        })
        
        state['jira_ticket'] = result
        state['status'] = 'jira_created'
        
        return state
    
    def _notify_slack_step(self, state: WorkflowState) -> WorkflowState:
        '''Step 3: Send Slack notifications'''
        print('[Orchestrator] Step 3: Sending Slack notifications...')
        
        classification = state['classification']
        jira_ticket = state['jira_ticket']
        
        # Determine channel based on priority
        if classification['priority'] in ['P0', 'P1']:
            channels = ['#alerts', state['channel']]
        else:
            channels = [state['channel']]
        
        notifications = []
        
        for channel in channels:
            message = f'''🎫 New {classification['category'].upper()} - {classification['priority']}

Issue: {state['user_input'][:200]}

Jira Ticket: {jira_ticket['ticket_id']}
URL: {jira_ticket['ticket_url']}

Workflow ID: {state['workflow_id']}'''
            
            result = self.slack_mcp.execute('send_message', {
                'channel': channel,
                'text': message
            })
            
            notifications.append({
                'channel': channel,
                'message_id': result.get('message_id'),
                'success': result.get('success')
            })
        
        state['slack_notifications'] = notifications
        state['status'] = 'notifications_sent'
        
        return state
    
    def _finalize_step(self, state: WorkflowState) -> WorkflowState:
        '''Step 4: Finalize workflow'''
        print('[Orchestrator] Step 4: Finalizing workflow...')
        
        # Save final state to DynamoDB
        self.triage_agent.save_state(state['workflow_id'], {
            'user_input': state['user_input'],
            'classification': state['classification'],
            'jira_ticket_id': state['jira_ticket']['ticket_id'],
            'slack_notifications': state['slack_notifications'],
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        })
        
        state['status'] = 'completed'
        
        workflow_id = state['workflow_id']
        print(f'[Orchestrator] ✅ Workflow {workflow_id} completed!')
        
        return state
    
    def run(self, user_input: str, channel: str = '#bugs') -> WorkflowState:
        '''Run the complete workflow'''
        
        # Initialize state
        initial_state = {
            'workflow_id': str(uuid.uuid4())[:8],
            'user_input': user_input,
            'channel': channel,
            'classification': {},
            'jira_ticket': {},
            'slack_notifications': [],
            'status': 'started',
            'error': ''
        }
        
        workflow_id = initial_state['workflow_id']
        print(f'[Orchestrator] Starting workflow: {workflow_id}')
        print(f'[Orchestrator] Input: {user_input[:50]}...')
        print()
        
        # Run the workflow
        final_state = self.workflow.invoke(initial_state)
        
        return final_state
