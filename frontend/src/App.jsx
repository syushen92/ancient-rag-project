import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import './index.css'

const DEFAULT_SESSION = {
  id: Date.now(),
  title: '新的辨識對話',
  image: null,        // Base64 string of portrait
  filename: '',       // Image filename
  status: 'ready',    // 'ready', 'busy', 'error'
  statusLabel: '等待上傳',
  response: '',       // Raw Markdown string response from backend
  error: ''
}

// Convert base64 Data URL to Blob for HTTP uploads
async function base64ToBlob(base64DataUrl) {
  const res = await fetch(base64DataUrl);
  return await res.blob();
}

function App() {
  // Chat Sessions State
  const [sessions, setSessions] = useState(() => {
    const saved = localStorage.getItem('ancientRAGSessions');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error("Failed to load saved sessions, resetting.", e);
      }
    }
    return [DEFAULT_SESSION];
  });

  const [currentSessionId, setCurrentSessionId] = useState(() => {
    return sessions[0]?.id || Date.now();
  });

  const [selectedImageFile, setSelectedImageFile] = useState(null);
  const fileInputRef = useRef(null);

  // Get current active session
  const activeSession = sessions.find(s => s.id === currentSessionId) || sessions[0] || DEFAULT_SESSION;

  // Save sessions to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('ancientRAGSessions', JSON.stringify(sessions));
  }, [sessions]);

  // Update a key in the current active session
  const updateCurrentSession = (updates) => {
    setSessions(prevSessions => prevSessions.map(session => {
      if (session.id === currentSessionId) {
        const merged = { ...session, ...updates };
        // Auto-generate a beautiful title if it's currently the default
        if (merged.title === '新的辨識對話' && merged.filename) {
          const baseName = merged.filename.substring(0, merged.filename.lastIndexOf('.')) || merged.filename;
          merged.title = baseName.substring(0, 14) + (baseName.length > 14 ? '...' : '');
        }
        return merged;
      }
      return session;
    }));
  };

  const createNewChat = () => {
    const newSession = {
      id: Date.now(),
      title: '新的辨識對話',
      image: null,
      filename: '',
      status: 'ready',
      statusLabel: '等待上傳',
      response: '',
      error: ''
    };
    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
    setSelectedImageFile(null);
  };

  const deleteChat = (e, id) => {
    e.stopPropagation();
    const newSessions = sessions.filter(s => s.id !== id);
    if (newSessions.length === 0) {
      const defaultS = {
        ...DEFAULT_SESSION,
        id: Date.now()
      };
      setSessions([defaultS]);
      setCurrentSessionId(defaultS.id);
    } else {
      setSessions(newSessions);
      if (id === currentSessionId) {
        setCurrentSessionId(newSessions[0].id);
      }
    }
    setSelectedImageFile(null);
  };

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      loadFile(file);
    }
  };

  const loadFile = (file) => {
    if (!file.type.startsWith('image/')) {
      updateCurrentSession({
        error: '請上傳合法的圖片檔案。',
        status: 'error',
        statusLabel: '發生錯誤'
      });
      return;
    }

    setSelectedImageFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      updateCurrentSession({
        image: e.target.result,
        filename: file.name,
        error: '',
        response: '',
        status: 'ready',
        statusLabel: '畫像已載入'
      });
    };
    reader.readAsDataURL(file);
  };

  const removeImage = () => {
    setSelectedImageFile(null);
    updateCurrentSession({
      image: null,
      filename: '',
      error: '',
      response: '',
      status: 'ready',
      statusLabel: '等待上傳'
    });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleIdentify = async () => {
    if (!activeSession.image) return;

    updateCurrentSession({
      status: 'busy',
      statusLabel: '檢索比對中...',
      error: '',
      response: ''
    });

    try {
      let fileToSend = selectedImageFile;
      if (!fileToSend) {
        // Reconstruct File from base64 if it has been reloaded from localStorage
        const blob = await base64ToBlob(activeSession.image);
        fileToSend = new File([blob], activeSession.filename || 'portrait.jpg', { type: blob.type });
      }

      const formData = new FormData();
      formData.append('image', fileToSend);

      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      updateCurrentSession({
        response: data.response,
        status: 'ready',
        statusLabel: '比對完成'
      });
    } catch (error) {
      updateCurrentSession({
        error: `比對失敗: ${error.message}`,
        status: 'error',
        statusLabel: '發生錯誤'
      });
    }
  };

  // Drag and Drop Events
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.add('over');
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('over');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('over');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      loadFile(e.dataTransfer.files[0]);
    }
  };

  // Parser helper to break down the backend combined response
  const parseResponse = (content) => {
    if (!content) return null;

    const parts = content.split(/={3,}/);
    const systemSection = parts[0] || '';
    const aiAnalysis = parts[1] || '';

    let imgMatch = { status: 'none', label: '未進行比對', score: 0, detail: '' };
    let txtMatch = { status: 'none', label: '未進行比對', score: 0, detail: '' };
    let initialDesc = '';

    // Parse Image Match status from system log
    if (systemSection.includes('圖片群體比對過關')) {
      const match = systemSection.match(/圖片群體比對過關:\s*([^\n(]+)(?:\(平均距離:\s*([0-9.]+)\))?/);
      const label = match ? match[1].trim() : '比對成功';
      const dist = match && match[2] ? parseFloat(match[2]) : 0.05; // default fallback if parse missing
      const score = Math.max(0, Math.min(100, Math.round((1 - dist) * 100)));
      imgMatch = {
        status: 'pass',
        label,
        score,
        detail: `距離: ${dist.toFixed(4)}`
      };
    } else if (systemSection.includes('圖片比對未達標') || systemSection.includes('❌ 圖片')) {
      imgMatch = {
        status: 'fail',
        label: '未達標',
        score: 0,
        detail: '特徵距離過大'
      };
    }

    // Parse Text/Document Match status
    if (systemSection.includes('文獻群體比對過關')) {
      const match = systemSection.match(/文獻群體比對過關:\s*([^\n(]+)(?:\(平均距離:\s*([0-9.]+)\))?/);
      const label = match ? match[1].trim() : '比對成功';
      const dist = match && match[2] ? parseFloat(match[2]) : 0.1;
      const score = Math.max(0, Math.min(100, Math.round((1 - dist) * 100)));
      txtMatch = {
        status: 'pass',
        label,
        score,
        detail: `距離: ${dist.toFixed(4)}`
      };
    } else if (systemSection.includes('文獻比對未達標') || systemSection.includes('❌ 文獻')) {
      txtMatch = {
        status: 'fail',
        label: '未達標',
        score: 0,
        detail: '文意距離過大'
      };
    }

    // Extract Initial Visual Description from Gemini Vision (Stage 1)
    const descIndex = systemSection.indexOf('【Gemini 初始特徵描述】');
    if (descIndex !== -1) {
      initialDesc = systemSection.substring(descIndex + '【Gemini 初始特徵描述】'.length).trim();
    }

    return {
      imgMatch,
      txtMatch,
      initialDesc,
      aiAnalysis: aiAnalysis.trim()
    };
  };

  const parsedResults = parseResponse(activeSession.response);

  return (
    <div className="app-container">
      {/* ── Sidebar ── */}
      <div className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">
            <svg viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <span className="brand-name">歷史人物畫像辨識</span>
        </div>

        <button className="new-chat-btn" onClick={createNewChat}>
          <svg viewBox="0 0 24 24">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          新任務
        </button>

        <div className="history-list">
          {sessions.map(session => (
            <div
              key={session.id}
              className={`history-item ${session.id === currentSessionId ? 'active' : ''}`}
              onClick={() => {
                setCurrentSessionId(session.id);
                setSelectedImageFile(null);
              }}
            >
              <div className="history-item-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
              </div>
              <div className="history-item-title">{session.title}</div>
              <button
                className="delete-chat-btn"
                onClick={(e) => deleteChat(e, session.id)}
                title="刪除"
              >
                &times;
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Main Dashboard Area ── */}
      <div className="main-area">
        <div className="page">

          {/* Header */}
          <div className="hd">
            <div className="hd-left">
              <h1 className="hd-title">歷史人物畫像辨識</h1>
              <p className="hd-desc">上傳歷史人物畫像，取得向量資料庫比對相似度與模型之考證分析</p>
            </div>

            <div className="hd-status" data-s={activeSession.status}>
              <div className="hd-status-dot"></div>
              <span>{activeSession.statusLabel}</span>
            </div>
          </div>

          {/* Grid Panel (3 Columns) */}
          <div className="grid">

            {/* Column 1: Upload / Preview */}
            <div className="card upload-card">
              <div className="card-hd">
                <div className="card-title">
                  <div className="card-title-icon">
                    <svg viewBox="0 0 24 24">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                  </div>
                  畫像上傳與預覽
                </div>
                {activeSession.status === 'busy' && (
                  <div className="card-badge on">
                    <div className="spin"></div>
                    &nbsp;辨識中
                  </div>
                )}
              </div>

              {/* Upload Drop Zone */}
              {!activeSession.image && (
                <div className="dz-wrap">
                  <div
                    className="dz"
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                  >
                    <input
                      type="file"
                      id="file-input"
                      accept="image/*"
                      ref={fileInputRef}
                      onChange={handleImageSelect}
                      aria-label="選擇歷史人物畫像"
                    />
                    <div className="dz-content">
                      <div className="dz-circle">
                        <svg viewBox="0 0 24 24">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                          <polyline points="17 8 12 3 7 8" />
                          <line x1="12" y1="3" x2="12" y2="15" />
                        </svg>
                      </div>
                      <p className="dz-primary">拖曳或點擊上傳畫像</p>
                      <p className="dz-secondary">支援 JPG, PNG, WEBP, BMP 格式</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Selected Image Preview Container */}
              {activeSession.image && (
                <div className="preview-wrap on fi">
                  <div className="preview-img-box">
                    <img id="preview-img" src={activeSession.image} alt="預覽影像" />
                  </div>

                  {activeSession.error && (
                    <div id="error-msg" className="on" role="alert">
                      <span>{activeSession.error}</span>
                    </div>
                  )}

                  <div className="preview-footer">
                    <div className="pf-name">
                      檔案名稱：<strong>{activeSession.filename || '未命名畫像'}</strong>
                    </div>
                    <div className="pf-actions">
                      <button
                        className="btn btn-soft"
                        onClick={removeImage}
                        disabled={activeSession.status === 'busy'}
                      >
                        <svg viewBox="0 0 24 24">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          <line x1="10" y1="11" x2="10" y2="17" />
                          <line x1="14" y1="11" x2="14" y2="17" />
                        </svg>
                        重新選擇
                      </button>
                      <button
                        className="btn btn-green"
                        onClick={handleIdentify}
                        disabled={activeSession.status === 'busy'}
                      >
                        <svg viewBox="0 0 24 24">
                          <circle cx="11" cy="11" r="8" />
                          <line x1="21" y1="21" x2="16.65" y2="16.65" />
                        </svg>
                        開始辨識
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Column 2: Database Match & Visual Features */}
            <div className="card res-card">
              <div className="card-hd">
                <div className="card-title">
                  <div className="card-title-icon">
                    <svg viewBox="0 0 24 24">
                      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                    </svg>
                  </div>
                  系統多模態檢索比對
                </div>
              </div>

              <div className="res-card-body">
                {/* Empty State when no response exists */}
                {!parsedResults && activeSession.status !== 'busy' && (
                  <div className="col-empty">
                    <div className="col-empty-icon">
                      <svg viewBox="0 0 24 24">
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                      </svg>
                    </div>
                    <p>上傳歷史人物畫像並開始辨識<br />即可在此查看向量庫比對結果</p>
                  </div>
                )}

                {/* Loading State during inference */}
                {activeSession.status === 'busy' && (
                  <div className="col-empty">
                    <div className="spin" style={{ width: '24px', height: '24px', borderWidth: '3px' }}></div>
                    <p style={{ marginTop: '12px' }}>檢索向量資料庫中...<br />進行圖片與文獻比對...</p>
                  </div>
                )}

                {/* Parsed Match Metrics & Descriptions */}
                {parsedResults && (
                  <div className="fi" style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                    {/* Database Verdicts */}
                    <div className="verdict-box">
                      <div className="verdict-header">資料庫雙軌比對數據</div>

                      <div className="verdict-row">
                        {/* 1. Image Search Match */}
                        <div className="match-item">
                          <div className="v-tag-row">
                            <span className="v-name">圖片特徵比對</span>
                            <span className={`v-tag ${parsedResults.imgMatch.status === 'pass' ? 'ok' : 'diseased'}`}>
                              <span className="v-tag-dot"></span>
                              {parsedResults.imgMatch.status === 'pass' ? '比對通過' : '未達標'}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--n-800)' }}>
                            候選人物：{parsedResults.imgMatch.label}
                          </div>
                          <div className="v-bar-wrap">
                            <div className="v-bar">
                              <div
                                className="v-bar-fill"
                                style={{
                                  width: `${parsedResults.imgMatch.score}%`,
                                  background: parsedResults.imgMatch.status === 'pass' ? 'linear-gradient(90deg, var(--p-400), var(--p-600))' : 'var(--n-300)'
                                }}
                              ></div>
                            </div>
                            <span className="v-pct">{parsedResults.imgMatch.score}%</span>
                          </div>
                          <div style={{ fontSize: '0.69rem', color: 'var(--n-400)' }}>
                            {parsedResults.imgMatch.detail}
                          </div>
                        </div>

                        {/* 2. Text Semantic Match */}
                        <div className="match-item">
                          <div className="v-tag-row">
                            <span className="v-name">文獻語意比對</span>
                            <span className={`v-tag ${parsedResults.txtMatch.status === 'pass' ? 'ok' : 'diseased'}`}>
                              <span className="v-tag-dot"></span>
                              {parsedResults.txtMatch.status === 'pass' ? '比對通過' : '未達標'}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--n-800)' }}>
                            候選人物：{parsedResults.txtMatch.label}
                          </div>
                          <div className="v-bar-wrap">
                            <div className="v-bar">
                              <div
                                className="v-bar-fill"
                                style={{
                                  width: `${parsedResults.txtMatch.score}%`,
                                  background: parsedResults.txtMatch.status === 'pass' ? 'linear-gradient(90deg, var(--p-400), var(--p-600))' : 'var(--n-300)'
                                }}
                              ></div>
                            </div>
                            <span className="v-pct">{parsedResults.txtMatch.score}%</span>
                          </div>
                          <div style={{ fontSize: '0.69rem', color: 'var(--n-400)' }}>
                            {parsedResults.txtMatch.detail}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Stage 1 Gemini Description */}
                    <div className="initial-desc-box">
                      <div className="initial-desc-title">
                        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ marginRight: '3px' }}>
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                        Gemini 初始畫像特徵描寫
                      </div>
                      <div className="scroll-text-wrap">
                        {parsedResults.initialDesc || '未取得視覺描述特徵。'}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Column 3: Historian AI Analysis */}
            <div className="card advice-col">
              <div className="card-hd">
                <div className="card-title">
                  <div className="card-title-icon">
                    <svg viewBox="0 0 24 24">
                      <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" />
                      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                      <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                  </div>
                  歷史學者模型分析
                </div>
              </div>

              <div className="advice-body-wrap">
                {/* Empty State when no response */}
                {!parsedResults && activeSession.status !== 'busy' && (
                  <div className="col-empty">
                    <div className="col-empty-icon">
                      <svg viewBox="0 0 24 24">
                        <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                      </svg>
                    </div>
                    <p>比對完成後<br />將在此呈現模型的分析與生平描述</p>
                  </div>
                )}

                {/* Loading State during inference */}
                {activeSession.status === 'busy' && (
                  <div className="col-empty">
                    <div className="spin" style={{ width: '24px', height: '24px', borderWidth: '3px' }}></div>
                    <p style={{ marginTop: '12px' }}>檢索此歷史人物中...<br />考究該人物生平...</p>
                  </div>
                )}

                {/* Scholar Analysis in Markdown */}
                {parsedResults && (
                  <>
                    <div id="advice-body" className="fi">
                      <ReactMarkdown>{parsedResults.aiAnalysis}</ReactMarkdown>
                    </div>
                    <div className="advice-note">
                      此內容由 AI 整合多模態 RAG 知識庫比對產生，史實仍建議參考專業學術著作與文獻。
                    </div>
                  </>
                )}
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  )
}

export default App
