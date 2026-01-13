import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

// 添加调试日志
console.log('API_BASE:', API_BASE);

interface Language {
  [key: string]: string;
}

const App: React.FC = () => {
  const [srtFile, setSrtFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [targetLanguage, setTargetLanguage] = useState<string>('English');
  const [languages, setLanguages] = useState<Language>({});
  const [translationResult, setTranslationResult] = useState<any>(null);
  const [isTranslating, setIsTranslating] = useState(false);
  const [status, setStatus] = useState<string>('');
  const [agentStates, setAgentStates] = useState<any>({});
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);

  // 获取支持的语言和建立WebSocket连接
  React.useEffect(() => {
    axios.get(`${API_BASE}/languages`)
      .then(response => setLanguages(response.data.languages))
      .catch(console.error);

    // 建立WebSocket连接
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
      console.log('WebSocket连接已建立');
      setWebsocket(ws);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'agent_status') {
          setAgentStates(data.agents);
        }
      } catch (e) {
        console.error('WebSocket消息解析失败:', e);
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket连接已关闭');
      setWebsocket(null);
    };
    
    return () => {
      ws.close();
    };
  }, []);

  // SRT文件拖拽处理
  const onSrtDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSrtFile(acceptedFiles[0]);
    }
  }, []);

  // 视频文件拖拽处理
  const onVideoDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setVideoFile(acceptedFiles[0]);
    }
  }, []);

  const srtDropzone = useDropzone({
    onDrop: onSrtDrop,
    accept: { 'text/plain': ['.srt'] },
    maxFiles: 1
  });

  const videoDropzone = useDropzone({
    onDrop: onVideoDrop,
    accept: { 'video/*': ['.mp4', '.avi', '.mov'] },
    maxFiles: 1
  });

  // 开始翻译
  const handleTranslate = async () => {
    if (!srtFile) return;

    setIsTranslating(true);
    setStatus('正在上传文件...');
    setAgentStates({}); // 重置agent状态
    setTranslationResult(null); // 重置翻译结果

    try {
      // 上传SRT文件
      const srtFormData = new FormData();
      srtFormData.append('file', srtFile);
      
      const srtResponse = await axios.post(`${API_BASE}/upload/srt`, srtFormData);
      const srtContent = srtResponse.data.content;

      let videoPath = null;
      
      // 如果有视频文件，上传视频
      if (videoFile) {
        setStatus('正在上传视频文件...');
        const videoFormData = new FormData();
        videoFormData.append('file', videoFile);
        
        const videoResponse = await axios.post(`${API_BASE}/upload/video`, videoFormData);
        videoPath = videoResponse.data.temp_path;
      }

      // 开始翻译
      setStatus('正在翻译...');
      const translateResponse = await axios.post(`${API_BASE}/translate`, {
        srt_content: srtContent,
        target_language: targetLanguage,
        video_path: videoPath
      });

      setTranslationResult(translateResponse.data.result);
      setStatus('翻译完成！');
    } catch (error: any) {
      console.error('翻译失败:', error);
      let errorMessage = '未知错误';
      
      try {
        if (error.response?.data?.detail) {
          errorMessage = String(error.response.data.detail);
        } else if (error.message) {
          errorMessage = String(error.message);
        } else {
          errorMessage = JSON.stringify(error);
        }
      } catch (e) {
        errorMessage = '错误信息解析失败';
      }
      
      setStatus(`翻译失败: ${errorMessage}`);
    } finally {
      setIsTranslating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* 标题 */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            🎬 SRT字幕翻译系统
          </h1>
          <p className="text-gray-600">基于AI的智能字幕翻译工具</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* 左侧：文件上传 */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">📁 文件上传</h2>
              
              {/* SRT文件上传 */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  SRT字幕文件 *
                </label>
                <div
                  {...srtDropzone.getRootProps()}
                  className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                    srtDropzone.isDragActive
                      ? 'border-blue-400 bg-blue-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <input {...srtDropzone.getInputProps()} />
                  {srtFile ? (
                    <div className="text-green-600">
                      ✅ {srtFile.name} ({(srtFile.size / 1024).toFixed(1)} KB)
                    </div>
                  ) : (
                    <div className="text-gray-500">
                      拖拽SRT文件到此处，或点击选择文件
                    </div>
                  )}
                </div>
              </div>

              {/* 视频文件上传 */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  视频文件 (可选)
                </label>
                <div
                  {...videoDropzone.getRootProps()}
                  className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                    videoDropzone.isDragActive
                      ? 'border-blue-400 bg-blue-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <input {...videoDropzone.getInputProps()} />
                  {videoFile ? (
                    <div className="text-green-600">
                      ✅ {videoFile.name} ({(videoFile.size / 1024 / 1024).toFixed(1)} MB)
                      <div className="text-sm text-gray-500 mt-1">
                        🎯 将用于专业术语的视觉上下文分析
                      </div>
                    </div>
                  ) : (
                    <div className="text-gray-500">
                      拖拽视频文件到此处，或点击选择文件
                      <div className="text-sm mt-1">支持 MP4, AVI, MOV 格式，最大200MB</div>
                    </div>
                  )}
                </div>
              </div>

              {/* 目标语言选择 */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  目标语言
                </label>
                <select
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {Object.entries(languages).map(([key, value]) => (
                    <option key={key} value={value}>
                      {key}
                    </option>
                  ))}
                </select>
              </div>

              {/* 翻译按钮 */}
              <button
                onClick={handleTranslate}
                disabled={!srtFile || isTranslating}
                className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
                  !srtFile || isTranslating
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {isTranslating ? '🔄 翻译中...' : '🚀 开始翻译'}
              </button>
            </div>
          </div>

          {/* 右侧：翻译结果 */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">🎯 翻译结果</h2>
            
            {status && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="text-blue-800">{status}</div>
              </div>
            )}

            {/* Agent状态显示 */}
            {Object.keys(agentStates).length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-medium mb-3">🤖 Agent工作状态</h3>
                <div className="space-y-2">
                  {Object.entries(agentStates).map(([agentName, state]: [string, any]) => (
                    <div key={agentName} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className={`w-3 h-3 rounded-full ${
                          state.status === 'RUNNING' ? 'bg-blue-500 animate-pulse' :
                          state.status === 'COMPLETED' ? 'bg-green-500' :
                          state.status === 'ERROR' ? 'bg-red-500' :
                          'bg-gray-400'
                        }`}></div>
                        <span className="font-medium">
                          {agentName === 'video_analyzer' ? '🎥 视频分析' :
                           agentName === 'translator' ? '🔤 翻译器' :
                           agentName === 'srt_parser' ? '📄 SRT解析' :
                           agentName === 'quality_controller' ? '✅ 质量检查' :
                           agentName}
                        </span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-600">{state.message}</div>
                        {state.progress !== undefined && (
                          <div className="w-24 bg-gray-200 rounded-full h-2 mt-1">
                            <div 
                              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${state.progress}%` }}
                            ></div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {translationResult && (
              <div className="space-y-4">
                {translationResult.success ? (
                  <div>
                    <div className="text-green-600 font-medium mb-2">
                      ✅ 翻译完成！
                    </div>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                        {translationResult.translated_srt}
                      </pre>
                    </div>
                    <button
                      onClick={() => {
                        const blob = new Blob([translationResult.translated_srt], { type: 'text/plain' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `translated_${srtFile?.name || 'subtitle.srt'}`;
                        a.click();
                      }}
                      className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      📥 下载翻译结果
                    </button>
                  </div>
                ) : (
                  <div className="text-red-600">
                    ❌ 翻译失败: {translationResult.error}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
