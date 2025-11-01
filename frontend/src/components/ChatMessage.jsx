const ChatMessage = ({ message }) => {
  const isUser = message.role === 'user'

  const formatTime = (timestamp) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div className={`flex items-end space-x-2 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
        {/* Avatar */}
        <div
          className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-md ${
            isUser
              ? 'bg-gradient-to-br from-orange-500 to-red-600'
              : 'bg-gradient-to-br from-orange-100 to-red-200'
          }`}
        >
          {isUser ? (
            <svg
              className="w-5 h-5 text-white"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                clipRule="evenodd"
              />
            </svg>
          ) : (
            <svg
              className="w-5 h-5 text-orange-600"
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
          )}
        </div>

        {/* Message Bubble */}
        <div className="flex flex-col max-w-xl">
          <div
            className={`${
              isUser
                ? 'bg-gradient-to-br from-orange-500 to-red-600 text-white shadow-lg shadow-orange-500/30'
                : 'bg-white text-gray-800 shadow-lg border border-gray-100'
            } rounded-2xl px-5 py-4 ${
              isUser ? 'rounded-tr-sm' : 'rounded-tl-sm'
            } transition-all hover:shadow-xl`}
          >
            <p className="text-base leading-relaxed whitespace-pre-wrap break-words">
              {message.content}
            </p>
          </div>
          {message.timestamp && (
            <span className={`text-xs text-gray-400 mt-1 px-2 ${isUser ? 'text-right' : 'text-left'}`}>
              {formatTime(message.timestamp)}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default ChatMessage
