from typing import Dict, Any, List
from .base_mcp import BaseMCPServer
import json
import uuid


class JiraMCPServer(BaseMCPServer):
    '''Mock Jira MCP Server (simulates Jira without real API)'''
    
    def __init__(self):
        super().__init__('jira-mcp')
        # Store mock tickets in memory
        self.tickets = []
    
    def get_tools(self) -> List[Dict[str, Any]]:
        '''Available Jira tools'''
        return [
            {
                'name': 'create_ticket',
                'description': 'Create a Jira ticket',
                'parameters': {
                    'title': 'Ticket title/summary',
                    'description': 'Detailed description',
                    'priority': 'P0/P1/P2/P3',
                    'ticket_type': 'Bug/Feature/Task'
                }
            },
            {
                'name': 'get_ticket',
                'description': 'Get ticket by ID',
                'parameters': {
                    'ticket_id': 'Ticket ID (e.g., BUG-123)'
                }
            },
            {
                'name': 'search_tickets',
                'description': 'Search for tickets',
                'parameters': {
                    'query': 'Search query',
                    'limit': 'Max results (default: 10)'
                }
            }
        ]
    
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        '''Execute Jira action'''
        self.log(f'Executing: {action}')
        
        if action == 'create_ticket':
            return self._create_ticket(params)
        elif action == 'get_ticket':
            return self._get_ticket(params)
        elif action == 'search_tickets':
            return self._search_tickets(params)
        else:
            return {
                'success': False,
                'error': f'Unknown action: {action}'
            }
    
    def _create_ticket(self, params: Dict[str, Any]) -> Dict[str, Any]:
        '''Mock creating a Jira ticket'''
        title = params.get('title', 'Untitled')
        description = params.get('description', '')
        priority = params.get('priority', 'P3')
        ticket_type = params.get('ticket_type', 'Task')
        
        # Generate ticket ID
        ticket_id = f'{ticket_type.upper()[:3]}-{len(self.tickets) + 1}'
        
        ticket = {
            'ticket_id': ticket_id,
            'title': title,
            'description': description,
            'priority': priority,
            'ticket_type': ticket_type,
            'status': 'Open',
            'created_at': '2026-01-30T12:00:00Z',
            'assignee': None
        }
        
        self.tickets.append(ticket)
        
        self.log(f'Ticket created: {ticket_id} - {title}')
        
        return {
            'success': True,
            'ticket_id': ticket_id,
            'ticket_url': f'https://jira.example.com/browse/{ticket_id}',
            'ticket': ticket
        }
    
    def _get_ticket(self, params: Dict[str, Any]) -> Dict[str, Any]:
        '''Mock getting a ticket'''
        ticket_id = params.get('ticket_id')
        
        # Find ticket
        ticket = next((t for t in self.tickets if t['ticket_id'] == ticket_id), None)
        
        if ticket:
            self.log(f'Ticket found: {ticket_id}')
            return {
                'success': True,
                'ticket': ticket
            }
        else:
            self.log(f'Ticket not found: {ticket_id}')
            return {
                'success': False,
                'error': f'Ticket {ticket_id} not found'
            }
    
    def _search_tickets(self, params: Dict[str, Any]) -> Dict[str, Any]:
        '''Mock searching tickets'''
        query = params.get('query', '').lower()
        limit = params.get('limit', 10)
        
        # Simple search in title and description
        results = [
            t for t in self.tickets
            if query in t['title'].lower() or query in t['description'].lower()
        ][:limit]
        
        self.log(f'Search found {len(results)} tickets for: {query}')
        
        return {
            'success': True,
            'tickets': results,
            'count': len(results)
        }
