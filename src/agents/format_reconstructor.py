from typing import List, Dict, Any
from ..tools.srt_utils import SRTSubtitle, generate_srt
from ..graph_orchestrator import AgentStatus

class FormatReconstructorAgent:
    def __init__(self, orchestrator):
        self.name = "Format Reconstructor"
        self.orchestrator = orchestrator
        
    def process(self, translated_subtitles: List[SRTSubtitle]) -> Dict[str, Any]:
        self.orchestrator.update_agent_status("reconstructor", AgentStatus.RUNNING, "重构SRT格式...")
        
        try:
            output_srt = generate_srt(translated_subtitles)
            
            self.orchestrator.update_agent_status(
                "reconstructor", 
                AgentStatus.COMPLETED, 
                "SRT格式重构完成"
            )
            
            return {
                "output_srt": output_srt,
                "success": True
            }
        except Exception as e:
            self.orchestrator.update_agent_status("reconstructor", AgentStatus.ERROR, f"格式重构失败: {str(e)}")
            return {"success": False, "error": str(e)}
