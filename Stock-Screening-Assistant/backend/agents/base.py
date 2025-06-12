# backend/agents/base.py
from abc import ABC, abstractmethod
from langchain_core.runnables import Runnable
from typing import Any, Dict

class BaseAgent(Runnable, ABC):
    @abstractmethod
    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        pass
