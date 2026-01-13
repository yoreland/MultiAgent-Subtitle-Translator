from typing import Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum

class AgentStatus(Enum):
    WAITING = "⏳ 等待中"
    RUNNING = "🔄 运行中"
    COMPLETED = "✅ 已完成"
    ERROR = "❌ 错误"

@dataclass
class AgentState:
    name: str
    status: AgentStatus
    message: str = ""
    progress: int = 0

class GraphOrchestrator:
    def __init__(self):
        self.agents_state = {
            "parser": AgentState("SRT解析器", AgentStatus.WAITING),
            "analyzer": AgentState("术语分析器", AgentStatus.WAITING),
            "translator": AgentState("翻译器", AgentStatus.WAITING),
            "quality": AgentState("质量控制器", AgentStatus.WAITING),
            "reconstructor": AgentState("格式重构器", AgentStatus.WAITING)
        }
        self.status_callback = None
    
    def update_agent_status(self, agent_name: str, status: AgentStatus, message: str = "", progress: int = 0):
        if agent_name in self.agents_state:
            self.agents_state[agent_name].status = status
            self.agents_state[agent_name].message = message
            self.agents_state[agent_name].progress = progress
            
            if self.status_callback:
                self.status_callback(self.agents_state)
    
    def get_status_summary(self) -> str:
        lines = []
        for agent_name, state in self.agents_state.items():
            progress_bar = ""
            if state.progress > 0:
                progress_bar = f" ({state.progress}%)"
            lines.append(f"{state.status.value} {state.name}{progress_bar}")
            if state.message:
                lines.append(f"   └─ {state.message}")
        return "\n".join(lines)
