from typing import Dict, Any, List
from abc import ABC, abstractmethod


class BaseMCPServer(ABC):
    '''Base class for all MCP servers'''
    
    def __init__(self, server_name: str):
        self.server_name = server_name
    
    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        '''Return list of available tools/actions'''
        pass
    
    @abstractmethod
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        '''Execute an action with given parameters'''
        pass
    
    def log(self, message: str):
        '''Simple logging'''
        print(f'[{self.server_name}] {message}')
