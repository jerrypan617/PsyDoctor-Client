const ConversationList = ({ conversations, currentConversationId, onSelectConversation, onNewConversation, onDeleteConversation }) => {
  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-white to-gray-50/50">
      {/* Header */}
      <div className="p-5 border-b border-gray-200/50 bg-white/50 backdrop-blur-sm">
        <button
          onClick={onNewConversation}
          className="w-full px-4 py-3 bg-gradient-to-r from-orange-500 via-red-500 to-pink-600 text-white rounded-xl hover:from-orange-600 hover:via-red-600 hover:to-pink-700 transition-all duration-200 flex items-center justify-center space-x-2 shadow-lg shadow-orange-500/30 hover:shadow-xl hover:shadow-orange-500/40 transform hover:scale-[1.02] active:scale-[0.98]"
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
              d="M12 4v16m8-8H4"
            />
          </svg>
          <span className="font-medium">新建对话</span>
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-3 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
        {conversations.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl mb-4">
              <svg
                className="w-8 h-8 text-gray-400"
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
            <p className="text-sm text-gray-500 font-medium">还没有对话记录</p>
            <p className="text-xs text-gray-400 mt-1">点击上方按钮开始新对话</p>
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                onClick={() => onSelectConversation(conversation.id)}
                className={`group relative p-4 rounded-xl cursor-pointer transition-all duration-200 ${
                  currentConversationId === conversation.id
                    ? 'bg-gradient-to-r from-orange-50 to-red-50 border-2 border-orange-400 shadow-md shadow-orange-200/50'
                    : 'hover:bg-white border-2 border-transparent hover:border-gray-200 hover:shadow-md'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-2">
                      <div className={`flex-shrink-0 w-2 h-2 rounded-full ${
                        currentConversationId === conversation.id
                          ? 'bg-orange-500'
                          : 'bg-gray-300 group-hover:bg-orange-400'
                      } transition-colors`}></div>
                      <p className={`text-sm font-semibold truncate ${
                        currentConversationId === conversation.id
                          ? 'text-orange-700'
                          : 'text-gray-700'
                      }`}>
                        {conversation.title}
                      </p>
                    </div>
                    <div className="flex items-center space-x-3 text-xs">
                      <span className={`${
                        currentConversationId === conversation.id
                          ? 'text-orange-600'
                          : 'text-gray-500'
                      }`}>
                        {conversation.messages.length} 条消息
                      </span>
                      <span className="text-gray-300">•</span>
                      <span className="text-gray-400">
                        {conversation.updatedAt}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteConversation(conversation.id)
                    }}
                    className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-red-50 transition-all ml-2"
                  >
                    <svg
                      className="w-4 h-4 text-red-500"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ConversationList

