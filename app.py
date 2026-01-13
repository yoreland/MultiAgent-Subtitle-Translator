import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.orchestrator import TranslationGraph
from config import LANGUAGES
import time

def main():
    st.set_page_config(
        page_title="SRT字幕翻译系统",
        page_icon="🎬",
        layout="wide"
    )
    
    st.title("🎬 SRT字幕翻译系统")
    st.markdown("基于Graph模式的智能字幕翻译工具")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ 设置")
        target_lang = st.selectbox("目标语言", list(LANGUAGES.keys()))
        
        st.header("🤖 Agent状态")
        status_container = st.empty()
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    # Initialize session state
    if 'video_file_data' not in st.session_state:
        st.session_state.video_file_data = None
    if 'video_file_name' not in st.session_state:
        st.session_state.video_file_name = None
    
    with col1:
        st.header("📁 文件上传")
        
        # File upload
        srt_file = st.file_uploader("上传SRT字幕文件", type=['srt'])
        
        # Video file upload - remove type restriction for testing
        video_file = st.file_uploader(
            "上传视频文件 (可选)", 
            type=['mp4', 'avi', 'mov']  # 恢复类型限制
        )
        
        if srt_file:
            st.success(f"✅ SRT文件已上传: {srt_file.name}")
        
        if video_file:
            print(f"DEBUG: 检测到视频文件: {video_file.name}")
            try:
                file_size_mb = video_file.size / (1024 * 1024)
                print(f"DEBUG: 文件大小: {file_size_mb:.1f}MB")
                
                if file_size_mb > 200:
                    st.error(f"❌ 视频文件过大: {file_size_mb:.1f}MB (最大200MB)")
                elif file_size_mb > 50:
                    st.warning(f"⚠️ 大文件上传中: {video_file.name} ({file_size_mb:.1f}MB)，请耐心等待...")
                    st.success(f"✅ 视频文件已上传: {video_file.name} ({file_size_mb:.1f}MB)")
                    st.info("🎯 视频将用于专业术语的视觉上下文分析")
                else:
                    st.success(f"✅ 视频文件已上传: {video_file.name} ({file_size_mb:.1f}MB)")
                    st.info("🎯 视频将用于专业术语的视觉上下文分析")
            except Exception as e:
                print(f"DEBUG: 处理视频文件时出错: {e}")
                st.error(f"处理视频文件时出错: {e}")
        else:
            print("DEBUG: 没有检测到视频文件")
    
    with col2:
        st.header("🎯 翻译结果")
        result_container = st.container()
    
    # Translation button
    if st.button("🚀 开始翻译", type="primary", disabled=not srt_file):
        if srt_file:
            # Read SRT content
            srt_content = srt_file.read().decode('utf-8')
            
            # Initialize translation graph
            translation_graph = TranslationGraph()
            
            # Status tracking
            def update_status(agents_state):
                with status_container:
                    status_text = translation_graph.orchestrator.get_status_summary()
                    st.text_area("Agent状态", status_text, height=300, key=f"status_{time.time()}")
            
            translation_graph.set_status_callback(update_status)
            
            # Progress bar
            progress_bar = st.progress(0)
            
            try:
                # Save video file temporarily if uploaded
                video_path = None
                if video_file:
                    st.info(f"处理视频文件: {video_file.name}")
                    
                    import tempfile
                    import os
                    
                    try:
                        # Create temp file with proper extension
                        file_extension = os.path.splitext(video_file.name)[1] or '.mp4'
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                            tmp_file.write(video_file.read())
                            video_path = tmp_file.name
                        
                        st.success(f"📹 视频文件已保存到临时位置")
                        
                    except Exception as temp_error:
                        st.error(f"临时文件创建失败: {temp_error}")
                        video_path = None
                
                # Execute translation
                with st.spinner("翻译进行中..."):
                    result = translation_graph.execute_translation(
                        srt_content, 
                        LANGUAGES[target_lang],
                        video_path
                    )
                
                progress_bar.progress(100)
                
                # Display results
                with result_container:
                    if result.get("success"):
                        st.success("🎉 翻译完成!")
                        
                        # Metrics
                        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                        with col_m1:
                            st.metric("原始字幕数", result["original_count"])
                        with col_m2:
                            st.metric("翻译字幕数", result["translated_count"])
                        with col_m3:
                            st.metric("段落数", result.get("segment_count", 0))
                        with col_m4:
                            st.metric("质量分数", f"{result['quality_score']}/100")
                        
                        # Segment statistics
                        if result.get("segment_stats"):
                            stats = result["segment_stats"]
                            st.info(f"""📊 智能分段统计:
• 段落数量: {stats.get('total_segments', 0)}
• 字符范围: {stats.get('min_chars', 0)}-{stats.get('max_chars', 0)} (平均: {int(stats.get('avg_chars', 0))})
• 上下文利用率: {stats.get('utilization', 0):.1f}%
• 术语数量: {result.get('terminology_count', 0)}""")
                        
                        # Issues
                        if result.get("issues"):
                            st.warning("⚠️ 发现问题:")
                            for issue in result["issues"]:
                                st.write(f"• {issue}")
                        
                        # Download button
                        st.download_button(
                            label="📥 下载翻译后的SRT文件",
                            data=result["output_srt"],
                            file_name=f"translated_{srt_file.name}",
                            mime="text/plain"
                        )
                        
                        # Preview
                        with st.expander("📖 预览翻译结果"):
                            st.text_area("翻译后的SRT内容", result["output_srt"], height=300)
                    else:
                        st.error(f"❌ 翻译失败: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                st.error(f"❌ 翻译失败: {str(e)}")

if __name__ == "__main__":
    main()
