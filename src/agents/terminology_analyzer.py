from typing import List, Dict, Any
from ..tools.llm_client import LLMClient
from ..tools.srt_utils import SRTSubtitle
from ..graph_orchestrator import AgentStatus

class TerminologyAnalyzer:
    def __init__(self, orchestrator):
        self.name = "Terminology Analyzer"
        self.orchestrator = orchestrator
        self.llm_client = LLMClient()
        
    def process(self, segments: List[Dict[str, Any]], terminology: List[str]) -> Dict[str, Any]:
        self.orchestrator.update_agent_status("analyzer", AgentStatus.RUNNING, "分析段落结构和术语...")
        
        try:
            # 分析段落统计信息
            total_chars = sum(segment['total_chars'] for segment in segments)
            avg_segment_length = total_chars / len(segments) if segments else 0
            
            # 术语分类（简化版本）
            terminology_db = {}
            for term in terminology:
                terminology_db[term] = {
                    'category': 'technical' if term.isupper() else 'proper_noun',
                    'frequency': 1  # 简化处理
                }
            
            self.orchestrator.update_agent_status(
                "analyzer", 
                AgentStatus.COMPLETED, 
                f"分析完成: {len(segments)}个段落, 平均{int(avg_segment_length)}字符, {len(terminology)}个术语"
            )
            
            return {
                "segments": segments,
                "terminology_db": terminology_db,
                "terminology": terminology,
                "segment_stats": {
                    "total_segments": len(segments),
                    "total_chars": total_chars,
                    "avg_length": avg_segment_length
                },
                "success": True
            }
        except Exception as e:
            self.orchestrator.update_agent_status("analyzer", AgentStatus.ERROR, f"分析失败: {str(e)}")
            return {"success": False, "error": str(e)}
