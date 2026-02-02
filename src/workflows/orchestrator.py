from typing import TypedDict
from langgraph.graph import StateGraph, END
from agents.triage_agent import TriageAgent
from mcp_servers.slack_mcp import SlackMCPServer
from mcp_servers.jira_mcp import JiraMCPServer
import uuid
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    workflow_id: str
    user_input: str
    channel: str
    classification: dict
    jira_ticket: dict
    slack_notifications: list
    status: str
    error: str
    retry_count: int


class WorkflowOrchestrator:
    '''Orchestrates multi-agent workflow with error handling'''
    
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.slack_mcp = SlackMCPServer()
        self.jira_mcp = JiraMCPServer()
        self.workflow = self._build_workflow()
        self.max_retries = 3
    
    def _build_workflow(self) -> StateGraph:
        '''Build the LangGraph workflow with error handling'''
        
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node('triage', self._triage_step)
        workflow.add_node('create_jira', self._create_jira_step)
        workflow.add_node('notify_slack', self._notify_slack_step)
        workflow.add_node('finalize', self._finalize_step)
        workflow.add_node('handle_error', self._handle_error)
        
        # Define the flow
        workflow.set_entry_point('triage')
        
        # Conditional edges for error handling
        workflow.add_conditional_edges(
            'triage',
            self._check_for_errors,
            {
                'success': 'create_jira',
                'error': 'handle_error'
            }
        )
        
        workflow.add_conditional_edges(
            'create_jira',
            self._check_for_errors,
            {
                'success': 'notify_slack',
                'error': 'handle_error'
            }
        )
        
        workflow.add_conditional_edges(
            'notify_slack',
            self._check_for_errors,
            {
                'success': 'finalize',
                'error': 'handle_error'
            }
        )
        
        workflow.add_edge('finalize', END)
        workflow.add_edge('handle_error', END)
        
        return workflow.compile()
    
    def _check_for_errors(self, state: WorkflowState) -> str:
        '''Check if there were errors in the last step'''
        if state.get('error'):
            return 'error'
        return 'success'
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        '''Manual retry with exponential backoff'''
        max_attempts = 3
        wait_time = 2
        
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                logger.warning(f'Attempt {attempt + 1} failed: {str(e)}, retrying in {wait_time}s...')
                time.sleep(wait_time)
                wait_time *= 2
    
    def _triage_step(self, state: WorkflowState) -> WorkflowState:
        '''Step 1: Classify the request'''
        print('[Orchestrator] Step 1: Triaging request...')
        
        try:
            classification = self._retry_with_backoff(
                self.triage_agent.classify_request,
                state['user_input']
            )
            state['classification'] = classification
            state['status'] = 'triaged'
            state['error'] = ''
            
        except Exception as e:
            logger.error(f'Triage failed: {str(e)}')
            state['error'] = f'Triage error: {str(e)}'
            state['retry_count'] = state.get('retry_count', 0) + 1
        
        return state
    
    def _create_jira_step(self, state: WorkflowState) -> WorkflowState:
        '''Step 2: Create Jira ticket'''
        print('[Orchestrator] Step 2: Creating Jira ticket...')
        
        try:
            classification = state['classification']
            
            result = self._retry_with_backoff(
                self.jira_mcp.execute,
                'create_ticket',
                {
                    'title': state['user_input'][:100],
                    'description': f'''User Report: {state['user_input']}

Classification:
- Category: {classification['category']}
- Priority: {classification['priority']}
- Reasoning: {classification['reasoning']}

Workflow ID: {state['workflow_id']}''',
                    'priority': classification['priority'],
                    'ticket_type': classification['category'].capitalize()
                }
            )
            
            if not result.get('success'):
                raise Exception(f'Jira creation failed: {result.get("error")}')
            
            state['jira_ticket'] = result
            state['status'] = 'jira_created'
            state['error'] = ''
            
        except Exception as e:
            logger.error(f'Jira creation failed: {str(e)}')
            state['error'] = f'Jira error: {str(e)}'
            state['retry_count'] = state.get('retry_count', 0) + 1
        
        return state
    
    def _notify_slack_step(self, state: WorkflowState) -> WorkflowState:
        '''Step 3: Send Slack notifications'''
        print('[Orchestrator] Step 3: Sending Slack notifications...')
        
        try:
            classification = state['classification']
            jira_ticket = state['jira_ticket']
            
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
                
                result = self._retry_with_backoff(
                    self.slack_mcp.execute,
                    'send_message',
                    {
                        'channel': channel,
                        'text': message
                    }
                )
                
                if not result.get('success'):
                    raise Exception(f'Slack notification failed for {channel}')
                
                notifications.append({
                    'channel': channel,
                    'message_id': result.get('message_id'),
                    'success': result.get('success')
                })
            
            state['slack_notifications'] = notifications
            state['status'] = 'notifications_sent'
            state['error'] = ''
            
        except Exception as e:
            logger.error(f'Slack notification failed: {str(e)}')
            state['error'] = f'Slack error: {str(e)}'
            state['retry_count'] = state.get('retry_count', 0) + 1
        
        return state
    
    def _finalize_step(self, state: WorkflowState) -> WorkflowState:
        '''Step 4: Finalize workflow'''
        print('[Orchestrator] Step 4: Finalizing workflow...')
        
        try:
            self.triage_agent.save_state(state['workflow_id'], {
                'user_input': state['user_input'],
                'classification': state.get('classification', {}),
                'jira_ticket_id': state.get('jira_ticket', {}).get('ticket_id'),
                'slack_notifications': state.get('slack_notifications', []),
                'status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'retry_count': state.get('retry_count', 0)
            })
            
            state['status'] = 'completed'
            
            workflow_id = state['workflow_id']
            print(f'[Orchestrator] ✅ Workflow {workflow_id} completed!')
            
        except Exception as e:
            logger.error(f'Finalization failed: {str(e)}')
            state['error'] = f'Finalize error: {str(e)}'
        
        return state
    
    def _handle_error(self, state: WorkflowState) -> WorkflowState:
        '''Handle workflow errors'''
        print(f'[Orchestrator] ❌ Workflow failed: {state["error"]}')
        
        try:
            self.triage_agent.save_state(state['workflow_id'], {
                'user_input': state['user_input'],
                'status': 'failed',
                'error': state['error'],
                'retry_count': state.get('retry_count', 0),
                'failed_at': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f'Error state save failed: {str(e)}')
        
        state['status'] = 'failed'
        
        return state
    
    def run(self, user_input: str, channel: str = '#bugs') -> WorkflowState:
        '''Run the complete workflow with error handling'''
        
        initial_state = {
            'workflow_id': str(uuid.uuid4())[:8],
            'user_input': user_input,
            'channel': channel,
            'classification': {},
            'jira_ticket': {},
            'slack_notifications': [],
            'status': 'started',
            'error': '',
            'retry_count': 0
        }
        
        workflow_id = initial_state['workflow_id']
        print(f'[Orchestrator] Starting workflow: {workflow_id}')
        print(f'[Orchestrator] Input: {user_input[:50]}...')
        print()
        
        try:
            final_state = self.workflow.invoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f'Workflow execution failed: {str(e)}')
            initial_state['status'] = 'failed'
            initial_state['error'] = str(e)
            return initial_state
