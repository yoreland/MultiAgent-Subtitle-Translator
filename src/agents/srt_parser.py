from typing import List, Dict, Any
from ..tools.srt_utils import SRTSubtitle, parse_srt
from ..tools.llm_client import LLMClient
from ..graph_orchestrator import AgentStatus

class SRTParserAgent:
    def __init__(self, orchestrator):
        self.name = "SRT Parser"
        self.orchestrator = orchestrator
        
        # LLM上下文配置 - 基于实际API限制调整
        self.max_context_tokens = 32000  # 降低到32k，避免504超时
        self.chars_per_token = 4  
        self.system_prompt_overhead = 1000  
        self.max_input_chars = int(self.max_context_tokens * self.chars_per_token * 0.6) - self.system_prompt_overhead  # 降低到60%
        self.max_subtitles_per_batch = 50  # 每批最多50条字幕
        
    def _calculate_optimal_segments(self, subtitles: List[SRTSubtitle]) -> List[Dict[str, Any]]:
        """基于LLM上下文限制计算最优分段"""
        total_chars = sum(len(sub.text) for sub in subtitles)
        
        # 计算最少需要分几段
        min_segments = max(1, (total_chars + self.max_input_chars - 1) // self.max_input_chars)
        
        self.orchestrator.update_agent_status(
            "parser", 
            AgentStatus.RUNNING, 
            f"总字符数: {total_chars}, 最大单次: {self.max_input_chars}, 最少分段: {min_segments}",
            20
        )
        
        segments = []
        current_segment = []
        current_chars = 0
        
        for i, subtitle in enumerate(subtitles):
            subtitle_chars = len(subtitle.text)
            
            # 检查是否需要开始新段落
            should_start_new = False
            
            # 1. 字符数限制检查
            if current_chars + subtitle_chars > self.max_input_chars and current_segment:
                should_start_new = True
            
            # 2. 字幕数量限制检查 - 防止504超时
            elif len(current_segment) >= self.max_subtitles_per_batch:
                should_start_new = True
            
            # 3. 自然分段点检查（在限制范围内寻找合适的分段点）
            elif current_chars > self.max_input_chars * 0.8 or len(current_segment) > self.max_subtitles_per_batch * 0.8:
                # 检查是否是句子结束
                if subtitle.text.strip().endswith(('.', '!', '?', '。', '！', '？')):
                    should_start_new = True
                # 检查时间间隔
                elif i < len(subtitles) - 1:
                    current_end = self._time_to_seconds(subtitle.end)
                    next_start = self._time_to_seconds(subtitles[i + 1].start)
                    if next_start - current_end > 2.0:  # 2秒间隔
                        should_start_new = True
            
            if should_start_new and current_segment:
                # 保存当前段落
                segments.append({
                    'subtitles': current_segment.copy(),
                    'start_index': current_segment[0].index,
                    'end_index': current_segment[-1].index,
                    'total_chars': current_chars,
                    'duration': self._time_to_seconds(current_segment[-1].end) - self._time_to_seconds(current_segment[0].start)
                })
                current_segment = []
                current_chars = 0
            
            # 添加当前字幕到段落
            current_segment.append(subtitle)
            current_chars += subtitle_chars
        
        # 添加最后一个段落
        if current_segment:
            segments.append({
                'subtitles': current_segment.copy(),
                'start_index': current_segment[0].index,
                'end_index': current_segment[-1].index,
                'total_chars': current_chars,
                'duration': self._time_to_seconds(current_segment[-1].end) - self._time_to_seconds(current_segment[0].start)
            })
        
        return segments
    
    def _analyze_segment_distribution(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析段落分布情况"""
        if not segments:
            return {}
        
        char_counts = [seg['total_chars'] for seg in segments]
        
        return {
            'total_segments': len(segments),
            'min_chars': min(char_counts),
            'max_chars': max(char_counts),
            'avg_chars': sum(char_counts) / len(char_counts),
            'utilization': sum(char_counts) / (len(segments) * self.max_input_chars) * 100
        }
    
    def _time_to_seconds(self, time_str: str) -> float:
        """将SRT时间格式转换为秒数"""
        try:
            time_part, ms_part = time_str.split(',')
            h, m, s = map(int, time_part.split(':'))
            ms = int(ms_part)
            return h * 3600 + m * 60 + s + ms / 1000.0
        except:
            return 0.0
    
    def _extract_terminology(self, subtitles: List[SRTSubtitle]) -> List[str]:
        """提取专业术语"""
        all_text = ' '.join([sub.text for sub in subtitles])
        
        import re
        
        # 检测专有名词和技术术语
        proper_nouns = re.findall(r'\b[A-Z][a-zA-Z]+\b', all_text)
        tech_terms = re.findall(r'\b(?:AI|API|ML|GPU|CPU|SDK|HTTP|JSON|XML|SQL|AWS|API|LLM|NLP|OCR)\b', all_text, re.IGNORECASE)
        
        # 去重并按频率排序
        all_terms = proper_nouns + tech_terms
        term_freq = {}
        for term in all_terms:
            term_freq[term] = term_freq.get(term, 0) + 1
        
        # 返回频率最高的术语
        sorted_terms = sorted(term_freq.items(), key=lambda x: x[1], reverse=True)
        return [term for term, freq in sorted_terms[:15]]  # 限制15个最重要的术语
        
    def process(self, srt_content: str) -> Dict[str, Any]:
        self.orchestrator.update_agent_status("parser", AgentStatus.RUNNING, "解析SRT文件...")
        
        try:
            # 解析字幕
            subtitles = parse_srt(srt_content)
            self.orchestrator.update_agent_status("parser", AgentStatus.RUNNING, "计算最优分段策略...", 30)
            
            # 计算最优分段
            segments = self._calculate_optimal_segments(subtitles)
            self.orchestrator.update_agent_status("parser", AgentStatus.RUNNING, "分析段落分布...", 60)
            
            # 分析段落分布
            segment_stats = self._analyze_segment_distribution(segments)
            self.orchestrator.update_agent_status("parser", AgentStatus.RUNNING, "提取专业术语...", 80)
            
            # 提取专业术语
            terminology = self._extract_terminology(subtitles)
            
            self.orchestrator.update_agent_status(
                "parser", 
                AgentStatus.COMPLETED, 
                f"智能分批完成: {len(subtitles)}条字幕→{len(segments)}批次 (每批≤{self.max_subtitles_per_batch}条)",
                100
            )
            
            return {
                "subtitles": subtitles,
                "segments": segments,
                "terminology": terminology,
                "total_count": len(subtitles),
                "segment_count": len(segments),
                "segment_stats": segment_stats,
                "context_config": {
                    "max_context_tokens": self.max_context_tokens,
                    "max_input_chars": self.max_input_chars,
                    "chars_per_token": self.chars_per_token
                },
                "success": True
            }
        except Exception as e:
            self.orchestrator.update_agent_status("parser", AgentStatus.ERROR, f"解析失败: {str(e)}")
            return {"success": False, "error": str(e)}
