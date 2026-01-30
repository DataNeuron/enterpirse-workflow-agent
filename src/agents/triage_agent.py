from typing import Dict, Any
from .base_agent import BaseAgent


class TriageAgent(BaseAgent):
    '''Classifies and prioritizes incoming requests'''
    
    def __init__(self):
        super().__init__('triage-agent')
    
    def classify_request(self, user_input: str) -> Dict[str, Any]:
        '''
        Classify a user request into category and priority
        
        Returns:
            {
                'category': 'bug' | 'feature' | 'question' | 'incident',
                'priority': 'P0' | 'P1' | 'P2' | 'P3',
                'reasoning': 'explanation of classification'
            }
        '''
        self.log(f'Classifying request: {user_input[:50]}...')
        
        prompt = f'''Analyze this user request and classify it.

User Request: {user_input}

Provide your analysis in this exact format:
Category: [bug/feature/question/incident]
Priority: [P0/P1/P2/P3]
Reasoning: [brief explanation]

Priority guidelines:
- P0: System down, revenue impacted, security breach
- P1: Major feature broken, affects many users
- P2: Minor bug, affects some users
- P3: Enhancement, cosmetic issue

Category guidelines:
- bug: Something is broken
- feature: Request for new functionality
- question: Asking for help or information
- incident: Active emergency or outage'''

        response = self.call_llm(prompt, max_tokens=500)
        
        # Parse the response
        result = self._parse_classification(response)
        
        self.log(f'Classification: {result["category"]} / {result["priority"]}')
        
        return result
    
    def _parse_classification(self, response: str) -> Dict[str, Any]:
        '''Parse LLM response into structured format'''
        lines = response.strip().split('\n')
        
        result = {
            'category': 'question',  # default
            'priority': 'P3',        # default
            'reasoning': 'Could not parse response'
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith('Category:'):
                category = line.split(':', 1)[1].strip().lower()
                if category in ['bug', 'feature', 'question', 'incident']:
                    result['category'] = category
            
            elif line.startswith('Priority:'):
                priority = line.split(':', 1)[1].strip().upper()
                if priority in ['P0', 'P1', 'P2', 'P3']:
                    result['priority'] = priority
            
            elif line.startswith('Reasoning:'):
                result['reasoning'] = line.split(':', 1)[1].strip()
        
        return result
