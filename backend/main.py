from fastapi import FastAPI, File, UploadFile, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sys
import os
import tempfile
import asyncio
from typing import List, Optional
import json

from src.orchestrator import TranslationGraph
from config import LANGUAGES

app = FastAPI(title="SRT Translation API", version="2.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # React开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量存储WebSocket连接
websocket_connections: List[WebSocket] = []

class TranslationManager:
    def __init__(self):
        self.current_task = None
        self.translation_graph = None
    
    async def broadcast_status(self, status_data):
        """广播状态更新到所有WebSocket连接"""
        if websocket_connections:
            try:
                # 转换AgentState对象为可序列化的字典
                serializable_data = {}
                if 'agents' in status_data:
                    serializable_data = {
                        "type": status_data.get("type", "agent_status"),
                        "agents": {}
                    }
                    for agent_name, agent_state in status_data['agents'].items():
                        serializable_data["agents"][agent_name] = {
                            "status": agent_state.status.name if hasattr(agent_state.status, 'name') else str(agent_state.status),
                            "message": agent_state.message,
                            "progress": getattr(agent_state, 'progress', None)
                        }
                else:
                    serializable_data = status_data
                
                message = json.dumps(serializable_data)
                for websocket in websocket_connections[:]:  # 复制列表避免修改时出错
                    try:
                        await websocket.send_text(message)
                    except:
                        websocket_connections.remove(websocket)
            except Exception as e:
                print(f"Broadcast error: {e}")

translation_manager = TranslationManager()

@app.get("/")
async def root():
    return {"message": "SRT Translation API", "version": "2.0.0"}

@app.get("/languages")
async def get_languages():
    """获取支持的语言列表"""
    return {"languages": LANGUAGES}

@app.post("/upload/srt")
async def upload_srt(file: UploadFile = File(...)):
    """上传SRT文件"""
    if not file.filename.endswith('.srt'):
        raise HTTPException(status_code=400, detail="只支持SRT文件")
    
    content = await file.read()
    try:
        srt_content = content.decode('utf-8')
        return {
            "success": True,
            "filename": file.filename,
            "size": len(content),
            "content": srt_content
        }
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="SRT文件编码错误")

@app.post("/upload/video")
async def upload_video(file: UploadFile = File(...)):
    """上传视频文件"""
    allowed_types = ['video/mp4', 'video/avi', 'video/mov']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="不支持的视频格式")
    
    # 检查文件大小 (200MB限制)
    content = await file.read()
    if len(content) > 200 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="视频文件过大，最大200MB")
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
        tmp_file.write(content)
        temp_path = tmp_file.name
    
    return {
        "success": True,
        "filename": file.filename,
        "size": len(content),
        "temp_path": temp_path
    }

from pydantic import BaseModel

class TranslationRequest(BaseModel):
    srt_content: str
    target_language: str
    video_path: Optional[str] = None

@app.post("/translate")
async def start_translation(request: TranslationRequest):
    """开始翻译任务"""
    if request.target_language not in LANGUAGES.values():
        raise HTTPException(status_code=400, detail="不支持的目标语言")
    
    # 创建翻译图
    translation_graph = TranslationGraph()
    
    # 设置状态回调
    def status_callback(agents_state):
        status_data = {
            "type": "agent_status",
            "agents": agents_state
        }
        asyncio.create_task(translation_manager.broadcast_status(status_data))
    
    translation_graph.set_status_callback(status_callback)
    
    try:
        # 执行翻译
        result = translation_graph.execute_translation(
            request.srt_content, 
            request.target_language,
            request.video_path
        )
        
        return {
            "success": True,
            "result": {
                "success": result.get("success", False),
                "translated_srt": result.get("output_srt", ""),
                "quality_score": result.get("quality_score", 0),
                "original_count": result.get("original_count", 0),
                "translated_count": result.get("translated_count", 0),
                "issues": result.get("issues", [])
            }
        }
    except Exception as e:
        import traceback
        error_detail = f"翻译失败: {str(e)}"
        print(f"Translation error: {error_detail}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接处理实时状态更新"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # 保持连接活跃
            await websocket.receive_text()
    except:
        pass
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
