import { useState, useRef, useEffect } from 'react'
import ChatMessage from './components/ChatMessage'
import MessageInput from './components/MessageInput'
import ConversationList from './components/ConversationList'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

// 调试：确认API_URL配置
console.log('前端API_URL配置:', API_URL)

// 检查API_URL是否指向本地后端（对话历史管理必须在本地后端）
const isLocalBackend = API_URL.includes('localhost') || 
                       API_URL.includes('127.0.0.1') || 
                       API_URL.startsWith('http://localhost') ||
                       API_URL.startsWith('http://127.0.0.1')
const isCloudServer = API_URL.includes('129.211.164.244') || (!isLocalBackend && API_URL !== 'http://localhost:8000')

if (isCloudServer) {
  console.error('错误: 前端API_URL未指向本地后端！')
  console.error('当前配置:', API_URL)
}

// 生成对话标题（基于首条消息）
const generateTitle = (messages) => {
  if (messages.length === 0) return '新对话'
  const firstUserMessage = messages.find(msg => msg.role === 'user')
  if (firstUserMessage) {
    const content = firstUserMessage.content
    return content.length > 20 ? content.substring(0, 20) + '...' : content
  }
  return '新对话'
}

// 格式化日期
const formatDate = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function App() {
  const [conversations, setConversations] = useState([])
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  // 从 localStorage 加载对话列表
  useEffect(() => {
    const saved = localStorage.getItem('conversations')
    if (saved) {
      const parsed = JSON.parse(saved)
      setConversations(parsed)
      if (parsed.length > 0 && !currentConversationId) {
        // 自动加载最近的对话
        setCurrentConversationId(parsed[0].id)
        setMessages(parsed[0].messages)
      }
    }
  }, [])

  // 同步对话到后端
  const syncConversationToBackend = async (conversation) => {
    // 如果API_URL未指向本地后端，跳过同步（对话历史管理必须在本地后端）
    if (!isLocalBackend) {
      console.warn(`跳过同步：API_URL (${API_URL}) 未指向本地后端，对话历史仅保存在localStorage`)
      return
    }
    
    try {
      const syncUrl = `${API_URL}/conversation/${conversation.id}`
      console.log(`同步对话到后端: ${conversation.id}`, {
        messageCount: conversation.messages?.length || 0,
        title: conversation.title,
        url: syncUrl  // 显示实际请求的URL
      })
      await axios.put(syncUrl, {
        messages: conversation.messages || [],
        title: conversation.title,
        updatedAt: conversation.updatedAt
      })
      console.log(`对话 ${conversation.id} 同步成功`)
    } catch (error) {
      console.error(`同步对话 ${conversation.id} 失败:`, error)
      if (error.response) {
        console.error('错误详情:', {
          status: error.response.status,
          data: error.response.data,
          url: error.config?.url
        })
        if (error.response.status === 404) {
          console.error('404错误：PUT端点不存在！')
        }
      }
      // 静默失败
    }
  }

  // 保存对话列表到 localStorage 并同步到后端
  const saveConversations = async (updated) => {
    // 先保存到 localStorage
    localStorage.setItem('conversations', JSON.stringify(updated))
    setConversations(updated)
    
    // 异步同步到后端（不阻塞UI，但记录日志）
    console.log(`准备同步 ${updated.length} 个对话到后端`)
    Promise.all(updated.map(conv => syncConversationToBackend(conv)))
      .then(() => {
        console.log(`所有对话同步完成`)
      })
      .catch(err => {
        console.error('批量同步对话失败:', err)
      })
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (message) => {
    if (!message.trim()) return

    const userMessage = { 
      role: 'user', 
      content: message,
      timestamp: new Date().toISOString()
    }
    const updatedMessages = [...messages.map(msg => ({
      ...msg,
      timestamp: msg.timestamp || new Date().toISOString()
    })), userMessage]
    setMessages(updatedMessages)
    setIsLoading(true)

    try {
      // 后端会自动添加系统消息，这里只发送历史对话（不含当前消息）
      const conversationHistory = messages.map((msg) => ({
        role: msg.role,
        content: msg.content
      }))
      
      const response = await axios.post(`${API_URL}/chat`, {
        message,
        conversation_history: conversationHistory,
        conversation_id: currentConversationId || undefined  // 传递对话ID用于RAG检索
      })

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString()
      }

      const finalMessages = [...updatedMessages, assistantMessage]
      setMessages(finalMessages)
      
      // 获取后端返回的conversation_id（如果后端生成了新的）
      const backendConversationId = response.data.conversation_id || currentConversationId
      
      // 创建或更新对话
      if (!currentConversationId) {
        // 使用后端返回的ID或生成新ID
        const newId = backendConversationId || Date.now().toString()
        const newConv = {
          id: newId,
          title: generateTitle(finalMessages),
          messages: finalMessages,
          updatedAt: formatDate(Date.now())
        }
        setCurrentConversationId(newId)
        await saveConversations([newConv, ...conversations])
      } else {
        // 确保使用后端返回的ID（如果后端有更新）
        const finalConversationId = backendConversationId || currentConversationId
        if (backendConversationId && backendConversationId !== currentConversationId) {
          setCurrentConversationId(backendConversationId)
        }
        updateConversation(finalConversationId, finalMessages)
      }
    } catch (error) {
      console.error('Error:', error)
      const errorMessage = {
        role: 'assistant',
        content: '抱歉，发生了错误。请稍后再试。'
      }
      const finalMessages = [...updatedMessages, errorMessage]
      setMessages(finalMessages)
      
      if (currentConversationId) {
        updateConversation(currentConversationId, finalMessages)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const updateConversation = async (id, msgs) => {
    const updated = conversations.map(conv => {
      if (conv.id === id) {
        const title = generateTitle(msgs)
        return {
          ...conv,
          messages: msgs,
          title,
          updatedAt: formatDate(Date.now())
        }
      }
      return conv
    })
    await saveConversations(updated)
  }

  const newConversation = async () => {
    const newId = Date.now().toString()
    const newConv = {
      id: newId,
      title: '新对话',
      messages: [],
      updatedAt: formatDate(Date.now())
    }
    const updated = [newConv, ...conversations]
    await saveConversations(updated)
    setCurrentConversationId(newId)
    setMessages([])
  }

  const selectConversation = (id) => {
    const conversation = conversations.find(c => c.id === id)
    if (conversation) {
      setCurrentConversationId(id)
      setMessages(conversation.messages)
    }
  }

  const deleteConversation = async (id) => {
    // 如果API_URL未指向本地后端，跳过后端删除（对话历史管理必须在本地后端）
    if (!isLocalBackend) {
      console.warn(`跳过后端删除：API_URL (${API_URL}) 未指向本地后端，仅从localStorage删除`)
      // 直接更新前端状态
      const updated = conversations.filter(c => c.id !== id)
      saveConversations(updated)
      
      if (currentConversationId === id) {
        if (updated.length > 0) {
          setCurrentConversationId(updated[0].id)
          setMessages(updated[0].messages)
        } else {
          setCurrentConversationId(null)
          setMessages([])
        }
      }
      return
    }
    
    try {
      // 调用后端API删除对话
      await axios.delete(`${API_URL}/conversation/${id}`)
      
      // 更新前端状态
      const updated = conversations.filter(c => c.id !== id)
      saveConversations(updated)
      
      if (currentConversationId === id) {
        if (updated.length > 0) {
          setCurrentConversationId(updated[0].id)
          setMessages(updated[0].messages)
        } else {
          setCurrentConversationId(null)
          setMessages([])
        }
      }
    } catch (error) {
      console.error('删除对话失败:', error)
      if (error.response?.status === 404) {
        console.error('404错误：DELETE端点不存在！')
        console.error('请确认前端API_URL指向本地后端 (http://localhost:8000)')
        console.error('本地后端必须包含 DELETE /conversation/{id} 端点')
      }
      // 即使后端删除失败，也更新前端状态（保持用户体验）
      const updated = conversations.filter(c => c.id !== id)
      saveConversations(updated)
      
      if (currentConversationId === id) {
        if (updated.length > 0) {
          setCurrentConversationId(updated[0].id)
          setMessages(updated[0].messages)
        } else {
          setCurrentConversationId(null)
          setMessages([])
        }
      }
    }
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-orange-50 via-red-50 to-pink-50">
      {/* Sidebar */}
      <div className="w-80 flex-shrink-0 shadow-xl border-r border-gray-200/50">
        <ConversationList
          conversations={conversations}
          currentConversationId={currentConversationId}
          onSelectConversation={selectConversation}
          onNewConversation={newConversation}
          onDeleteConversation={deleteConversation}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <header className="bg-white/80 backdrop-blur-md shadow-sm px-6 py-5 border-b border-gray-200/50 sticky top-0 z-10">
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <div className="flex items-center space-x-4">
              <div className="relative">
                <div className="w-14 h-14 bg-gradient-to-br from-orange-500 via-red-500 to-pink-600 rounded-2xl flex items-center justify-center shadow-lg shadow-orange-500/30 transform transition-transform hover:scale-105">
                  <svg
                    className="w-7 h-7 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                </div>
                <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-white shadow-sm"></div>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
                  心理医生聊天室
                </h1>
                <p className="text-sm text-gray-500 mt-0.5">专业的心理支持与倾听</p>
              </div>
            </div>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-8 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 && (
              <div className="text-center py-16 animate-fade-in">
                <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-orange-100 via-red-100 to-pink-100 rounded-3xl mb-6 shadow-lg">
                  <svg
                    className="w-12 h-12 text-orange-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                    />
                  </svg>
                </div>
                <h2 className="text-3xl font-bold text-gray-800 mb-3">
                  欢迎，有什么可以帮你的？
                </h2>
                <p className="text-gray-500 text-lg">
                  我是一个专业的心理医生，愿意倾听和帮助你。
                </p>
              </div>
            )}

            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}

            {isLoading && (
              <div className="flex justify-start animate-fade-in">
                <div className="bg-white rounded-2xl rounded-tl-sm px-6 py-5 shadow-lg max-w-xl border border-gray-100">
                  <div className="flex space-x-2">
                    <div className="w-2.5 h-2.5 bg-orange-400 rounded-full animate-bounce"></div>
                    <div className="w-2.5 h-2.5 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2.5 h-2.5 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="bg-white/80 backdrop-blur-md border-t border-gray-200/50 px-4 py-5 shadow-lg">
          <div className="max-w-4xl mx-auto">
            <MessageInput onSendMessage={sendMessage} disabled={isLoading} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
