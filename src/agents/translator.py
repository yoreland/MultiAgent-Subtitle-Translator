from typing import List, Dict, Any
from ..tools.llm_client import LLMClient
from ..tools.srt_utils import SRTSubtitle
from ..graph_orchestrator import AgentStatus
from ..logger import get_logger
from .video_analyzer import VideoAnalysisAgent

class TranslatorAgent:
    def __init__(self, orchestrator):
        self.name = "Translator"
        self.orchestrator = orchestrator
        self.llm_client = LLMClient()
        self.logger = get_logger(__name__)
        self.video_analyzer = VideoAnalysisAgent()
        self.video_path = None
        
    def set_video_path(self, video_path: str):
        """设置视频文件路径"""
        self.video_path = video_path
        
    def _translate_segment(self, segment: Dict[str, Any], target_lang: str, terminology: List[str]) -> List[SRTSubtitle]:
        """翻译一个完整段落，保持上下文连贯性"""
        subtitles = segment['subtitles']
        segment_chars = segment['total_chars']
        
        self.logger.info(f"开始翻译段落: {len(subtitles)}条字幕, {segment_chars}字符")
        
        # 构建完整的上下文
        context_lines = []
        for i, sub in enumerate(subtitles):
            context_lines.append(f"{i+1}. {sub.text}")
        
        context_text = '\n'.join(context_lines)
        
        self.logger.info(f"发送翻译请求，长度: {len(context_text)}字符")
        
        try:
            # 检查是否需要视频分析辅助
            visual_context = ""
            self.logger.info(f"视频路径: {self.video_path}")
            
            if self.video_path:
                needs_analysis = self._needs_visual_analysis(context_text)
                self.logger.info(f"是否需要视频分析: {needs_analysis}")
                
                if needs_analysis:
                    self.logger.info("检测到专业术语，启用视频分析...")
                    
                    # 更新状态：检测到专词
                    self.orchestrator.update_agent_status(
                        "translator", 
                        AgentStatus.RUNNING, 
                        "检测到专业术语，正在启用视频分析..."
                    )
                    
                    visual_context = self._get_visual_context(subtitles[0])
                    
                    # 更新状态：视频分析完成，继续翻译
                    self.orchestrator.update_agent_status(
                        "translator", 
                        AgentStatus.RUNNING, 
                        "视频分析完成，继续翻译..."
                    )
                else:
                    self.logger.info("未检测到需要视频分析的内容")
            else:
                self.logger.info("未提供视频文件")
            
            # 使用更简洁的翻译prompt
            prompt = f"""Translate each numbered line to {target_lang}. Return only the translations with the same numbers:

{context_text}

{visual_context}

Terminology reference: {', '.join(terminology) if terminology else 'None'}"""
            
            translated_text = self.llm_client.translate(prompt, target_lang)
            
            self.logger.info(f"收到翻译响应，长度: {len(translated_text)}字符")
            self.logger.debug(f"LLM回复内容: {repr(translated_text[:500])}...")  # 改为debug级别
            
            # 更智能的结果解析
            translated_lines = []
            lines = translated_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 跳过LLM的格式说明
                if any(skip_word in line.lower() for skip_word in ['translation', 'format', 'numbering', 'here is', 'maintaining']):
                    continue
                
                # 尝试匹配编号格式
                import re
                match = re.match(r'^\d+\.\s*(.+)', line)
                if match:
                    content = match.group(1).strip()
                    if content and not content.endswith(':'):  # 排除冒号结尾的说明
                        translated_lines.append(content)
                elif line and not re.match(r'^\d+\.$', line) and ':' not in line:  # 不是纯数字行且不包含冒号
                    translated_lines.append(line)
            
            self.logger.info(f"解析出翻译行数: {len(translated_lines)}")
            
            # 如果翻译结果数量仍然不匹配，尝试其他策略
            if len(translated_lines) != len(subtitles):
                self.logger.warning(f"翻译结果数量不匹配: 期望{len(subtitles)}, 实际{len(translated_lines)}")
                
                # 策略1: 如果翻译结果太少，补充翻译
                if len(translated_lines) < len(subtitles):
                    self.logger.info("补充缺失的翻译...")
                    for i in range(len(translated_lines), len(subtitles)):
                        individual_translation = self.llm_client.translate(subtitles[i].text, target_lang)
                        translated_lines.append(individual_translation)
                
                # 策略2: 如果翻译结果太多，截取匹配数量
                elif len(translated_lines) > len(subtitles):
                    self.logger.info(f"截取前{len(subtitles)}个翻译结果")
                    translated_lines = translated_lines[:len(subtitles)]
            
            # 创建翻译后的字幕对象
            translated_subtitles = []
            for i, subtitle in enumerate(subtitles):
                if i < len(translated_lines):
                    translated_text_line = translated_lines[i]
                else:
                    translated_text_line = subtitle.text  # 保持原文作为备选
                
                translated_subtitle = SRTSubtitle(
                    subtitle.index,
                    subtitle.start,
                    subtitle.end,
                    translated_text_line
                )
                translated_subtitles.append(translated_subtitle)
            
            self.logger.info(f"段落翻译完成: {len(translated_subtitles)}条字幕")
            return translated_subtitles
            
        except Exception as e:
            self.logger.error(f"段落翻译失败: {str(e)}")
            # 降级到逐条翻译
            return self._translate_batch(subtitles, target_lang)
    
    def _translate_batch(self, subtitles: List[SRTSubtitle], target_lang: str) -> List[SRTSubtitle]:
        """逐条翻译作为备选方案"""
        self.logger.info(f"使用逐条翻译模式: {len(subtitles)}条字幕")
        
        translated_subtitles = []
        for i, subtitle in enumerate(subtitles):
            try:
                translated_text = self.llm_client.translate(subtitle.text, target_lang)
                translated_subtitle = SRTSubtitle(
                    subtitle.index,
                    subtitle.start,
                    subtitle.end,
                    translated_text
                )
                translated_subtitles.append(translated_subtitle)
                
                if i % 10 == 0:  # 每10条记录一次进度
                    self.logger.info(f"逐条翻译进度: {i+1}/{len(subtitles)}")
                    
            except Exception as e:
                self.logger.error(f"翻译字幕{subtitle.index}失败: {str(e)}")
                # 保持原文
                translated_subtitles.append(subtitle)
        
        return translated_subtitles
        
    def process(self, segments: List[Dict[str, Any]], target_lang: str, terminology: List[str]) -> List[SRTSubtitle]:
        self.orchestrator.update_agent_status("translator", AgentStatus.RUNNING, f"开始翻译到{target_lang}...")
        self.logger.info(f"开始翻译流程: {len(segments)}个段落")
        
        try:
            all_translated_subtitles = []
            total_segments = len(segments)
            
            for i, segment in enumerate(segments):
                progress = int((i + 1) / total_segments * 100)
                segment_info = f"段落 {i+1}/{total_segments} (字幕{segment['start_index']}-{segment['end_index']}, {segment['total_chars']}字符)"
                
                self.orchestrator.update_agent_status(
                    "translator", 
                    AgentStatus.RUNNING, 
                    f"翻译{segment_info}",
                    progress
                )
                
                self.logger.info(f"开始翻译{segment_info}")
                
                # 翻译当前段落
                translated_segment = self._translate_segment(segment, target_lang, terminology)
                all_translated_subtitles.extend(translated_segment)
                
                self.logger.info(f"完成翻译{segment_info}")
                
                # 每个段落完成后立即更新状态
                self.orchestrator.update_agent_status(
                    "translator", 
                    AgentStatus.RUNNING, 
                    f"已完成{segment_info}，继续下一段落...",
                    progress
                )
            
            self.orchestrator.update_agent_status("translator", AgentStatus.COMPLETED, "翻译完成", 100)
            self.logger.info(f"翻译流程完成: 共{len(all_translated_subtitles)}条字幕")
            return all_translated_subtitles
            
        except Exception as e:
            self.logger.error(f"翻译流程失败: {str(e)}")
            self.orchestrator.update_agent_status("translator", AgentStatus.ERROR, f"翻译失败: {str(e)}")
            return []
    
    def _needs_visual_analysis(self, text: str) -> bool:
        """判断是否需要视频分析辅助"""
        # 检测专业术语、技术词汇等 - 扩展关键词
        technical_indicators = [
            '设备', '工具', '操作', '步骤', '方法', '技术', '系统', '界面', '按钮', '菜单',
            '软件', '应用', '程序', '功能', '选项', '设置', '配置', '安装', '下载', '上传',
            '文件', '文档', '数据', '信息', '内容', '格式', '类型', '版本', '更新', '升级',
            'app', 'software', 'system', 'tool', 'device', 'function', 'option', 'setting'
        ]
        
        found_indicators = [indicator for indicator in technical_indicators if indicator in text.lower()]
        self.logger.info(f"检测到的技术词汇: {found_indicators}")
        
        return len(found_indicators) > 0
    
    def _get_visual_context(self, subtitle: SRTSubtitle) -> str:
        """获取视频帧的视觉上下文"""
        if not self.video_path:
            return ""
        
        try:
            # 更新状态：开始视频分析
            self.orchestrator.update_agent_status(
                "video_analyzer", 
                AgentStatus.RUNNING, 
                f"正在提取时间戳 {subtitle.start} 的视频帧..."
            )
            
            # 提取视频帧
            frame_base64 = self.video_analyzer.extract_frame_at_timestamp(
                self.video_path, subtitle.start
            )
            
            if frame_base64:
                # 更新状态：开始分析
                self.orchestrator.update_agent_status(
                    "video_analyzer", 
                    AgentStatus.RUNNING, 
                    "正在分析视觉上下文..."
                )
                
                # 分析视觉上下文
                analysis = self.video_analyzer.analyze_visual_context(frame_base64, subtitle.text)
                
                # 更新状态：完成
                confidence = analysis.get('confidence', 0)
                scene_desc = analysis.get('scene_description', '')
                hints = analysis.get('translation_hints', '')
                
                self.orchestrator.update_agent_status(
                    "video_analyzer", 
                    AgentStatus.COMPLETED, 
                    f"分析完成: {scene_desc} (置信度: {confidence:.0%})"
                )
                
                self.logger.info(f"视频分析详情: 场景={scene_desc}, 建议={hints}, 置信度={confidence}")
                
                return f"\n视觉上下文分析: {scene_desc}. 翻译建议: {hints}"
            else:
                self.orchestrator.update_agent_status(
                    "video_analyzer", 
                    AgentStatus.ERROR, 
                    "视频帧提取失败"
                )
            
        except Exception as e:
            self.logger.error(f"视频分析失败: {e}")
            self.orchestrator.update_agent_status(
                "video_analyzer", 
                AgentStatus.ERROR, 
                f"视频分析失败: {str(e)}"
            )
        
        return ""
