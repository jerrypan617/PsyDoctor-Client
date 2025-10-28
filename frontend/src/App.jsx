import { useState, useRef, useEffect } from 'react'
import ChatMessage from './components/ChatMessage'
import MessageInput from './components/MessageInput'
import ConversationList from './components/ConversationList'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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

  // 保存对话列表到 localStorage
  const saveConversations = (updated) => {
    localStorage.setItem('conversations', JSON.stringify(updated))
    setConversations(updated)
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (message) => {
    if (!message.trim()) return

    const userMessage = { role: 'user', content: message }
    const updatedMessages = [...messages, userMessage]
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
        conversation_history: conversationHistory
      })

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response
      }

      const finalMessages = [...updatedMessages, assistantMessage]
      setMessages(finalMessages)
      
      // 创建或更新对话
      if (!currentConversationId) {
        const newId = Date.now().toString()
        const newConv = {
          id: newId,
          title: generateTitle(finalMessages),
          messages: finalMessages,
          updatedAt: formatDate(Date.now())
        }
        setCurrentConversationId(newId)
        saveConversations([newConv, ...conversations])
      } else {
        updateConversation(currentConversationId, finalMessages)
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

  const updateConversation = (id, msgs) => {
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
    saveConversations(updated)
  }

  const newConversation = () => {
    const newId = Date.now().toString()
    const newConv = {
      id: newId,
      title: '新对话',
      messages: [],
      updatedAt: formatDate(Date.now())
    }
    const updated = [newConv, ...conversations]
    saveConversations(updated)
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

  const deleteConversation = (id) => {
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

  return (
    <div className="flex h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Sidebar */}
      <div className="w-80 flex-shrink-0">
        <ConversationList
          conversations={conversations}
          currentConversationId={currentConversationId}
          onSelectConversation={selectConversation}
          onNewConversation={newConversation}
          onDeleteConversation={deleteConversation}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex flex-col flex-1">
        {/* Header */}
        <header className="bg-white shadow-sm px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-white"
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
              <div>
                <h1 className="text-2xl font-bold text-gray-800">心理医生聊天室</h1>
                <p className="text-sm text-gray-500">专业的心理支持与倾听</p>
              </div>
            </div>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-12">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-100 to-indigo-200 rounded-full mb-4">
                  <svg
                    className="w-10 h-10 text-blue-600"
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
                <h2 className="text-2xl font-semibold text-gray-700 mb-2">
                  欢迎，有什么可以帮你的？
                </h2>
                <p className="text-gray-500">
                  我是一个专业的心理医生，愿意倾听和帮助你。
                </p>
              </div>
            )}

            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white rounded-2xl rounded-tl-sm px-6 py-4 shadow-sm max-w-xl">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="bg-white border-t border-gray-200 px-4 py-4">
          <div className="max-w-4xl mx-auto">
            <MessageInput onSendMessage={sendMessage} disabled={isLoading} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
