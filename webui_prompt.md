# OpenAGI WebUI 完整重构设计规范 v2.0

## 核心任务
重构 OpenAGI 前端，参考 OpenClaw 的设计，实现现代化、高性能、视觉友好的Web UI。基于当前完整功能基础上，优化交互、性能和视觉体验。

---

## 📋 当前功能分析与保留项

### ✅ 已完美实现（必须保留）

#### 架构与技术栈
- **React 18 + TypeScript 5** - 完整的类型安全开发
- **Vite 构建系统** - 快速热更新和优化打包
- **CSS Modules + CSS Variables** - 灵活的主题切换系统
- **WebSocket 集成** - 实时双向通信，消息队列，自动重连
- **REST API 集成** - axios 请求拦截，错误处理

#### 主题系统（Dark/Light/Auto）
- CSS 变量定义完整：背景色、边框色、文字色、强调色
- 玻璃态效果（Glassmorphism）- backdrop-filter + border-blur
- 颜色系统：Blue、Green、Cyan、Purple、Yellow、Red
- 动画系统：slideIn、fadeIn、pulse、shimmer 等

#### 9 页面框架
1. **Chat** - 实时消息、快速按钮、输入区域
2. **Dashboard** - 系统状态卡片、能力评分
3. **History** - 会话列表、搜索过滤
4. **Channels** - 频道管理、配置编辑
5. **Tools** - 工具列表、执行历史
6. **Skills** - 技能卡片、参数配置
7. **Goals** - 目标管理、进度追踪
8. **Logs** - 实时日志流、级别过滤
9. **Memory** - 内存事件表、语义搜索

#### 导航与布局
- **Icon-only Sidebar** (60px) - FA Icons 清晰直观
- **全屏宽度设计** - 内容区充分利用空间
- **Settings Modal** - 基础/路由/高级/快捷键/危险区域 5 标签页
- **响应式设计** - 支持桌面/平板/手机

---

## ⚠️ 需要改进的部分

### 1. Dashboard 页面 - 缺乏交互性
**当前问题**：
- Capability Radar 图表为纯静态展示
- 系统状态卡片无实时更新动画
- 无悬停交互效果
- 图表无动画过渡

**改进方案**：
- ✨ **Capability Radar** 增加：
  - 数据变化时的过渡动画（capability值变化时圆弧动画）
  - 鼠标悬停显示详细信息 tooltip
  - 点击维度展开详细分析
  - 颜色渐变基于值大小
- 📊 **系统状态卡片** 增加：
  - Uptime 实时计时动画
  - 内存使用图表（迷你线图或环形图）
  - 响应时间趋势（小型 sparkline）
  - 工具使用率柱状图
- 🎯 **新增快速卡片**：
  - 最近 3 个目标进度（进度条动画）
  - 今日任务完成率（环形进度图）
  - 最常用 3 个工具
  - 系统健康度评分（圆形饼图）

### 2. Chat 页面 - 动画和交互优化
**当前问题**：
- 消息加载动画简单
- 思考状态三点动画不够生动
- 无消息操作 UI（复制、收藏、重生成等）
- 快速按钮响应反馈不足

**改进方案**：
- 💬 **消息加载动画**：
  - 消息逐字显示动画（打字效果）
  - Skeleton 消息占位符（3 行灰色渐变）
  - 消息组动画进场
  - 不同消息类型的进场动画
- 🤔 **思考状态**：
  - 动画脉冲波纹效果（thinking 状态）
  - 微妙的 shimmer 动画
  - "正在思考..." 文本动画
- ✨ **消息操作菜单**：
  - 鼠标悬停消息时显示操作按钮（复制、反应、重生成）
  - 复制成功 toast 反馈
  - 快速操作图标
- ⚡ **快速按钮**：
  - 点击时有按压反馈动画
  - 禁用状态的灰显效果
  - 生成中的加载指示

### 3. History 页面 - 视觉和功能增强
**当前问题**：
- 会话卡片较为简单
- 搜索反馈不足
- 无预览功能
- 列表加载状态不清楚

**改进方案**：
- 📋 **会话卡片优化**：
  - 卡片悬停放大动画和阴影效果
  - 右侧快速操作菜单（查看、编辑、删除、导出）
  - 时间戳格式化（"2小时前" 而非时间戳）
  - 消息数、Token 使用量展示
  - 标签/分类显示（可点击过滤）
- 🔍 **搜索增强**：
  - 搜索框 focus 时 expand 动画
  - 搜索过程中的 skeleton cards
  - 搜索结果高亮显示关键词
  - 搜索历史记录（下拉菜单）
- 👁️ **预览功能**：
  - 悬停卡片时显示对话片段预览
  - Modal 预览整个会话（虚拟滚动）
  - 对话导出为 PDF/Markdown

### 4. Memory 页面 - 可视化和交互
**当前问题**：
- 内存事件表格展示单调
- FAISS 索引可视化缺失
- 无搜索结果可视化
- 数据删除无确认

**改进方案**：
- 📊 **Memory 可视化**：
  - FAISS 嵌入空间的 2D/3D 投影展示（使用 plotly 或 visx）
  - 相似度热力图
  - 事件聚类可视化
  - 时间轴展示
- 🔎 **搜索交互**：
  - 语义搜索结果排序和相似度评分展示
  - 搜索结果高亮和相似度条形图
  - 搜索建议（基于历史查询）
- 🗑️ **删除交互**：
  - 删除前的确认模态框（带预览）
  - 批量删除选项（checkbox）
  - Undo 功能（5 秒内可恢复）
  - 清空警告模态框

### 5. Logs 页面 - 性能和可读性
**当前问题**：
- 日志量大时性能下降
- 过滤选项有限
- 日志可读性可改进

**改进方案**：
- 📜 **虚拟滚动优化**：
  - 仅渲染可见日志行（react-window）
  - 支持 1000+ 日志条目无卡顿
- 🎨 **日志格式和着色**：
  - ERROR 红色、WARNING 黄色、INFO 蓝色、DEBUG 灰色
  - JSON 日志语法高亮
  - 日志时间戳 tooltip（精确毫秒）
- 🔧 **过滤增强**：
  - 多选过滤器（级别、模块、时间范围）
  - 搜索框支持正则表达式
  - 保存常用过滤组合

### 6. Channels/Tools/Skills/Goals 页面 - 通用增强
**改进方案**：
- 🃏 **卡片设计统一**：
  - 悬停阴影提升动画
  - 操作按钮在悬停时显示（缓慢 fade 进入）
  - 快速预览信息（tooltip）
- 🔄 **加载状态**：
  - Skeleton cards 占位符
  - Loading spinner 居中
  - "无数据" 状态插画
- 📱 **搜索和过滤**：
  - 实时过滤（debounce 搜索）
  - 标签/分类过滤
  - 排序选项（按名称、日期、使用频率）

---

## 🎯 新增功能需求

### 1. 全局加载优化（首要任务）

#### Skeleton Preview UI
```
实现 Skeleton Loading 组件库：
- SkeletonCard - 3 行灰色波浪线
- SkeletonChart - 图表骨架（网格 + 线条）
- SkeletonTable - 表格行骨架
- SkeletonText - 文本骨架（不同宽度）
- SkeletonAvatar - 圆形骨架

应用到所有初始加载页面：
- Dashboard 首屏加载时显示 skeleton cards
- History 列表初始加载时显示 skeleton list
- Memory 表格初始加载时显示 skeleton rows
```

#### Optimistic UI（即时反馈）
```
用户操作后立即显示预期结果，无需等待服务器：

1. 删除操作：
   - 点击删除时立即从列表移除
   - 后台发送删除请求
   - 失败时恢复数据，显示错误提示

2. 创建操作：
   - 点击创建时立即显示新项目（灰显/虚线边框标记）
   - 后台上传数据
   - 成功后移除标记，更新 ID
   
3. 更新操作：
   - 修改设置值后立即反映 UI
   - 后台同步到服务器
   - 失败时回滚并显示错误

示例：Settings 修改任何选项 → 立即保存到 localStorage → 后台 POST 到服务器
```

#### Progress Illusions（进度幻觉）
```
让等待时间感觉更短 - 使用假的进度条优化感知等待时间：

1. 工具执行进度：
   - 快速增长到 30%（0.5s）
   - 缓慢增长到 90%（全过程）
   - 完成时快速到 100%
   - 动画曲线：cubic-bezier(0.25, 0.46, 0.45, 0.94)

2. 数据加载进度：
   - 显示多步骤进度（获取数据 → 解析 → 渲染）
   - 每步有对应的进度条分段
   - 微妙的脉冲动画

3. 消息生成进度：
   - 显示 tokens 生成进度（预估）
   - 用小型环形进度条

代码示例：
const [progress, setProgress] = useState(0);
useEffect(() => {
  let p = 0;
  const interval = setInterval(() => {
    p = Math.min(p + Math.random() * 30, 90);
    setProgress(p);
  }, 200);
  return () => clearInterval(interval);
}, []);
```

#### Fast Start（快速启动）
```
应用启动和页面切换时的快速反馈：

1. 应用首屏（< 1s）：
   - 显示 Logo + 品牌名称
   - 执行必要的初始化（WebSocket 连接、加载设置）
   - 显示简单动画（fade-in）
   - 准备好后自动跳转到 Chat 页面

2. 页面切换（< 200ms）：
   - 点击页面 tab 时立即显示 skeleton UI
   - 后台并行加载数据
   - 数据到达时逐个替换 skeleton

3. 导航反馈：
   - 点击 nav item 时立即高亮
   - 页面过渡动画（slide/fade）
   - 活跃页面指示器立即更新
```

### 2. 动画和过渡系统

#### 进场/出场动画
```
所有页面/模态框/卡片都应有平滑过渡：

Page transitions:
- Enter: slideInFromRight (200ms)
- Exit: slideOutToLeft (150ms)

Modal dialogs:
- Enter: scaleIn + fadeIn (300ms) + blur backdrop
- Exit: scaleOut + fadeOut (150ms)

Card hovers:
- Scale: 1 → 1.02
- Shadow: 升级
- Duration: 200ms
```

#### 微交互动画
```
所有交互元素都应有反馈：

按钮点击：
- 按压效果：scale(0.98)
- 涟漪效果：从点击点扩散
- 反馈动画：100ms

输入框 focus：
- Border 颜色变化
- Glow 动画
- Label 上浮

列表项悬停：
- 背景颜色渐变
- 右侧操作按钮 fade in
- 阴影提升

滚动过程中：
- 脉冲动画（subtle pulse）
- 显示更多指示（↓ arrow）
```

### 3. 现代玻璃态效果（Modern Glassmorphism）

#### 当前效果保留
- 半透明背景 + backdrop-filter blur
- 边框渐变色
- 悬停时的 border-bright 变化

#### 新增增强
```
深度感和分层：
- Surface 分为 3 级（surface-1, surface-2, surface-3）
- 每级逐渐增加不透明度和模糊
- 使用 box-shadow 创建深度

特效增强：
1. Frosted Glass - 更强的 blur（blur(32px)）+ 更低的透明度
2. Neon Glow - 边框添加 glow 效果（box-shadow: 0 0 20px rgba(color, 0.3)）
3. Reflection Effect - 伪元素创建倒影（可选）
4. Floating Effect - 悬停时轻微上浮（transform: translateY(-4px)）

CSS 变量新增：
--blur-lg: blur(32px)
--glow-primary: 0 0 20px rgba(var(--blue-rgb), 0.3)
--glow-success: 0 0 20px rgba(var(--green-rgb), 0.3)
```

### 4. 响应式和性能优化

#### 响应式设计
```
Breakpoints:
- Mobile: < 640px - Sidebar 隐藏，Button 变小
- Tablet: 640px - 1024px - Sidebar 60px，内容自适应
- Desktop: > 1024px - 完整布局

特殊处理：
- Mobile 上：modal 全屏显示
- Tablet 上：图表响应式缩小
- 触屏设备：增加按钮大小，去除 hover 效果
```

#### 性能优化
```
1. 代码分割：
   - 每个 page 单独 chunk
   - 按需加载 heavy 组件（charts, modals）

2. 图片优化：
   - WebP 格式 + fallback
   - 响应式图片（srcset）
   - Lazy loading

3. 动画优化：
   - 使用 will-change 声明
   - 使用 transform/opacity（GPU 加速）
   - 避免布局抖动（layout thrashing）
   - 帧率检测（requestAnimationFrame）

4. 内存优化：
   - 虚拟滚动 for 长列表
   - 组件卸载时清理事件监听
   - Memoization for 复杂计算
```

---

## 🎨 设计系统完整规范

### 色彩系统
```
Light Theme:
--bg: #f0f5ff （柔和蓝白）
--surface-1/2/3: rgba(255,255,255, 0.7/0.85/0.95) （递进不透明）
--text: #1a1a2e （深蓝灰）
--blue: #4d8af0
--green: #36d399
--cyan: #0dcad9
--purple: #8b5cf6
--yellow: #fbbf24
--red: #ff6b6b

Dark Theme:
--bg: #0a0a12 （极深蓝）
--surface-1/2/3: rgba(20,20,35, 0.7/0.85/0.95) （对应递进）
--text: #e2e8f0 （浅灰蓝）
--blue: #60a5fa （更亮）
...其他颜色相应调整
```

### 排版
```
Font Stack:
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI'
--font-mono: 'JetBrains Mono', 'Fira Code', 'Monaco'

Font Sizes:
- h1: 32px / bold / leading-tight
- h2: 24px / semi-bold
- h3: 18px / semi-bold
- body: 14px / 16px
- small: 12px
- code: 13px / mono font
```

### 间距系统
```
--gap-2: 8px
--gap-4: 16px
--gap-6: 24px
--gap-8: 32px
```

### 圆角
```
--radius: 16px （卡片/大组件）
--radius-lg: 20px （更圆的元素）
--radius-sm: 8px （小按钮）
--radius-full: 9999px （完全圆形）
```

---

## 📦 依赖库和工具

### 核心依赖（已有）
```json
{
  "react": "^18.3.0",
  "react-dom": "^18.3.0",
  "typescript": "^5.3.0",
  "vite": "^5.0.0",
  "react-icons": "^5.0.0"
}
```

### 新增必需依赖
```json
{
  "recharts": "^2.10.0",           // 交互式图表库
  "framer-motion": "^10.16.0",     // 高性能动画库
  "react-markdown": "^9.0.0",       // Markdown 渲染
  "react-syntax-highlighter": "^15.5.0", // 代码高亮
  "react-hot-toast": "^2.4.0",     // Toast 通知
  "zustand": "^4.4.0",             // 轻量状态管理
  "clsx": "^2.0.0",                // 条件类名工具
  "date-fns": "^3.0.0",            // 日期处理
  "lodash-es": "^4.17.21",         // 工具函数库
  "react-window": "^8.8.0",        // 虚拟滚动
  "plotly.js": "^2.26.0",          // 数据可视化（Memory 页面）
  "@radix-ui/react-dialog": "^1.1.0", // 无样式 Dialog 基础
  "axios": "^1.6.0"                // HTTP 客户端
}
```

### 开发依赖
```json
{
  "tailwindcss": "^3.3.0",
  "postcss": "^8.4.0",
  "autoprefixer": "^10.4.0",
  "eslint": "^8.55.0",
  "@typescript-eslint/eslint-plugin": "^6.10.0",
  "prettier": "^3.1.0"
}
```

---

## 📄 页面详细规范

### Chat 页面
```
布局：
┌─────────────────────────────────────┐
│ Header: 对话标题 + 更多菜单         │
├─────────────────────────────────────┤
│                                     │
│  消息列表（虚拟滚动）                │
│  - User 消息（右对齐）              │
│  - Agent 消息（左对齐，支持 MD）   │
│  - Thinking 状态（脉冲动画）        │
│  - System 消息（居中，虚线边框）   │
│                                     │
├─────────────────────────────────────┤
│ 快速按钮行（8 个按钮，2 行）       │
├─────────────────────────────────────┤
│ [麦克风] [输入框....] [发送]        │
└─────────────────────────────────────┘

功能需求：
✨ 消息加载动画（逐字显示）
✨ Skeleton 消息占位符
✨ 消息操作菜单（悬停显示）
✨ 思考动画（脉冲 + shimmer）
✨ 快速按钮按压反馈
✨ 输入框 focus 边框变化
✨ 消息组进场动画
✨ 无消息状态插画
✨ 复制成功 toast
```

### Dashboard 页面
```
布局（4 列网格）：
┌──────────────────────────────────────────┐
│ 系统状态 │ 工具数 │ 内存使用 │ 性能指标  │
├──────────────────────────────────────────┤
│ Capability Radar（交互式）  │ 最近活动   │
├──────────────────────────────────────────┤
│ 快速统计（目标/工具） │ 最常用工具    │
└──────────────────────────────────────────┘

卡片内容：
1. 系统状态：
   - 在线/离线（彩色指示灯）
   - Uptime 计时器（实时更新）
   - 响应时间趋势线

2. 工具数：
   - 总数大字
   - 活跃数下标
   - 迷你柱状图（用法频率）

3. 内存使用：
   - 大字 MB
   - 占比百分比
   - 迷你环形图

4. 性能指标：
   - 平均响应时间
   - 请求/分钟 sparkline

5. Capability Radar：
   - 7 维雷达图（交互式）
   - 悬停显示维度详情
   - 点击展开详细分析

功能：
✨ 数据实时更新
✨ 卡片悬停阴影提升
✨ 图表过渡动画
✨ 响应式网格
```

### History 页面
```
布局：
┌────────────────────────────────────┐
│ 搜索框 [搜索...] 📅 📊              │
├────────────────────────────────────┤
│ 按日期分组：                        │
│ 📅 2025-04-19 (5 个会话)          │
│   - 📄 会话标题 - 12:30            │
│     💬 消息数: 23 | ⏱ 时长: 15m  │
│     [查看] [删除] [导出]           │
│   - 📄 另一个会话                  │
│ 📅 2025-04-18 (3 个会话)          │
│   - ...                            │
└────────────────────────────────────┘

功能需求：
✨ 日期分组 section headers
✨ 会话卡片悬停动画
✨ 快速操作菜单（查看、删除、导出）
✨ 搜索实时过滤
✨ Skeleton cards 加载状态
✨ 会话预览 modal（虚拟滚动消息）
✨ 时间格式化（"2 小时前"）
✨ 无数据状态插画
```

### Channels 页面
```
布局：
┌────────────────────────────────────┐
│ [+ 添加频道] 频道列表               │
├────────────────────────────────────┤
│ 频道卡片：                          │
│ 📱 Telegram                         │
│ 状态: 已连接 🟢                    │
│ DM 策略: 全部                      │
│ Allowlist: @user1, @user2          │
│ [配置] [删除]                      │
│                                    │
│ 💬 Discord                         │
│ 状态: 断开连接 🔴                  │
│ ...                                │
└────────────────────────────────────┘

功能：
✨ 卡片悬停阴影
✨ 状态指示灯（绿/红）
✨ 配置弹窗（编辑字段）
✨ 删除确认对话
✨ 频道图标
```

### Tools/Skills/Goals 页面
```
统一卡片设计：
┌──────────────────────────────┐
│ 📌 工具/技能/目标名称          │
│ 描述文本，最多 2 行           │
│                              │
│ 标签: [标签1] [标签2]         │
│ 进度: [=====>    ] 60%（仅Goal）
│                              │
│ [运行/操作] [更多]            │
└──────────────────────────────┘

功能：
✨ 卡片悬停提升 + 阴影
✨ 操作按钮 fade in on hover
✨ 搜索/过滤实时响应
✨ Skeleton cards
✨ Responsive grid (2-4 列)
```

### Logs 页面
```
布局：
┌────────────────────────────────────┐
│ 级别: [ERROR] [WARNING] [INFO]     │
│ 模块: [Kernel] [Tool] [Memory]    │
│ 搜索: [搜索日志...]               │
├────────────────────────────────────┤
│ 实时日志流（虚拟滚动）：           │
│ 12:34:56 [Kernel] INFO  工具执行.. │
│ 12:34:57 [Memory] DEBUG 存储事件.. │
│ ...（最多显示 100 条）            │
│                              |    │
│ ↓ 新消息 (自动滚动到底)          │
└────────────────────────────────────┘

功能：
✨ 虚拟滚动（react-window）
✨ 日志着色（ERROR 红、WARNING 黄）
✨ 多选过滤器
✨ 搜索正则支持
✨ JSON 日志语法高亮
✨ 时间戳 tooltip
✨ 自动滚动到底
```

### Memory 页面
```
布局（2 列）：
┌──────────────────┬──────────────────┐
│ 事件表             │ 可视化             │
│                  │                  │
│ 搜索: [语义搜索]  │ FAISS 投影      │
│ 类型: [所有]      │ (2D/3D 散点)    │
│                  │                  │
│ 事件列表           │ 相似度热力图      │
│ (虚拟滚动)        │                  │
│                  │ 时间轴             │
└──────────────────┴──────────────────┘

功能：
✨ 语义搜索（带相似度评分）
✨ 搜索结果高亮
✨ 批量删除（checkbox）
✨ 删除确认 + Undo（5s）
✨ FAISS 可视化（3D scatter）
✨ 事件聚类显示
✨ 时间轴视图
```

---

## 🎬 动画和过渡规范

### 全局动画时间线
```
快速反馈: 100-150ms
- 按钮按压
- Icon 变化
- 列表项高亮

页面过渡: 200-300ms
- 页面进场 slideIn
- 模态框缩放进场
- 卡片进场

复杂动画: 500-800ms
- 图表数据更新
- 进度条完成
- Radar 图表旋转更新
```

### Easing 曲线
```
标准过渡: cubic-bezier(0.4, 0, 0.2, 1)
缓入: cubic-bezier(0.42, 0, 1, 1)
缓出: cubic-bezier(0, 0, 0.58, 1)
弹性: cubic-bezier(0.68, -0.55, 0.265, 1.55)
```

---

## 🚀 开发阶段分解

### Phase 1: 基础优化（Week 1）
- [ ] Skeleton Loading UI 组件库
- [ ] Optimistic UI 实现（Settings 优先）
- [ ] Progress Illusions（进度条）
- [ ] Fast Start 初屏优化
- [ ] 基础动画系统集成

### Phase 2: 页面增强（Week 2）
- [ ] Dashboard 图表交互
- [ ] Chat 消息动画
- [ ] History 卡片优化
- [ ] Memory 可视化
- [ ] Logs 虚拟滚动

### Phase 3: 视觉和交互（Week 3）
- [ ] 现代玻璃态效果增强
- [ ] 微交互动画（按钮、输入、列表）
- [ ] 主题系统深化
- [ ] 响应式设计完善

### Phase 4: 性能和兼容性（Week 4）
- [ ] 代码分割和 lazy loading
- [ ] 性能审计和优化
- [ ] 跨浏览器兼容性测试
- [ ] 无障碍访问 (A11y)

---

## ✅ 验收标准

### 功能验收
- [ ] 所有 9 页面完全可用
- [ ] WebSocket 实时通信正常
- [ ] Settings 完整功能
- [ ] 响应式设计 (Mobile/Tablet/Desktop)

### 性能验收
- [ ] 首屏加载 < 1.5s
- [ ] FCP (First Contentful Paint) < 1s
- [ ] Lighthouse Performance > 90
- [ ] 消息列表可流畅滚动 1000+ 条

### 视觉验收
- [ ] Dark/Light 主题完整
- [ ] 所有过渡动画平滑
- [ ] 玻璃态效果视觉完整
- [ ] 品牌色彩应用一致

### 交互验收
- [ ] 所有按钮有反馈
- [ ] 表单输入有 focus 状态
- [ ] 列表过滤实时响应
- [ ] 模态框开关流畅

---

## 📝 实施说明

这个规范涵盖了：
1. ✅ **完美保留部分** - 架构、技术栈、主题系统
2. ⚠️ **需要改进部分** - 交互性、可视化、性能
3. 🎯 **新增功能** - Skeleton UI、Optimistic UI、Progress Illusions、Fast Start
4. 🎨 **设计系统** - 色彩、排版、间距、动画
5. 📦 **技术依赖** - 必需的新库和工具
6. 🎬 **详细规范** - 每个页面的布局、功能、动画
7. 🚀 **实施计划** - 4 周分阶段开发

### 核心强调

**首要目标**：
1. Skeleton Loading + Optimistic UI（让界面感觉更快）
2. 交互动画（让界面感觉更生动）
3. Progress Illusions（改善感知等待时间）

**次要目标**：
1. 图表交互（Dashboard 图表）
2. 可视化增强（Memory FAISS）
3. 虚拟滚动优化（Logs、History）

**可选目标**：
1. 3D 效果（Memory 3D 投影）
2. 高级动画（粒子效果、morphing）
3. 国际化支持

---

## 🔗 后端无修改

所有前端改进都基于现有 REST API 和 WebSocket 协议。
不需要修改后端，只需优化前端展示层。
