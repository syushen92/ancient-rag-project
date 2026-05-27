import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import './index.css'

const DEFAULT_MESSAGE = {
  role: 'bot',
  content: '你好！我是古人辨識助理。請上傳一張古人的畫像或照片，我會為您辨識並介紹他。',
}

function App() {
  // Chat Sessions State
  const [sessions, setSessions] = useState(() => {
    const saved = localStorage.getItem('chatSessions')
    if (saved) return JSON.parse(saved)
    return [{
      id: Date.now(),
      title: '新的辨識對話',
      messages: [DEFAULT_MESSAGE]
    }]
  })
  
  const [currentSessionId, setCurrentSessionId] = useState(sessions[0]?.id || Date.now())

  const [input, setInput] = useState('')
  const [selectedImage, setSelectedImage] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const fileInputRef = useRef(null)
  const messagesEndRef = useRef(null)

  // Get current session messages
  const currentSession = sessions.find(s => s.id === currentSessionId) || sessions[0]
  const messages = currentSession?.messages || []

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  // Save sessions to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('chatSessions', JSON.stringify(sessions))
  }, [sessions])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const createNewChat = () => {
    const newSession = {
      id: Date.now(),
      title: '新的辨識對話',
      messages: [DEFAULT_MESSAGE]
    }
    setSessions(prev => [newSession, ...prev])
    setCurrentSessionId(newSession.id)
  }

  const deleteChat = (e, id) => {
    e.stopPropagation()
    const newSessions = sessions.filter(s => s.id !== id)
    if (newSessions.length === 0) {
      // Create a default if all are deleted
      const defaultSession = {
        id: Date.now(),
        title: '新的辨識對話',
        messages: [DEFAULT_MESSAGE]
      }
      setSessions([defaultSession])
      setCurrentSessionId(defaultSession.id)
    } else {
      setSessions(newSessions)
      if (id === currentSessionId) {
        setCurrentSessionId(newSessions[0].id)
      }
    }
  }

  // Helper to update the current session's messages and auto-generate title
  const updateCurrentSession = (newMessages) => {
    setSessions(prevSessions => prevSessions.map(session => {
      if (session.id === currentSessionId) {
        let title = session.title
        // Auto-generate title if it's the default and we have a user message
        if (title === '新的辨識對話' && newMessages.length > 1) {
          const userMsg = newMessages.find(m => m.role === 'user')
          if (userMsg?.content) {
            title = userMsg.content.substring(0, 15)
          } else if (userMsg?.imageUrl) {
            title = '圖片辨識查詢'
          }
        }
        return { ...session, title, messages: newMessages }
      }
      return session
    }))
  }

  const handleImageSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedImage(file)
      setPreviewUrl(URL.createObjectURL(file))
    }
  }

  const removeImage = () => {
    setSelectedImage(null)
    setPreviewUrl(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleSend = async () => {
    if (!selectedImage && !input.trim()) return

    const userMessage = {
      role: 'user',
      content: input,
      imageUrl: previewUrl
    }

    const updatedMessages = [...messages, userMessage]
    updateCurrentSession(updatedMessages)
    setIsLoading(true)
    setInput('')
    
    const fileToSend = selectedImage
    setSelectedImage(null)
    setPreviewUrl(null)

    try {
      const formData = new FormData()
      if (fileToSend) {
        formData.append('image', fileToSend)
      } else {
        throw new Error("目前系統需上傳圖片才能進行辨識")
      }

      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        body: formData
      })
      
      const data = await response.json()
      
      if (data.error) {
        throw new Error(data.error)
      }
      
      updateCurrentSession([...updatedMessages, {
        role: 'bot',
        content: data.response
      }])
    } catch (error) {
      updateCurrentSession([...updatedMessages, {
        role: 'bot',
        content: `發生錯誤: ${error.message}`
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="app-container">
      {/* Sidebar */}
      <div className="sidebar">
        <button className="new-chat-btn" onClick={createNewChat}>
          <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" strokeLinecap="round" strokeLinejoin="round" height="16" width="16" xmlns="http://www.w3.org/2000/svg"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          New Chat
        </button>
        
        <div className="history-list">
          {sessions.map(session => (
            <div 
              key={session.id} 
              className={`history-item ${session.id === currentSessionId ? 'active' : ''}`}
              onClick={() => setCurrentSessionId(session.id)}
            >
              <div className="history-item-title">{session.title}</div>
              <button className="delete-chat-btn" onClick={(e) => deleteChat(e, session.id)} title="刪除">×</button>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="chat-area">
        <div className="messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message-wrapper ${msg.role}`}>
              <div className="message-content">
                <div className={`avatar ${msg.role}`}>
                  {msg.role === 'user' ? 'U' : 'AI'}
                </div>
                <div className="message-text">
                  {msg.imageUrl && (
                    <img src={msg.imageUrl} alt="Uploaded" className="chat-image-preview" />
                  )}
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="message-wrapper bot">
              <div className="message-content">
                <div className="avatar bot">AI</div>
                <div className="message-text">
                  <div className="typing-indicator">
                    <div className="dot"></div>
                    <div className="dot"></div>
                    <div className="dot"></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="input-container">
          <div className="input-box">
            
            {previewUrl && (
              <div className="upload-preview-overlay">
                <img src={previewUrl} alt="Preview" />
                <button className="remove-image-btn" onClick={removeImage}>移除圖片</button>
              </div>
            )}
            
            <input 
              type="file" 
              accept="image/*" 
              style={{display: 'none'}} 
              ref={fileInputRef}
              onChange={handleImageSelect}
            />
            
            <button className="image-upload-btn" onClick={() => fileInputRef.current.click()} title="上傳圖片">
              <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" strokeLinecap="round" strokeLinejoin="round" height="20" width="20" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
            </button>
            
            <input 
              type="text" 
              placeholder="傳送訊息給 AI 助理... (請記得先上傳圖片)" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              disabled={isLoading}
            />
            
            <button 
              className="send-btn" 
              onClick={handleSend}
              disabled={isLoading || (!input.trim() && !selectedImage)}
            >
              <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" strokeLinecap="round" strokeLinejoin="round" height="20" width="20" xmlns="http://www.w3.org/2000/svg"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
