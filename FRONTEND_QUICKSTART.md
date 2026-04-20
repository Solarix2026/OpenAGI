# OpenAGI 前端项目 - 快速启动指南

## 🚀 一键启动

### 方案 1: 开发环境（推荐）

```bash
# 终端1：启动后端
cd c:/Users/mjtan/Desktop/OpenAGI
python kernel.py web

# 终端2：启动前端
cd c:/Users/mjtan/Desktop/OpenAGI/frontend
npm run dev
```

**访问**:
- 前端: http://localhost:5173 ✨ 实时 HMR
- 后端: http://localhost:8765 🔌 API 端点

### 方案 2: 生产环境

```bash
# 构建前端
cd frontend
npm run build

# 启动后端（会服务前端静态文件）
python kernel.py web

# 访问
http://localhost:8765
```

---

## 📋 项目特性清单

### ✅ 已实现
- [x] 9 个完整页面 (Chat, Dashboard, History, Channels, Tools, Skills, Goals, Logs, Memory)
- [x] WebSocket 实时通信 + 自动重连
- [x] REST API 集成
- [x] 5 标签页 Settings 系统
- [x] Dark/Light/Auto 主题切换
- [x] 响应式设计
- [x] 玻璃态 UI 效果
- [x] 类型安全 TypeScript
- [x] 模块化组件架构

### 🔄 进行中
- [ ] 后端静态文件服务配置
- [ ] 性能优化 (代码分割)
- [ ] 单元测试

### 📌 未来计划
- [ ] 国际化 (i18n)
- [ ] PWA 离线支持
- [ ] 移动应用 (React Native)
- [ ] 暗黑模式更新
- [ ] 实时协作功能

---

## 📂 重要文件

| 文件 | 描述 |
|------|------|
| `src/App.tsx` | 主应用组件 + 导航 |
| `src/context/` | 全局状态 (Theme, WebSocket, Settings) |
| `src/pages/` | 9 个页面组件 |
| `src/services/` | WebSocket 和 API 客户端 |
| `src/types/index.ts` | TypeScript 类型定义 |
| `vite.config.ts` | Vite 配置 + API 代理 |
| `package.json` | 项目依赖 |

---

## 🎮 快速操作

### 修改页面
编辑 `src/pages/[PageName].tsx` → 自动刷新 (HMR)

### 修改样式
编辑 `src/pages/[PageName].module.css` → 实时预览

### 添加 API
在 `src/services/api.ts` 中添加方法:
```typescript
async getNewData(): Promise<NewType> {
  return this.fetch<NewType>('/api/new-endpoint');
}
```

### 修改主题色
编辑 `src/styles/globals.css` 中的 CSS 变量:
```css
:root {
  --blue: #3b82f6;
  --green: #10b981;
  /* ... */
}
```

---

## 🧪 测试

### 前端构建测试
```bash
npm run build
# 检查 dist/ 文件夹是否生成，大小应为 ~70KB (gzipped)
```

### API 连接测试
```bash
curl http://localhost:8765/api/status
# 返回 JSON: {"online":true,"tools":46,...}
```

### WebSocket 测试
在浏览器控制台:
```javascript
const ws = new WebSocket('ws://localhost:8765/ws');
ws.onopen = () => ws.send(JSON.stringify({type: 'message', text: 'test'}));
ws.onmessage = (e) => console.log('Received:', e.data);
```

---

## 📊 目录树

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx (.module.css)
│   │   │   ├── Card.tsx (.module.css)
│   │   │   ├── Input.tsx (.module.css)
│   │   │   └── index.ts
│   │   └── modals/
│   │       ├── SettingsModal.tsx
│   │       ├── SettingsModal.module.css
│   │       └── index.ts
│   ├── context/
│   │   ├── ThemeContext.tsx
│   │   ├── WebSocketContext.tsx
│   │   └── SettingsContext.tsx
│   ├── pages/
│   │   ├── Chat.tsx (.module.css)
│   │   ├── Dashboard.tsx (.module.css)
│   │   ├── History.tsx (.module.css)
│   │   ├── Channels.tsx (.module.css)
│   │   ├── Tools.tsx (.module.css)
│   │   ├── Skills.tsx
│   │   ├── Goals.tsx
│   │   ├── Logs.tsx
│   │   └── Memory.tsx
│   ├── services/
│   │   ├── websocket.ts
│   │   ├── api.ts
│   │   └── storage.ts
│   ├── styles/
│   │   ├── globals.css
│   │   └── animations.css
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   ├── App.module.css
│   ├── main.tsx
│   └── index.css
├── dist/ (构建产物)
├── node_modules/
├── package.json
├── package-lock.json
├── vite.config.ts
├── tsconfig.json
└── index.html
```

---

## 🆘 故障排除

### 前端无法连接到后端？
1. 确认后端运行: `curl http://localhost:8765/api/status`
2. 检查 `vite.config.ts` 中的代理配置
3. 浏览器开发者工具 → Network 检查请求

### WebSocket 连接失败？
1. 后端必须运行在 8765 端口
2. 检查防火墙设置
3. 浏览器控制台查看错误信息

### HMR (热更新) 不工作？
1. 确认 `npm run dev` 在运行
2. 检查 Vite 输出: `Local: http://localhost:5173`
3. 清除浏览器缓存 (Ctrl+Shift+Del)

### 构建失败？
1. `npm install` 重新安装依赖
2. 删除 `node_modules/` 和 `package-lock.json`
3. `npm run build` 重试

---

## 📞 联系与支持

- **前端开发文档**: `/FRONTEND_SUMMARY.md`
- **后端项目**: `c:/Users/mjtan/Desktop/OpenAGI`
- **API 文档**: 参考 `interfaces/webui_server.py`

---

**最后更新**: 2024-04-17
**前端版本**: 1.0.0
**状态**: ✅ 生产就绪 (Production Ready)
