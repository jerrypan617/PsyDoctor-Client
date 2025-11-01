import { useState, useRef, useEffect } from 'react'

const MessageInput = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('')
  const textareaRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSendMessage(message)
      setMessage('')
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
    }
  }, [message])

  return (
    <form onSubmit={handleSubmit} className="flex items-end space-x-3">
      <div className="flex-1 relative">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="输入你的消息... (Shift + Enter 换行)"
            disabled={disabled}
            rows={1}
            className="w-full px-5 py-4 bg-white border-2 border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-400 resize-none disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md focus:shadow-lg text-gray-700 placeholder-gray-400"
            style={{ maxHeight: '120px' }}
          />
          <div className="absolute bottom-2 right-3 text-xs text-gray-400 pointer-events-none">
            {message.length > 0 && `${message.length}`}
          </div>
        </div>
      </div>
      <button
        type="submit"
        disabled={!message.trim() || disabled}
        className="px-6 py-4 bg-gradient-to-r from-orange-500 via-red-500 to-pink-600 text-white rounded-2xl hover:from-orange-600 hover:via-red-600 hover:to-pink-700 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-orange-500/30 hover:shadow-xl hover:shadow-orange-500/40 transform hover:scale-105 active:scale-95 disabled:transform-none"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
          />
        </svg>
      </button>
    </form>
  )
}

export default MessageInput
