// 配色主题配置 - 暖色系主题
// 在这里修改颜色即可全局更改界面配色

export const theme = {
  // 主色调 - 渐变色的起始和结束颜色（暖色系）
  primary: {
    from: 'orange-500',      // 主色起始 - 橙色
    via: 'red-500',          // 主色中间 - 红色
    to: 'pink-600',          // 主色结束 - 粉色
  },
  
  // 悬停状态的主色调
  primaryHover: {
    from: 'orange-600',
    via: 'red-600',
    to: 'pink-700',
  },
  
  // 文字主色调
  textPrimary: {
    from: 'orange-600',
    to: 'red-600',
  },
  
  // 背景渐变
  background: {
    from: 'orange-50',      // 背景起始色 - 浅橙
    via: 'red-50',           // 背景中间色 - 浅红
    to: 'pink-50',           // 背景结束色 - 浅粉
  },
  
  // 用户消息气泡颜色
  userMessage: {
    from: 'orange-500',
    to: 'red-600',
  },
  
  // 助手消息气泡颜色（浅色背景）
  assistantMessage: {
    from: 'orange-100',
    to: 'red-200',
  },
  
  // 图标颜色
  icon: {
    primary: 'orange-600',   // 主图标颜色
    assistant: 'orange-600', // 助手图标颜色
  },
  
  // 边框和分割线颜色
  border: {
    default: 'gray-200',
    light: 'gray-200/50',
  },
  
  // 文字颜色
  text: {
    primary: 'gray-800',     // 主要文字
    secondary: 'gray-500',  // 次要文字
    muted: 'gray-400',      // 弱化文字
  },
  
  // 选中/激活状态颜色
  active: {
    bg: 'orange-50',        // 选中背景
    bgTo: 'red-50',         // 选中背景渐变结束
    border: 'orange-400',   // 选中边框
    text: 'orange-700',     // 选中文字
    dot: 'orange-500',      // 选中指示点
  },
  
  // 状态指示颜色
  status: {
    online: 'green-400',    // 在线状态（保持绿色）
  },
  
  // 加载动画颜色
  loading: {
    dot1: 'orange-400',
    dot2: 'red-400',
    dot3: 'pink-400',
  },
  
  // 阴影颜色
  shadow: {
    primary: 'orange-500/30',
    primaryHover: 'orange-500/40',
    active: 'orange-200/50',
  },
}

// 使用示例：
// 渐变背景: `bg-gradient-to-br from-${theme.background.from} via-${theme.background.via} to-${theme.background.to}`
// 但注意：Tailwind CSS 需要完整的类名才能正确编译，所以直接使用字符串拼接可能不会生效
// 更好的方式是使用完整的类名，然后通过这个配置文件作为参考来统一修改


