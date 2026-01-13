from typing import List, Dict, Any, Callable
from .graph_orchestrator import GraphOrchestrator, AgentStatus
from .agents.srt_parser import SRTParserAgent
from .agents.terminology_analyzer import TerminologyAnalyzer
from .agents.translator import TranslatorAgent
from .agents.quality_controller import QualityControllerAgent
from .agents.format_reconstructor import FormatReconstructorAgent

class TranslationGraph:
    def __init__(self):
        self.orchestrator = GraphOrchestrator()
        
        # Initialize agents with orchestrator reference
        self.parser = SRTParserAgent(self.orchestrator)
        self.analyzer = TerminologyAnalyzer(self.orchestrator)
        self.translator = TranslatorAgent(self.orchestrator)
        self.quality_controller = QualityControllerAgent(self.orchestrator)
        self.reconstructor = FormatReconstructorAgent(self.orchestrator)
        
    def set_status_callback(self, callback: Callable):
        self.orchestrator.status_callback = callback
        
    def execute_translation(self, srt_content: str, target_lang: str, video_path: str = None) -> Dict[str, Any]:
        try:
            # 设置视频路径
            if video_path:
                self.translator.set_video_path(video_path)
            
            # Step 1: Parse SRT and generate segments
            parse_result = self.parser.process(srt_content)
            if not parse_result.get("success"):
                return parse_result
            
            subtitles = parse_result["subtitles"]
            segments = parse_result["segments"]
            terminology = parse_result["terminology"]
            
            # Step 2: Analyze segments and terminology
            analysis_result = self.analyzer.process(segments, terminology)
            if not analysis_result.get("success"):
                return analysis_result
            
            # Step 3: Translate by segments (maintaining context)
            translated_subtitles = self.translator.process(segments, target_lang, terminology)
            if not translated_subtitles:
                return {"success": False, "error": "Translation failed"}
            
            # Step 4: Quality Control
            quality_result = self.quality_controller.process(subtitles, translated_subtitles)
            if not quality_result.get("success"):
                return quality_result
            
            # Step 5: Format Reconstruction
            reconstruction_result = self.reconstructor.process(translated_subtitles)
            if not reconstruction_result.get("success"):
                return reconstruction_result
            
            return {
                "success": True,
                "output_srt": reconstruction_result["output_srt"],
                "quality_score": quality_result["quality_score"],
                "issues": quality_result["issues"],
                "original_count": len(subtitles),
                "translated_count": len(translated_subtitles),
                "segment_count": len(segments),
                "terminology_count": len(terminology),
                "segment_stats": analysis_result.get("segment_stats", {})
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
