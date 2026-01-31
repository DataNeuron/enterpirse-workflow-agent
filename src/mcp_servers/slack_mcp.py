from typing import Dict, Any, List
from .base_mcp import BaseMCPServer
import json


class SlackMCPServer(BaseMCPServer):
    '''Mock Slack MCP Server (simulates Slack without real API)'''
    
    def __init__(self):
        super().__init__('slack-mcp')
        # Store mock messages in memory
        self.messages = []
    
    def get_tools(self) -> List[Dict[str, Any]]:
        '''Available Slack tools'''
        return [
            {
                'name': 'send_message',
                'description': 'Send a message to a Slack channel',
                'parameters': {
                    'channel': 'Channel name (e.g., #bugs)',
                    'text': 'Message text'
                }
            },
            {
                'name': 'get_messages',
                'description': 'Get recent messages from a channel',
                'parameters': {
                    'channel': 'Channel name',
                    'limit': 'Number of messages (default: 10)'
                }
            }
        ]
    
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        '''Execute Slack action'''
        self.log(f'Executing: {action}')
        
        if action == 'send_message':
            return self._send_message(params)
        elif action == 'get_messages':
            return self._get_messages(params)
        else:
            return {
                'success': False,
                'error': f'Unknown action: {action}'
            }
    
    def _send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        '''Mock sending a message'''
        channel = params.get('channel', '#general')
        text = params.get('text', '')
        
        message = {
            'channel': channel,
            'text': text,
            'timestamp': '1234567890.123456',
            'user': 'workflow-agent'
        }
        
        self.messages.append(message)
        
        self.log(f'Message sent to {channel}: {text[:50]}...')
        
        return {
            'success': True,
            'message_id': message['timestamp'],
            'channel': channel
        }
    
    def _get_messages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        '''Mock getting messages'''
        channel = params.get('channel', '#general')
        limit = params.get('limit', 10)
        
        channel_messages = [
            m for m in self.messages 
            if m['channel'] == channel
        ][-limit:]
        
        self.log(f'Retrieved {len(channel_messages)} messages from {channel}')
        
        return {
            'success': True,
            'messages': channel_messages,
            'count': len(channel_messages)
        }
