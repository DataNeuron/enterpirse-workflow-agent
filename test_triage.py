import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agents.triage_agent import TriageAgent

print('='*60)
print('Testing Triage Agent')
print('='*60)
print()

agent = TriageAgent()

# Test cases
test_cases = [
    'The checkout page is broken! Customers cannot complete purchases!',
    'Can we add dark mode to the app?',
    'How do I reset my password?',
    'Site is completely down - getting 500 errors everywhere'
]

for i, test_input in enumerate(test_cases, 1):
    print(f'Test {i}: {test_input}')
    print('-' * 60)
    
    result = agent.classify_request(test_input)
    
    print(f'Category:  {result["category"]}')
    print(f'Priority:  {result["priority"]}')
    print(f'Reasoning: {result["reasoning"]}')
    print()

print('✅ All triage tests complete!')
