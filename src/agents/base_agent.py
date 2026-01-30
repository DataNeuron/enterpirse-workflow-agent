import boto3
import json
from typing import Dict, Any, Optional
import os
from datetime import datetime


class BaseAgent:
    '''Base class for all agents'''
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.model_id = os.getenv(
            'BEDROCK_MODEL_ID',
            'amazon.titan-text-express-v1'
        )
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.state_table = self.dynamodb.Table(
            os.getenv('DYNAMODB_STATE_TABLE', 'workflow-agent-agent-state')
        )
    
    def call_llm(self, prompt: str, max_tokens: int = 1000) -> str:
        '''Call LLM via Bedrock (supports Claude and Titan)'''
        try:
            # Different format for Claude vs Titan
            if 'claude' in self.model_id:
                body = {
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': max_tokens,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ]
                }
            else:  # Titan
                body = {
                    'inputText': prompt,
                    'textGenerationConfig': {
                        'maxTokenCount': max_tokens,
                        'temperature': 0.7
                    }
                }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            result = json.loads(response['body'].read())
            
            # Different response format for Claude vs Titan
            if 'claude' in self.model_id:
                return result['content'][0]['text']
            else:  # Titan
                return result['results'][0]['outputText']
            
        except Exception as e:
            print(f'❌ LLM Error in {self.agent_name}: {str(e)}')
            raise
    
    def save_state(self, workflow_id: str, state: Dict[str, Any]):
        '''Save workflow state to DynamoDB'''
        try:
            self.state_table.put_item(
                Item={
                    'workflow_id': workflow_id,
                    'timestamp': int(datetime.now().timestamp()),
                    'agent': self.agent_name,
                    'state': json.dumps(state),
                    'updated_at': datetime.now().isoformat()
                }
            )
            print(f'✅ State saved by {self.agent_name}')
        except Exception as e:
            print(f'❌ State save error: {str(e)}')
            raise
    
    def log(self, message: str):
        '''Simple logging'''
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{timestamp}] [{self.agent_name}] {message}')
