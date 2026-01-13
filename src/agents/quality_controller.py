from typing import List, Dict, Any
from ..tools.srt_utils import SRTSubtitle
from ..graph_orchestrator import AgentStatus

class QualityControllerAgent:
    def __init__(self, orchestrator):
        self.name = "Quality Controller"
        self.orchestrator = orchestrator
        
    def process(self, original_subtitles: List[SRTSubtitle], translated_subtitles: List[SRTSubtitle]) -> Dict[str, Any]:
        self.orchestrator.update_agent_status("quality", AgentStatus.RUNNING, "检查翻译质量...")
        
        try:
            issues = []
            
            # Check count consistency
            if len(original_subtitles) != len(translated_subtitles):
                issues.append("字幕数量不匹配")
            
            # Check for empty translations
            empty_count = sum(1 for sub in translated_subtitles if not sub.text.strip())
            if empty_count > 0:
                issues.append(f"发现{empty_count}条空翻译")
            
            # Check timing consistency
            for orig, trans in zip(original_subtitles, translated_subtitles):
                if orig.start != trans.start or orig.end != trans.end:
                    issues.append(f"时间戳不匹配: 字幕{orig.index}")
            
            quality_score = max(0, 100 - len(issues) * 10)
            
            if issues:
                message = f"发现{len(issues)}个问题，质量分数: {quality_score}"
            else:
                message = f"质量检查通过，分数: {quality_score}"
                
            self.orchestrator.update_agent_status("quality", AgentStatus.COMPLETED, message)
            
            return {
                "quality_score": quality_score,
                "issues": issues,
                "passed": len(issues) == 0,
                "success": True
            }
        except Exception as e:
            self.orchestrator.update_agent_status("quality", AgentStatus.ERROR, f"质量检查失败: {str(e)}")
            return {"success": False, "error": str(e)}
