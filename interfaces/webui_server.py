# Copyright (c) 2026 HackerTMJ
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI
import asyncio, json, socket, os, logging
from pathlib import Path

log = logging.getLogger("WebUI")

HTML_V3 = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenAGI</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root { --bg: #020617; --surface-1: rgba(15,23,42,0.85); --surface-2: rgba(30,41,59,0.65); --surface-3: rgba(51,65,85,0.4); --border: rgba(148,163,184,0.08); --border-bright: rgba(148,163,184,0.14); --text: #e2e8f0; --text-muted: #64748b; --text-dim: #334155; --blue: #3b82f6; --blue-dim: rgba(59,130,246,0.12); --blue-border: rgba(59,130,246,0.25); --green: #10b981; --cyan: #06b6d4; --purple: #8b5cf6; --yellow: #f59e0b; --red: #ef4444; --blur: blur(24px); --blur-sm: blur(16px); --radius: 12px; --radius-sm: 8px; }
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100vh;overflow:hidden;background:var(--bg);color:var(--text);font-family:'Syne',system-ui,sans-serif}
.bg-mesh{position:fixed;inset:0;z-index:0; background: radial-gradient(ellipse 80% 60% at 15% 30%, rgba(59,130,246,0.055) 0%,transparent 65%), radial-gradient(ellipse 50% 40% at 85% 15%, rgba(139,92,246,0.04) 0%,transparent 65%), radial-gradient(ellipse 60% 35% at 55% 85%, rgba(6,182,212,0.035) 0%,transparent 65%), var(--bg); }
.glass{background:var(--surface-1);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);border:1px solid var(--border)}
.glass-sm{background:var(--surface-2);backdrop-filter:var(--blur-sm);-webkit-backdrop-filter:var(--blur-sm);border:1px solid var(--border)}
.glass-input{background:rgba(15,23,42,0.55);backdrop-filter:blur(12px);border:1px solid var(--border);transition:border-color .18s,box-shadow .18s}
.glass-input:focus{border-color:rgba(59,130,246,0.45);box-shadow:0 0 0 3px rgba(59,130,246,0.08);outline:none}
.root{position:relative;z-index:1;display:flex;flex-direction:column;height:100vh}
.header{height:48px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;border-bottom:1px solid var(--border);flex-shrink:0}
.header{background:rgba(2,6,23,0.9);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur)}
.main{display:flex;flex:1;min-height:0}
.sidebar{width:220px;flex-shrink:0;display:flex;flex-direction:column;border-right:1px solid var(--border)}
.sidebar{background:rgba(5,12,30,0.85);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur)}
.chat{flex:1;display:flex;flex-direction:column;min-width:0}
.rightbar{width:260px;flex-shrink:0;display:flex;flex-direction:column;border-left:1px solid var(--border)}
.rightbar{background:rgba(5,12,30,0.85);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur)}
#messages{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:14px}
.msg-row{display:flex;gap:10px;animation:fadeIn .22s ease-out}
.msg-row.user{flex-direction:row-reverse}
.avatar{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0}
.avatar.agent{background:rgba(59,130,246,0.2);border:1px solid rgba(59,130,246,0.3);color:#93c5fd}
.avatar.user{background:rgba(30,41,59,0.8);border:1px solid var(--border-bright);color:#94a3b8}
.avatar.system{background:rgba(139,92,246,0.15);border:1px solid rgba(139,92,246,0.25);color:#a78bfa}
.bubble{max-width:72%;padding:10px 14px;font-size:13.5px;line-height:1.65;border-radius:var(--radius);position:relative}
.bubble.agent{background:rgba(15,23,42,0.8);border:1px solid var(--border);backdrop-filter:blur(12px)}
.bubble.user{background:rgba(37,99,235,0.18);border:1px solid var(--blue-border)}
.bubble.proactive{background:rgba(139,92,246,0.1);border:1px solid rgba(139,92,246,0.2)}
.bubble.system{background:rgba(5,12,30,0.9);border:1px solid var(--border);color:var(--text-muted);font-size:12px}
.bubble strong{color:#f1f5f9}
.bubble code{font-family:'JetBrains Mono',monospace;font-size:.82em;background:rgba(0,0,0,.35);border:1px solid rgba(148,163,184,.1);padding:1px 6px;border-radius:4px;color:#93c5fd}
.bubble pre{background:rgba(0,0,0,.45);border:1px solid rgba(148,163,184,.1);border-radius:8px;padding:10px 12px;overflow-x:auto;margin:6px 0}
.bubble pre code{background:none;border:none;padding:0;color:#a5f3fc;font-size:12.5px}
.tool-card{background:rgba(2,6,23,.8);border-left:3px solid var(--blue);border:1px solid var(--border);border-left-width:3px;border-radius:var(--radius-sm);padding:8px 12px;margin:5px 0;font-size:12px;font-family:'JetBrains Mono',monospace}
.tool-card.ok{border-left-color:var(--green)} .tool-card.err{border-left-color:var(--red)}
#thinking-row{display:none}
.thinking-dots span{display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--blue);margin:0 2px;animation:bounce .9s infinite}
.thinking-dots span:nth-child(2){animation-delay:.15s}
.thinking-dots span:nth-child(3){animation-delay:.3s}
@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
@keyframes fadeIn{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
.input-area{padding:12px 16px;border-top:1px solid var(--border);background:rgba(2,6,23,.75);backdrop-filter:var(--blur);flex-shrink:0}
.input-row{display:flex;gap:8px;align-items:flex-end;background:rgba(15,23,42,.7);border:1px solid var(--border);border-radius:var(--radius);padding:8px 10px}
.input-row:focus-within{border-color:rgba(59,130,246,.4)}
#chat-input{flex:1;background:transparent;border:none;color:var(--text);font-size:13.5px;font-family:inherit;resize:none;outline:none;line-height:1.55;max-height:120px;min-height:22px}
#chat-input::placeholder{color:var(--text-dim)}
.btn-icon{width:30px;height:30px;border-radius:7px;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:13px;transition:all .15s;flex-shrink:0}
.btn-send{background:var(--blue);color:#fff} .btn-send:hover{background:#2563eb}
.btn-mic{background:var(--surface-2);color:var(--text-muted)} .btn-mic:hover{background:var(--surface-3);color:var(--text)}
.btn-mic.active{background:rgba(239,68,68,.15);color:#f87171;border:1px solid rgba(239,68,68,.25)}
.quick-row{display:flex;gap:6px;overflow-x:auto;padding:8px 16px 0;scrollbar-width:none}
.quick-row::-webkit-scrollbar{display:none}
.qbtn{padding:4px 10px;border-radius:99px;border:1px solid var(--border);background:var(--surface-2);color:var(--text-muted);font-size:11.5px;cursor:pointer;white-space:nowrap;transition:all .15s;font-family:inherit}
.qbtn:hover{background:var(--surface-3);color:var(--text);border-color:var(--border-bright)}
.nav-section{padding:10px 8px 0;flex:1;overflow-y:auto}
.nav-item{display:flex;align-items:center;gap:9px;padding:7px 10px;border-radius:var(--radius-sm);cursor:pointer;font-size:13px;color:var(--text-muted);border:1px solid transparent;transition:all .15s;width:100%;border-radius:8px;background:none;text-align:left;font-family:inherit}
.nav-item:hover{background:rgba(148,163,184,.05);color:#cbd5e1}
.nav-item.active{background:rgba(59,130,246,.1);color:#93c5fd;border-color:rgba(59,130,246,.15)}
.nav-item i{width:16px;text-align:center;font-size:13px}
.nav-badge{margin-left:auto;font-size:10px;background:rgba(59,130,246,.2);color:#60a5fa;padding:1px 6px;border-radius:99px}
.nav-footer{padding:10px 8px;border-top:1px solid var(--border);font-size:11px;color:var(--text-dim)}
.sidebar-content{flex:1;overflow-y:auto;padding:8px}
.panel-header{padding:10px 12px;border-bottom:1px solid var(--border);font-size:11px;font-weight:600;color:var(--text-muted);letter-spacing:.06em;text-transform:uppercase;display:flex;align-items:center;gap:7px}
.mem-item{padding:8px 10px;border-radius:8px;margin-bottom:5px;cursor:pointer;border:1px solid transparent;transition:all .15s}
.mem-item:hover{background:var(--surface-2);border-color:var(--border)}
.cap-row{padding:0 12px 8px}
.cap-label{display:flex;justify-content:space-between;margin-bottom:4px}
.cap-label span:first-child{font-size:11.5px;color:var(--text-muted)}
.cap-label span:last-child{font-size:11px;color:var(--text-dim);font-family:'JetBrains Mono',monospace}
.cap-track{height:3px;background:rgba(148,163,184,.08);border-radius:99px}
.cap-fill{height:100%;border-radius:99px;transition:width .6s ease}
.status-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.online{background:var(--green);box-shadow:0 0 6px rgba(16,185,129,.5)}
.offline{background:var(--red)}
.thinking-st{background:var(--blue);animation:pulse 1.1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.mode-pill{padding:2px 9px;border-radius:99px;font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;border:1px solid}
.mode-auto{background:rgba(100,116,139,.1);color:#64748b;border-color:rgba(100,116,139,.15)}
.mode-code{background:rgba(16,185,129,.1);color:#34d399;border-color:rgba(16,185,129,.2)}
.mode-reason{background:rgba(139,92,246,.1);color:#a78bfa;border-color:rgba(139,92,246,.2)}
.mode-plan{background:rgba(245,158,11,.1);color:#fbbf24;border-color:rgba(245,158,11,.2)}
.mode-research{background:rgba(6,182,212,.1);color:#22d3ee;border-color:rgba(6,182,212,.2)}
.cmd-overlay{display:none;position:fixed;inset:0;z-index:200;background:rgba(2,6,23,.75);backdrop-filter:blur(10px);align-items:flex-start;justify-content:center;padding-top:120px}
.cmd-overlay.open{display:flex}
.cmd-box{background:rgba(15,23,42,.95);border:1px solid var(--border-bright);border-radius:16px;width:100%;max-width:540px;overflow:hidden;box-shadow:0 25px 50px rgba(0,0,0,.5)}
.cmd-input-row{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid var(--border)}
.cmd-input-row i{color:var(--text-muted)}
#cmd-input{flex:1;background:transparent;border:none;color:var(--text);font-size:14px;font-family:inherit;outline:none}
#cmd-input::placeholder{color:var(--text-dim)}
.cmd-results{max-height:300px;overflow-y:auto;padding:8px}
.cmd-item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:8px;cursor:pointer;transition:all .12s}
.cmd-item:hover,.cmd-item.sel{background:rgba(59,130,246,.1)}
.cmd-item i{width:18px;text-align:center;color:var(--text-muted);font-size:13px}
.cmd-item-label{flex:1;font-size:13px}
.cmd-item-hint{font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--text-dim);background:rgba(148,163,184,.08);padding:2px 6px;border-radius:4px}
.cmd-section{font-size:10.5px;color:var(--text-dim);padding:6px 10px 3px;letter-spacing:.06em;text-transform:uppercase}
.modal-overlay{display:none;position:fixed;inset:0;z-index:150;background:rgba(2,6,23,.75);backdrop-filter:blur(10px);align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal-box{background:rgba(15,23,42,.97);border:1px solid var(--border-bright);border-radius:18px;width:100%;max-width:440px;margin:16px;overflow:hidden}
.modal-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border)}
.modal-body{padding:20px}
.form-label{font-size:11.5px;color:var(--text-muted);font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin-bottom:8px;display:block}
.form-row{margin-bottom:18px}
.mode-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.mode-btn{padding:7px;border-radius:8px;border:1px solid var(--border);background:var(--surface-2);color:var(--text-muted);font-size:11.5px;cursor:pointer;text-align:center;transition:all .15s;font-family:inherit}
.mode-btn:hover{border-color:var(--border-bright);color:var(--text)}
.mode-btn.active{background:rgba(59,130,246,.12);color:#93c5fd;border-color:rgba(59,130,246,.25)}
.toggle-row{display:flex;align-items:center;justify-content:space-between;padding:8px 0}
.toggle{width:38px;height:20px;border-radius:99px;border:none;cursor:pointer;position:relative;transition:all .2s}
.toggle.on{background:var(--blue)} .toggle.off{background:rgba(100,116,139,.3)}
.toggle:after{content:'';position:absolute;width:14px;height:14px;border-radius:50%;background:#fff;top:3px;transition:.2s}
.toggle.on:after{right:3px} .toggle.off:after{left:3px}
.btn-danger{width:100%;padding:9px;border-radius:9px;border:1px solid rgba(239,68,68,.2);background:rgba(239,68,68,.07);color:#f87171;font-size:13px;cursor:pointer;transition:all .15s;font-family:inherit}
.btn-danger:hover{background:rgba(239,68,68,.12);border-color:rgba(239,68,68,.3)}
::-webkit-scrollbar{width:4px;height:4px} ::-webkit-scrollbar-track{background:transparent} ::-webkit-scrollbar-thumb{background:rgba(148,163,184,.15);border-radius:99px}
.skill-card{background:rgba(15,23,42,.6);border:1px solid var(--border);border-radius:9px;padding:9px 11px;margin-bottom:7px}
.skill-card h4{font-size:12.5px;margin-bottom:3px;color:#cbd5e1}
.skill-card p{font-size:11px;color:var(--text-muted);line-height:1.4}
.skill-card button{margin-top:7px;width:100%;padding:5px;border-radius:6px;border:1px solid rgba(59,130,246,.2);background:rgba(59,130,246,.08);color:#60a5fa;font-size:11px;cursor:pointer;transition:all .15s;font-family:inherit}
.skill-card button:hover{background:rgba(59,130,246,.15)}
.tool-row{display:flex;align-items:center;gap:7px;padding:5px 7px;border-radius:6px;transition:all .12s}
.tool-row:hover{background:rgba(148,163,184,.05)}
.tool-dot{width:5px;height:5px;border-radius:50%;background:var(--green);flex-shrink:0}
.log-row{font-size:11px;padding:4px 0;border-bottom:1px solid rgba(148,163,184,.04);line-height:1.4}
.log-row.err{color:#f87171} .log-row.warn{color:#fbbf24} .log-row.info{color:var(--text-muted)}
kbd{display:inline-flex;align-items:center;padding:1px 5px;border-radius:4px;background:rgba(148,163,184,.08);border:1px solid rgba(148,163,184,.12);font-size:10px;font-family:'JetBrains Mono',monospace;color:var(--text-dim)}
/* Reply, File Preview, Actions styles */
.msg-actions{display:none;position:absolute;top:-28px;right:0;gap:4px;background:rgba(15,23,42,.9);border:1px solid var(--border);border-radius:8px;padding:3px 6px}
.bubble:hover .msg-actions{display:flex}
.msg-action-btn{background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:11px;padding:2px 5px}
.msg-action-btn:hover{color:var(--text)}
.reply-preview{border-left:2px solid rgba(59,130,246,.4);padding:4px 8px;margin-bottom:6px;font-size:11px;color:var(--text-muted);background:rgba(59,130,246,.05);border-radius:0 4px 4px 0}
.file-chip{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:7px;border:1px solid var(--border);background:rgba(15,23,42,.6);cursor:pointer;font-size:11.5px;font-family:'JetBrains Mono',monospace;color:#93c5fd;margin-top:6px}
.file-chip:hover{border-color:rgba(59,130,246,.4)}
.file-modal-content pre{font-size:12.5px;line-height:1.6;color:#a5f3fc;background:none;border:none;padding:0}
/* Settings expand */
.settings-section{border-bottom:1px solid var(--border);padding-bottom:16px;margin-bottom:16px}
.settings-section:last-child{border-bottom:none;padding-bottom:0;margin-bottom:0}
.input-with-status{position:relative}
.input-with-status .status-badge{position:absolute;right:10px;top:50%;transform:translateY(-50%);font-size:11px;color:var(--green)}
</style>
</head>
<body>
<div class="bg-mesh"></div>
<div class="root">
<header class="header">
<div style="display:flex;align-items:center;gap:10px">
<span style="font-size:18px;font-weight:800;letter-spacing:-.02em;color:#f1f5f9">OpenAGI</span>
<span style="font-size:11px;background:rgba(30,41,59,.8);border:1px solid var(--border);padding:2px 8px;border-radius:99px;color:var(--text-muted);font-family:'JetBrains Mono',monospace">v5.4</span>
<span id="mode-pill" class="mode-pill mode-auto">Auto</span>
</div>
<div style="display:flex;align-items:center;gap:14px">
<button onclick="openCmd()" style="display:flex;align-items:center;gap:8px;padding:5px 12px;border-radius:8px;border:1px solid var(--border);background:rgba(15,23,42,.5);color:var(--text-muted);font-size:12px;cursor:pointer;font-family:inherit">
<i class="fa fa-search" style="font-size:11px"></i><span>Search commands</span><kbd>⌘K</kbd>
</button>
<div style="display:flex;align-items:center;gap:7px">
<div class="status-dot offline" id="status-dot"></div>
<span id="status-text" style="font-size:12px;color:var(--text-muted)">Connecting</span>
</div>
<button onclick="openSettings()" style="width:30px;height:30px;border-radius:7px;border:1px solid var(--border);background:var(--surface-2);color:var(--text-muted);cursor:pointer;transition:all .15s" onmouseover="this.style.color='#e2e8f0'" onmouseout="this.style.color='var(--text-muted)'"><i class="fa fa-gear"></i></button>
<button onclick="togglePet()" style="width:30px;height:30px;border-radius:7px;border:1px solid var(--border);background:var(--surface-2);color:var(--text-muted);cursor:pointer;transition:all .15s;margin-left:6px" title="Toggle Pet" onmouseover="this.style.color='#e2e8f0'" onmouseout="this.style.color='var(--text-muted)'"><i class="fa fa-circle" style="font-size:10px;color:#60a5fa"></i></button>
</div>
</header>
<div class="main">
<aside class="sidebar">
<div class="nav-section">
<button onclick="setTab('chat')" data-tab="chat" class="nav-item active"><i class="fa fa-comment-dots"></i> Chat</button>
<button onclick="setTab('skills')" data-tab="skills" class="nav-item"><i class="fa fa-puzzle-piece"></i> Skills <span id="skills-badge" class="nav-badge" style="display:none"></span></button>
<button onclick="setTab('goals')" data-tab="goals" class="nav-item"><i class="fa fa-bullseye"></i> Goals <span id="goals-badge" class="nav-badge" style="display:none"></span></button>
<button onclick="setTab('tools')" data-tab="tools" class="nav-item"><i class="fa fa-wrench"></i> Tools</button>
<button onclick="setTab('logs')" data-tab="logs" class="nav-item"><i class="fa fa-terminal"></i> Logs <span id="log-dot" style="display:none;margin-left:auto;width:6px;height:6px;border-radius:50%;background:var(--green)"></span></button>
</div>
<div id="sidebar-content" class="sidebar-content"></div>
<div class="nav-footer">
<div style="display:flex;justify-content:space-between;margin-bottom:4px"><span><i class="fa fa-screwdriver-wrench" style="color:var(--text-dim);margin-right:5px"></i><span id="tool-count">0</span> tools</span><span><i class="fa fa-flag" style="color:var(--text-dim);margin-right:5px"></i><span id="goal-count">0</span> goals</span></div>
</div>
</aside>
<main class="chat">
<div id="messages"></div>
<div id="thinking-row" class="msg-row" style="padding:0 20px">
<div class="avatar agent"><i class="fa fa-robot"></i></div>
<div style="display:flex;flex-direction:column;gap:4px">
<div class="thinking-dots"><span></span><span></span><span></span></div>
<div style="font-size:11px;color:var(--text-muted)">Processing <span id="elapsed"></span></div>
</div>
</div>
<div class="quick-row">
<button class="qbtn" onclick="qs('morning briefing')"><i class="fa fa-sun"></i> Morning</button>
<button class="qbtn" onclick="qs('status')"><i class="fa fa-chart-bar"></i> Status</button>
<button class="qbtn" onclick="qs('what is happening in the world')"><i class="fa fa-globe"></i> World</button>
<button class="qbtn" onclick="qs('evolve')"><i class="fa fa-dna"></i> Evolve</button>
<button class="qbtn" onclick="qs('/mode code')"><i class="fa fa-code"></i> Code</button>
<button class="qbtn" onclick="qs('/mode reason')"><i class="fa fa-brain"></i> Reason</button>
<button class="qbtn" onclick="qs('/mode plan')"><i class="fa fa-list-check"></i> Plan</button>
<button class="qbtn" onclick="qs('/mode research')"><i class="fa fa-magnifying-glass-chart"></i> Research</button>
</div>
<div class="input-area">
<div class="input-row">
<button class="btn-icon btn-mic" id="mic-btn" onclick="toggleVoice()" title="Voice input"><i class="fa fa-microphone"></i></button>
<textarea id="chat-input" placeholder="Message OpenAGI... (Enter to send)" rows="1" onkeydown="handleKey(event)" oninput="this.style.height='auto';this.style.height=Math.min(this.scrollHeight,120)+'px'"></textarea>
<button class="btn-icon btn-send" onclick="send()" title="Send message"><i class="fa fa-paper-plane"></i></button>
</div>
</div>
</main>
<aside class="rightbar">
<div class="panel-header"><i class="fa fa-clock-rotate-left"></i> Recent Memory <button onclick="loadMemory()" style="margin-left:auto;background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:12px" title="Refresh"><i class="fa fa-rotate"></i></button></div>
<div id="memory-list" style="flex:1;overflow-y:auto;padding:8px"><div style="text-align:center;color:var(--text-dim);font-size:12px;padding:20px">Loading memory...</div></div>
<div style="border-top:1px solid var(--border)"><div class="panel-header"><i class="fa fa-gauge"></i> Capabilities</div><div id="cap-list" style="padding-bottom:8px"></div></div>
</aside>
</div>
</div>
<div id="cmd-overlay" class="cmd-overlay" onclick="if(event.target===this)closeCmd()">
<div class="cmd-box">
<div class="cmd-input-row"><i class="fa fa-magnifying-glass" style="color:var(--text-muted)"></i><input id="cmd-input" placeholder="Type a command or message..." oninput="filterCmds(this.value)" onkeydown="handleCmdKey(event)"><kbd>Esc</kbd></div>
<div id="cmd-results" class="cmd-results"></div>
</div>
</div>
<div id="settings-modal" class="modal-overlay" onclick="if(event.target===this)closeSettings()">
<div class="modal-box" style="max-width:520px">
<div class="modal-header"><span style="font-size:15px;font-weight:700">Settings</span><button onclick="closeSettings()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:18px"><i class="fa fa-xmark"></i></button></div>
<div class="modal-body">
<div class="settings-section">
<div class="form-row"><label class="form-label"><i class="fa fa-bolt" style="margin-right:6px"></i>Mode</label><div class="mode-grid">
<button onclick="setMode('auto')" class="mode-btn active-mode" id="mb-auto"><i class="fa fa-bolt"></i> Auto</button>
<button onclick="setMode('code')" class="mode-btn" id="mb-code"><i class="fa fa-code"></i> Code</button>
<button onclick="setMode('reason')" class="mode-btn" id="mb-reason"><i class="fa fa-brain"></i> Reason</button>
<button onclick="setMode('plan')" class="mode-btn" id="mb-plan"><i class="fa fa-list-check"></i> Plan</button>
<button onclick="setMode('research')" class="mode-btn" id="mb-research"><i class="fa fa-flask"></i> Research</button>
</div></div>
</div>
<div class="settings-section">
<div class="form-row"><label class="form-label"><i class="fa fa-key" style="margin-right:6px"></i>API Keys</label>
<div style="display:flex;flex-direction:column;gap:8px">
<div class="input-with-status"><input id="groq-key" type="password" placeholder="GROQ_API_KEY (gsk_...)" class="glass-input" style="width:100%;padding:8px 36px 8px 10px;border-radius:8px;font-size:12.5px;font-family:'JetBrains Mono',monospace;color:var(--text)"><span id="groq-status" class="status-badge"></span></div>
<div class="input-with-status"><input id="nvidia-key" type="password" placeholder="NVIDIA_API_KEY (nvapi_...)" class="glass-input" style="width:100%;padding:8px 36px 8px 10px;border-radius:8px;font-size:12.5px;font-family:'JetBrains Mono',monospace;color:var(--text)"><span id="nvidia-status" class="status-badge"></span></div>
<div><input id="tg-token" type="password" placeholder="TELEGRAM_BOT_TOKEN (optional)" class="glass-input" style="width:100%;padding:8px 10px;border-radius:8px;font-size:12.5px;font-family:'JetBrains Mono',monospace;color:var(--text)"></div>
<button onclick="saveKeys()" style="padding:7px;border-radius:8px;border:1px solid var(--blue-border);background:var(--blue-dim);color:#60a5fa;font-size:12px;cursor:pointer;font-family:inherit"><i class="fa fa-floppy-disk" style="margin-right:5px"></i>Save Keys</button>
</div></div>
<div class="form-row"><label class="form-label"><i class="fa fa-microchip" style="margin-right:6px"></i>Model</label>
<select id="model-select" class="glass-input" style="width:100%;padding:8px 10px;border-radius:8px;font-size:13px;font-family:inherit;color:var(--text)" onchange="saveSetting('model_main',this.value)">
<option value="moonshotai/kimi-k2.5">Kimi k2.5 (Recommended)</option>
<option value="nvidia/llama-3.3-nemotron-super-49b-v1">Nemotron 49B</option>
<option value="meta/llama-3.1-70b-instruct">Llama 3.1 70B</option>
<option value="deepseek-ai/deepseek-r1">DeepSeek R1</option>
<option value="google/gemma-3-27b-it">Gemma 3 27B</option>
<option value="qwen/qwen3-235b-a22b">Qwen3 235B</option>
</select></div>
</div>
<div class="settings-section">
<div class="form-row"><label class="form-label"><i class="fa fa-location-dot" style="margin-right:6px"></i>Your City</label>
<input id="city-input" type="text" placeholder="e.g. Kuala Lumpur" class="glass-input" style="width:100%;padding:8px 10px;border-radius:8px;font-size:13px;color:var(--text);font-family:inherit" onblur="saveSetting('user_city',this.value)"></div>
<div class="form-row"><label class="form-label"><i class="fa fa-microphone" style="margin-right:6px"></i>Wake Word</label>
<input id="wake-input" type="text" placeholder="jarvis" class="glass-input" style="width:100%;padding:8px 10px;border-radius:8px;font-size:13px;color:var(--text);font-family:'JetBrains Mono',monospace" onblur="saveSetting('wake_word',this.value)"></div>
<div class="form-row"><label class="form-label"><i class="fa fa-clock-rotate-left" style="margin-right:6px"></i>History Turns</label>
<input id="history-input" type="number" min="4" max="32" value="8" class="glass-input" style="width:100%;padding:8px 10px;border-radius:8px;font-size:13px;color:var(--text);font-family:inherit" onblur="saveSetting('max_history',parseInt(this.value))"></div>
<div class="form-row"><label class="form-label"><i class="fa fa-volume-high" style="margin-right:6px"></i>TTS Language</label><select id="tts-select" style="width:100%;background:var(--surface-2);border:1px solid var(--border);color:var(--text);padding:8px 10px;border-radius:8px;font-size:13px;font-family:inherit" onchange="saveSetting('tts_lang',this.value)"><option value="auto">Auto Detect</option><option value="en">English (Ryan)</option><option value="zh">Chinese (Yunxi)</option></select></div>
</div>
<div class="settings-section">
<div class="form-row"><label class="form-label"><i class="fa fa-bell" style="margin-right:6px"></i>Proactive nudges</label><div class="toggle-row"><span style="font-size:13px;color:var(--text-muted)">Send suggestions when idle 45+ min</span><button class="toggle on" id="proactive-toggle" onclick="toggleProactive()"></button></div></div>
<div class="form-row"><label class="form-label"><i class="fa fa-circle" style="margin-right:6px"></i>Desktop Pet</label><div class="toggle-row"><span style="font-size:13px;color:var(--text-muted)">Show animated companion</span><button class="toggle on" id="pet-toggle" onclick="togglePet()"></button></div></div>
</div>
<button onclick="clearMemoryConfirm()" class="btn-danger"><i class="fa fa-trash-can" style="margin-right:7px"></i>Clear All Memory</button>
</div></div></div>
<div id="file-modal" class="modal-overlay" onclick="if(event.target===this)closeFileModal()">
<div style="background:rgba(5,12,30,.97);border:1px solid var(--border-bright);border-radius:14px;width:90%;max-width:700px;max-height:80vh;display:flex;flex-direction:column">
<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--border)">
<span id="file-modal-name" style="font-size:13px;font-family:'JetBrains Mono',monospace;color:#93c5fd"></span>
<div style="display:flex;gap:8px">
<button onclick="copyFileContent()" style="background:none;border:1px solid var(--border);color:var(--text-muted);cursor:pointer;padding:4px 10px;border-radius:6px;font-size:12px"><i class="fa fa-copy"></i> Copy</button>
<button onclick="closeFileModal()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:16px"><i class="fa fa-xmark"></i></button>
</div></div>
<pre id="file-modal-content" style="flex:1;overflow:auto;padding:16px;font-size:12.5px;font-family:'JetBrains Mono',monospace;line-height:1.6;color:#a5f3fc;margin:0"></pre>
</div></div>
<div id="reply-preview" style="display:none;align-items:center;gap:8px;padding:7px 16px;background:rgba(15,23,42,.8);border-top:1px solid var(--border);font-size:12px;color:var(--text-muted)">
<i class="fa fa-reply" style="color:var(--blue)"></i>
<span id="reply-preview-text" style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"></span>
<button onclick="cancelReply()" style="background:none;border:none;color:var(--text-muted);cursor:pointer"><i class="fa fa-xmark"></i></button>
</div>
<script>
let ws=null,currentTab='chat',currentMode='auto',logs=[],thinkStart=0,thinkTimer=null,msgCounter=0,replyingTo=null,petMood='idle';
const CMDS=[
{icon:'fa-sun',label:'Morning briefing',cmd:'morning briefing',group:'Actions'},{icon:'fa-chart-bar',label:'System status',cmd:'status',group:'Actions'},
{icon:'fa-globe',label:'World events',cmd:'what is happening in the world',group:'Actions'},{icon:'fa-dna',label:'Run evolution cycle',cmd:'evolve',group:'Actions'},
{icon:'fa-wrench',label:'Invent a tool',cmd:'invent_tool: ',group:'Actions'},
{icon:'fa-code',label:'Switch to Code mode',cmd:'/mode code',group:'Modes'},{icon:'fa-brain',label:'Switch to Reason mode',cmd:'/mode reason',group:'Modes'},{icon:'fa-list-check',label:'Switch to Plan mode',cmd:'/mode plan',group:'Modes'},{icon:'fa-flask',label:'Switch to Research mode',cmd:'/mode research',group:'Modes'},{icon:'fa-bolt',label:'Switch to Auto mode',cmd:'/mode auto',group:'Modes'},
{icon:'fa-bullseye',label:'Show my goals',cmd:'list my goals',group:'Memory'},{icon:'fa-magnifying-glass',label:'Search memory',cmd:'recall: ',group:'Memory'},
{icon:'fa-newspaper',label:'Subscribe to AI news',cmd:'subscribe me to daily AI news at 9am',group:'Subscriptions'},{icon:'fa-chart-line',label:'Investment watchlist',cmd:'get me an investment watchlist for tech',group:'Research'}
];
function connect(){ws=new WebSocket('ws://'+location.host+'/ws');ws.onopen=()=>{setStatus('online');loadHistory();refreshSidebar();loadMemory();loadCapabilities();};ws.onclose=()=>{setStatus('offline');setTimeout(connect,3000);};ws.onerror=()=>setStatus('offline');ws.onmessage=(e)=>{const d=JSON.parse(e.data);if(d.type==='thinking')showThinking();if(d.type==='response')showResponse(d.text);if(d.type==='proactive')addMsg(d.text,'agent',true);if(d.type==='log')addLog(d);if(d.type==='mode')updateModePill(d.mode);};}
function setStatus(state){const dot=document.getElementById('status-dot'),txt=document.getElementById('status-text');dot.className='status-dot '+(state==='online'?'online':state==='thinking'?'thinking-st':'offline');txt.textContent=state==='online'?'Online':'Connecting';}
function send(){const inp=document.getElementById('chat-input'),text=inp.value.trim();if(!text||!ws||ws.readyState!==WebSocket.OPEN)return;addMsg(text,'user');ws.send(JSON.stringify({type:'message',text}));inp.value='';inp.style.height='auto';detectMode(text);}
function qs(text){document.getElementById('chat-input').value=text;send();}
function handleKey(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}}
function addMsg(text,who,isProactive=false,replyTo=null){const id=`msg-${++msgCounter}`;const msgs=document.getElementById('messages'),row=document.createElement('div');row.id=id;row.className=`msg-row ${who==='user'?'user':''}`;row.dataset.text=text;const icon=who==='user'?'fa-user':'fa-robot',bubbleClass=isProactive?'proactive':who,avatarClass=isProactive?'system':who;const replyHtml=replyTo?`<div class="reply-preview"><i class="fa fa-reply" style="margin-right:4px"></i>${renderMd(replyTo.slice(0,60))}...</div>`:'';row.innerHTML=`<div class="avatar ${avatarClass}"><i class="fa ${icon}"></i></div><div class="bubble ${bubbleClass}">${replyHtml}${renderMd(text)}${renderFilePreviews(text)}<div class="msg-actions"><button class="msg-action-btn" onclick="replyToMsg('${id}')" title="Reply"><i class="fa fa-reply"></i></button><button class="msg-action-btn" onclick="copyMsg('${id}')" title="Copy"><i class="fa fa-copy"></i></button><button class="msg-action-btn" onclick="regenerate('${id}')" title="Regenerate"><i class="fa fa-rotate-right"></i></button></div></div>`;msgs.appendChild(row);msgs.scrollTop=9999;return id;}
function renderMd(text){if(!text)return'';let s=text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');s=s.replace(/```(\w*)\n?([\s\S]*?)```/g,(_,lang,code)=>`<pre><code>${code.trim().replace(/&/g,'&amp;')}</code></pre>`);s=s.replace(/`([^`]+)`/g,'<code>$1</code>');s=s.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');s=s.replace(/\n\n/g,'</p><p style="margin-top:8px" class="bubble-p">');s=s.replace(/\n/g,'<br>');if(!s.startsWith('<p'))s='<p>'+s;return s+'</p>';}
function renderFilePreviews(text){const filePattern=/(?:saved?|written?|created?|updated?)\s+(?:to\s+)?[`'"]([\w./\\-]+\.(?:py|js|ts|html|css|json|md|yaml|txt))[`'"]/gi;const matches=[...text.matchAll(filePattern)];if(!matches.length)return'';const icons={py:'fa-python',js:'fa-js',ts:'fa-code',html:'fa-html5',css:'fa-css3-alt',json:'fa-brackets-curly',md:'fa-markdown',yaml:'fa-file-code',txt:'fa-file-lines'};return `<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px">`+matches.map(m=>{const ext=m[1].split('.').pop();return `<div class="file-chip" onclick="previewFile('${m[1]}')"><i class="fa ${icons[ext]||'fa-file'}"></i>${m[1].split('/').pop()}</div>`;}).join('')+'</div>';}
function showThinking(){document.getElementById('thinking-row').style.display='flex';thinkStart=Date.now();thinkTimer=setInterval(()=>{const s=((Date.now()-thinkStart)/1000).toFixed(1);document.getElementById('elapsed').textContent=` ${s}s`;},100);document.getElementById('messages').scrollTop=9999;setStatus('thinking');}
function showResponse(text){document.getElementById('thinking-row').style.display='none';clearInterval(thinkTimer);setStatus('online');addMsg(text,'agent');}
async function loadHistory(){const data=await fetchJson('/api/history');const messages=data.messages||[];if(!messages.length){addMsg('OpenAGI v5.3 online. Memory, computer control, and self-evolution active.','agent');return;}for(const m of messages){addMsg(m.content,m.role==='user'?'user':'agent');}}
function detectMode(text){const t=text.toLowerCase();if(t.startsWith('/mode ')){updateModePill(t.split('/mode ')[1].trim());return;}if(/build.*app|create.*app|typescript|react|fastapi/.test(t))updateModePill('code');else if(/why|analyze|deeply|steelman/.test(t))updateModePill('reason');else if(/plan|strategy|roadmap/.test(t))updateModePill('plan');else if(/research|latest|news about/.test(t))updateModePill('research');else updateModePill('auto');}
const MODE_ICONS={auto:'fa-bolt',code:'fa-code',reason:'fa-brain',plan:'fa-list-check',research:'fa-flask'},MODE_LABELS={auto:'Auto',code:'Code',reason:'Reason',plan:'Plan',research:'Research'};
function updateModePill(mode){currentMode=mode;const p=document.getElementById('mode-pill');p.className=`mode-pill mode-${mode}`;p.innerHTML=`<i class="fa ${MODE_ICONS[mode]||'fa-bolt'}"></i> ${MODE_LABELS[mode]||mode}`;document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active-mode'));const mb=document.getElementById('mb-'+mode);if(mb)mb.classList.add('active-mode');}
function setMode(mode){updateModePill(mode);qs('/mode '+mode);closeSettings();}
function setTab(tab){currentTab=tab;document.querySelectorAll('[data-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.tab===tab);});renderSidebar();}
async function renderSidebar(){if(!ws||ws.readyState!==WebSocket.OPEN)return;const panel=document.getElementById('sidebar-content');if(currentTab==='chat'){panel.innerHTML='';return;}panel.innerHTML=`<div style="text-align:center;color:var(--text-dim);font-size:12px;padding:20px"><i class="fa fa-spinner fa-spin"></i></div>`;if(currentTab==='skills'){const d=await fetchJson('/api/skills');const skills=d.skills||[];document.getElementById('skills-badge').textContent=skills.length;document.getElementById('skills-badge').style.display=skills.length?'block':'none';panel.innerHTML=skills.length?skills.map(s=>`<div class="skill-card"><h4><i class="fa fa-puzzle-piece" style="color:var(--text-muted);margin-right:6px;font-size:11px"></i>${s.name}</h4><p>${s.description||'No description'}</p><button onclick="qs('run skill: ${s.name}')"><i class="fa fa-play" style="margin-right:5px;font-size:10px"></i>Run</button></div>`).join(''):'<p style="text-align:center;color:var(--text-dim);font-size:12px">No skills loaded</p>';}else if(currentTab==='goals'){const d=await fetchJson('/api/goals');const goals=d.goals||[];const pending=goals.filter(g=>g.status==='pending');document.getElementById('goals-badge').textContent=pending.length;document.getElementById('goals-badge').style.display=pending.length?'':'';panel.innerHTML=goals.length?goals.slice(0,12).map(g=>`<div style="padding:7px 9px;border-radius:8px;border:1px solid var(--border);margin-bottom:5px;background:rgba(15,23,42,.5)"><div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><div style="width:5px;height:5px;border-radius:50%;background:${g.status==='pending'?'var(--blue)':'var(--green)'}"></div><span style="font-size:10px;color:var(--text-dim)">${g.source||'user'}</span></div><p style="font-size:11.5px;color:var(--text-muted);line-height:1.4">${(g.description||'').slice(0,90)}</p></div>`).join(''):'<p style="text-align:center;color:var(--text-dim);font-size:12px">No goals</p>';}else if(currentTab==='tools'){const d=await fetchJson('/api/status');const tools=d.tool_names||[];document.getElementById('tool-count').textContent=d.tools||0;panel.innerHTML=tools.map(t=>`<div class="tool-row"><div class="tool-dot"></div><span style="font-size:11.5px;color:var(--text-muted);font-family:'JetBrains Mono',monospace">${t}</span></div>`).join('')||'<p style="text-align:center;color:var(--text-dim);font-size:12px">No tools</p>';}else if(currentTab==='logs'){document.getElementById('log-dot').style.display='none';panel.innerHTML=logs.length?logs.slice(-40).reverse().map(l=>`<div class="log-row ${l.level==='ERROR'?'err':l.level==='WARNING'?'warn':'info'}"><span style="color:var(--text-dim);font-family:'JetBrains Mono',monospace;font-size:10px">${new Date((l.ts||Date.now()/1000)*1000).toLocaleTimeString()}</span><span style="margin-left:6px">[${l.module||'?'}] ${l.msg}</span></div>`).join(''):'<p style="text-align:center;color:var(--text-dim);font-size:12px;padding:16px">No logs yet</p>';}}
async function loadMemory(){const d=await fetchJson('/api/memory/recent');const list=document.getElementById('memory-list');const events=d.events||[];list.innerHTML=events.length?events.slice(0,10).map(e=>`<div class="mem-item"><div style="font-size:10.5px;color:var(--text-dim);margin-bottom:3px;font-family:'JetBrains Mono',monospace">${(e.ts||'').slice(11,19)} ${e.event_type||''}</div><div style="font-size:12px;color:var(--text-muted);line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical">${e.content||''}</div></div>`).join(''):'<div style="text-align:center;color:var(--text-dim);font-size:12px;padding:20px">No memories yet</div>';}
async function loadCapabilities(){const d=await fetchJson('/api/capabilities');const list=document.getElementById('cap-list');const colors=['#3b82f6','#8b5cf6','#10b981','#06b6d4','#f59e0b','#ec4899','#6366f1'];list.innerHTML=Object.entries(d).slice(0,7).map(([name,score],i)=>`<div class="cap-row"><div class="cap-label"><span>${name}</span><span>${(score*100).toFixed(0)}%</span></div><div class="cap-track"><div class="cap-fill" style="width:${score*100}%;background:${colors[i%colors.length]}"></div></div></div>`).join('');}
async function refreshSidebar(){const status=await fetchJson('/api/status');document.getElementById('tool-count').textContent=status.tools||0;const goals=await fetchJson('/api/goals');const pending=(goals.goals||[]).filter(g=>g.status==='pending').length;document.getElementById('goal-count').textContent=pending;}let cmdSel=-1;
function openCmd(){document.getElementById('cmd-overlay').classList.add('open');document.getElementById('cmd-input').value='';filterCmds('');setTimeout(()=>document.getElementById('cmd-input').focus(),40);}
function closeCmd(){document.getElementById('cmd-overlay').classList.remove('open');cmdSel=-1;}
function filterCmds(q){const filtered=q?CMDS.filter(c=>c.label.toLowerCase().includes(q.toLowerCase())):CMDS;const groups={};filtered.forEach(c=>{if(!groups[c.group])groups[c.group]=[];groups[c.group].push(c);});const res=document.getElementById('cmd-results');res.innerHTML=Object.entries(groups).map(([grp,items])=>`<div class="cmd-section">${grp}</div>`+items.map(c=>`<div class="cmd-item" onclick="execCmd('${c.cmd}')"><i class="fa ${c.icon}"></i><span class="cmd-item-label">${c.label}</span><span class="cmd-item-hint">${c.cmd.slice(0,22)}</span></div>`).join('')).join('')||'<div style="text-align:center;color:var(--text-dim);font-size:12px;padding:16px">No results</div>';cmdSel=-1;}
function execCmd(cmd){closeCmd();qs(cmd);}
function handleCmdKey(e){if(e.key==='Escape'){closeCmd();return;}if(e.key==='Enter'){const v=e.target.value.trim();if(v){closeCmd();qs(v);}}}
function openSettings(){document.getElementById('settings-modal').classList.add('open');}
function closeSettings(){document.getElementById('settings-modal').classList.remove('open');}
function toggleProactive(){const t=document.getElementById('proactive-toggle');t.classList.toggle('on');t.classList.toggle('off');}
async function clearMemoryConfirm(){if(confirm('Clear all memory? This cannot be undone.')){await fetch('/api/memory/clear',{method:'POST'});loadMemory();closeSettings();}}
function replyToMsg(msgId){const row=document.getElementById(msgId);const text=row.dataset.text||'';replyingTo=text;document.getElementById('reply-preview').style.display='flex';document.getElementById('reply-preview-text').textContent=text.slice(0,80);document.getElementById('chat-input').focus();}
function cancelReply(){replyingTo=null;document.getElementById('reply-preview').style.display='none';}
function copyMsg(msgId){const row=document.getElementById(msgId);navigator.clipboard.writeText(row.dataset.text||'');}
function regenerate(msgId){const row=document.getElementById(msgId);if(row.previousElementSibling&&row.previousElementSibling.classList.contains('user')){const prevText=row.previousElementSibling.dataset.text;qs(prevText);}}
async function previewFile(path){const d=await fetchJson(`/api/file?path=${encodeURIComponent(path)}`);if(d.content){document.getElementById('file-modal-name').textContent=path;document.getElementById('file-modal-content').textContent=d.content;document.getElementById('file-modal').classList.add('open');}}
function closeFileModal(){document.getElementById('file-modal').classList.remove('open');}
function copyFileContent(){const content=document.getElementById('file-modal-content').textContent;navigator.clipboard.writeText(content);}
async function loadSettingsData(){const d=await fetchJson('/api/settings');document.getElementById('model-select').value=d.model_main||'moonshotai/kimi-k2.5';document.getElementById('city-input').value=d.user_city||'';document.getElementById('wake-input').value=d.wake_word||'jarvis';document.getElementById('history-input').value=d.max_history||8;document.getElementById('groq-status').textContent=d.groq_key_set?'set':'';document.getElementById('nvidia-status').textContent=d.nvidia_key_set?'set':'';document.getElementById('tts-select').value=d.tts_lang||'auto';updateModePill(d.mode||'auto');const pt=document.getElementById('proactive-toggle');pt.classList.toggle('on',d.proactive_enabled);pt.classList.toggle('off',!d.proactive_enabled);document.getElementById('pet-toggle').classList.toggle('on',localStorage.getItem('pet_enabled')!=='false');document.getElementById('pet-toggle').classList.toggle('off',localStorage.getItem('pet_enabled')==='false');}
async function saveKeys(){const groq=document.getElementById('groq-key').value.trim();const nvidia=document.getElementById('nvidia-key').value.trim();const tg=document.getElementById('tg-token').value.trim();const body={};if(groq)body.GROQ_API_KEY=groq;if(nvidia)body.NVIDIA_API_KEY=nvidia;if(tg)body.TELEGRAM_BOT_TOKEN=tg;if(!Object.keys(body).length)return;await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});alert('Keys saved! Restart for full effect.');}
async function saveSetting(key,value){await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({[key]:value})});}
function openSettings(){loadSettingsData();document.getElementById('settings-modal').classList.add('open');}
function toggleVoice(){const btn=document.getElementById('mic-btn');if(recognition){recognition.stop();recognition=null;btn.classList.remove('active');return;}const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){alert('Voice not supported. Use Chrome or Edge.');return;}recognition=new SR();recognition.lang='zh-CN';recognition.continuous=false;recognition.onresult=(e)=>{qs(e.results[0][0].transcript);btn.classList.remove('active');recognition=null;};recognition.onend=()=>{btn.classList.remove('active');recognition=null;};recognition.start();btn.classList.add('active');}
function addLog(l){logs.push(l);if(logs.length>300)logs.shift();if(currentTab!=='logs')document.getElementById('log-dot').style.display='';else renderSidebar();}
async function fetchJson(url){try{return await fetch(url).then(r=>r.json());}catch{return{};}}
document.addEventListener('keydown',(e)=>{if((e.metaKey||e.ctrlKey)&&e.key==='k'){e.preventDefault();openCmd();}if(e.key==='Escape'){closeCmd();closeSettings();}});
// ── PET WIDGET ─────────────────────────────────────────
const pet=document.getElementById('pet'),petCanvas=document.getElementById('pet-canvas'),ctx2=petCanvas.getContext('2d');
let petX=window.innerWidth-100,petY=window.innerHeight-100,petTargetX=petX,petTargetY=petY,petBlink=false,petFrame=0,petMoveTimer=null;pet.style.left=petX+'px';pet.style.top=petY+'px';if(localStorage.getItem('pet_enabled')==='false')pet.style.display='none';pet.style.display='none';
function drawPet(){ctx2.clearRect(0,0,52,52);petFrame++;ctx2.fillStyle='rgba(0,0,0,.2)';ctx2.beginPath();ctx2.ellipse(26,48,14,4,0,0,Math.PI*2);ctx2.fill();const grd=ctx2.createRadialGradient(26,24,2,26,24,22);if(petMood==='happy'){grd.addColorStop(0,'#60a5fa');grd.addColorStop(1,'#1d4ed8');}else if(petMood==='thinking'){grd.addColorStop(0,'#a78bfa');grd.addColorStop(1,'#5b21b6');}else{grd.addColorStop(0,'#38bdf8');grd.addColorStop(1,'#0369a1');}ctx2.beginPath();ctx2.arc(26,24,20,0,Math.PI*2);ctx2.fillStyle=grd;ctx2.fill();ctx2.beginPath();ctx2.arc(20,17,6,0,Math.PI*2);ctx2.fillStyle='rgba(255,255,255,.25)';ctx2.fill();ctx2.beginPath();ctx2.arc(26,24,20,0,Math.PI*2);ctx2.strokeStyle='rgba(255,255,255,.15)';ctx2.lineWidth=1.5;ctx2.stroke();const blinkH=petBlink?1:7,eyeY=23;ctx2.beginPath();ctx2.ellipse(20,eyeY,4,blinkH/2,0,0,Math.PI*2);ctx2.fillStyle='#f1f5f9';ctx2.fill();ctx2.beginPath();ctx2.ellipse(32,eyeY,4,blinkH/2,0,0,Math.PI*2);ctx2.fill();if(!petBlink){ctx2.beginPath();ctx2.arc(21,eyeY+1,2,0,Math.PI*2);ctx2.fillStyle='#0f172a';ctx2.fill();ctx2.beginPath();ctx2.arc(33,eyeY+1,2,0,Math.PI*2);ctx2.fill();}ctx2.beginPath();if(petMood==='happy'){ctx2.arc(26,30,6,0.1*Math.PI,0.9*Math.PI);ctx2.strokeStyle='#f1f5f9';ctx2.lineWidth=1.5;ctx2.stroke();}else if(petMood==='thinking'){const dot=Math.floor(petFrame/10)%3;for(let i=0;i<3;i++){ctx2.beginPath();ctx2.arc(36+i*6,14,i===dot?2.5:1.5,0,Math.PI*2);ctx2.fillStyle=i===dot?'#a78bfa':'rgba(167,139,250,.4)';ctx2.fill();}ctx2.beginPath();ctx2.arc(26,32,3,Math.PI*1.1,Math.PI*1.9);ctx2.strokeStyle='#c4b5fd';ctx2.lineWidth=1.5;ctx2.stroke();}else{ctx2.moveTo(22,31);ctx2.lineTo(30,31);ctx2.strokeStyle='#cbd5e1';ctx2.lineWidth=1.5;ctx2.stroke();}}
function schedulePetMove(){const delay=4000+Math.random()*8000;petMoveTimer=setTimeout(()=>{petTargetX=60+Math.random()*(window.innerWidth-160);petTargetY=60+Math.random()*(window.innerHeight-160);pet.style.left=petTargetX+'px';pet.style.top=petTargetY+'px';schedulePetMove();},delay);}
function petClick(){petMood='happy';setTimeout(()=>petMood='idle',2000);petTargetX=window.innerWidth/2-26;petTargetY=window.innerHeight/2-26;pet.style.left=petTargetX+'px';pet.style.top=petTargetY+'px';}
function setPetMood(mood){petMood=mood;}
function togglePet(){const t=document.getElementById('pet-toggle');const isOn=t.classList.contains('on');t.classList.toggle('on',!isOn);t.classList.toggle('off',isOn);document.getElementById('pet').style.display=!isOn?'block':'none';localStorage.setItem('pet_enabled',!isOn);if(!isOn){schedulePetMove();}else{clearTimeout(petMoveTimer);}}
setInterval(()=>{petBlink=true;setTimeout(()=>petBlink=false,120);},3800+Math.random()*2000);
function petLoop(){drawPet();requestAnimationFrame(petLoop);}petLoop();
const origShowThinking=showThinking;showThinking=function(){origShowThinking();setPetMood('thinking');pet.style.display=localStorage.getItem('pet_enabled')!=='false'?'block':'none';};
const origShowResponse=showResponse;showResponse=function(text){origShowResponse(text);setPetMood('happy');setTimeout(()=>setPetMood('idle'),3000);};
// Microphone HTTPS warning
function toggleVoice(){const btn=document.getElementById('mic-btn');if(location.protocol!=='https:'&&location.hostname!=='localhost'){alert('Microphone requires HTTPS.\n\nFix:\n1. Use http://localhost:8765/\n2. Run: ngrok http 8765');return;}if(recognition){recognition.stop();recognition=null;btn.classList.remove('active');return;}const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){alert('Voice not supported. Use Chrome or Edge.');return;}recognition=new SR();recognition.lang='zh-CN';recognition.continuous=false;recognition.onresult=(e)=>{qs(e.results[0][0].transcript);btn.classList.remove('active');recognition=null;};recognition.onend=()=>{btn.classList.remove('active');recognition=null;};recognition.start();btn.classList.add('active');}
connect();setInterval(loadMemory,30000);
</script>
<div id="pet" style="position:fixed;z-index:500;width:52px;height:52px;cursor:pointer;user-select:none;display:none;transition:left .4s cubic-bezier(.34,1.56,.64,1),top .4s cubic-bezier(.34,1.56,.64,1)" onclick="petClick()" title="Click me!"><canvas id="pet-canvas" width="52" height="52"></canvas></div>
</body>
</html>"""


class WebUIServer:
    def __init__(self, kernel):
        self.kernel = kernel
        self._active_ws = set()

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def push_sync(self, msg: str):
        """Thread-safe push from background threads (ProactiveEngine etc.)."""
        if not self._active_ws:
            return
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._push_to_all(msg), loop)
        except Exception as e:
            log.debug(f"push_sync failed: {e}")

    async def _push_to_all(self, message: str):
        dead = set()
        for ws in self._active_ws:
            try:
                await ws.send_json({"type": "proactive", "text": message})
            except Exception:
                dead.add(ws)
        self._active_ws -= dead

    def start(self, host="0.0.0.0", port=None):
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import HTMLResponse, JSONResponse
        import uvicorn

        self.app = FastAPI()
        port = port or int(os.getenv("WEBUI_PORT", "8765"))

        if self.kernel:
            self.kernel._webui_push = self.push_sync

        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            return HTML_V3

        @self.app.get("/api/status")
        async def status():
            tools = self.kernel.executor.registry.list_tools() if self.kernel else []
            return {"online": True, "tools": len(tools), "tool_names": tools[:35]}

        @self.app.get("/api/history")
        async def history():
            """Return conversation history from episodic memory."""
            if not self.kernel:
                return {"messages": []}
            try:
                events = self.kernel.memory.get_recent_timeline(limit=60)
                messages = []
                for e in reversed(events):  # chronological order
                    if e.get("event_type") == "user_message":
                        messages.append({"role": "user", "content": e.get("content", "")})
                    elif e.get("event_type") == "assistant_response":
                        messages.append({"role": "assistant", "content": e.get("content", "")})
                return {"messages": messages[-40:]}  # last 40 turns
            except Exception as ex:
                return {"messages": [], "error": str(ex)}

        @self.app.get("/api/skills")
        async def list_skills():
            if not self.kernel or not self.kernel.skills:
                return {"skills": []}
            skills = []
            for name in self.kernel.skills.list_skills():
                spec = self.kernel.skills.get_skill(name)
                if spec:
                    skills.append({"name": name, "description": spec.get("description", "")})
            return {"skills": skills}

        @self.app.get("/api/goals")
        async def list_goals():
            from core.goal_persistence import load_goal_queue
            return {"goals": load_goal_queue()[:20]}

        @self.app.get("/api/memory/recent")
        async def recent_memory():
            if not self.kernel:
                return {"events": []}
            try:
                events = self.kernel.memory.get_recent_timeline(limit=15)
                return {"events": events}
            except Exception as ex:
                return {"events": [], "error": str(ex)}

        @self.app.post("/api/memory/clear")
        async def clear_memory():
            if self.kernel:
                self.kernel.memory._faiss_index = None
                self.kernel.memory._faiss_texts = []
                self.kernel.memory._faiss_dirty = True
            return {"success": True}

        @self.app.get("/api/capabilities")
        async def capabilities():
            default = {"memory": 0.85, "reasoning": 0.70, "planning": 0.65,
                       "coding": 0.60, "computer": 0.45, "browser": 0.45, "evolution": 0.68}
            if self.kernel and self.kernel.meta:
                try:
                    matrix = self.kernel.meta._matrix
                    return {k: round(min(v / 5.0, 1.0), 2) for k, v in list(matrix.items())[:7]}
                except Exception:
                    pass
            return default

        @self.app.get("/api/settings")
        async def get_settings():
            """Return current settings for the UI."""
            if not self.kernel:
                return {"mode": "auto", "proactive_enabled": False, "tts_lang": "auto"}

            current_mode = "auto"
            try:
                if hasattr(self.kernel, 'mode_manager') and self.kernel.mode_manager:
                    current_mode = str(self.kernel.mode_manager.current).lower()
            except Exception:
                pass

            proactive_enabled = False
            try:
                if self.kernel.proactive and hasattr(self.kernel.proactive, '_thread'):
                    proactive_enabled = self.kernel.proactive._thread and self.kernel.proactive._thread.is_alive()
            except Exception:
                pass

            return {
                "mode": current_mode,
                "proactive_enabled": proactive_enabled,
                "tts_lang": "zh" if os.getenv("TTS_VOICE_ZH") else "en",
                "model_main": os.getenv("NVIDIA_MAIN_MODEL", "moonshotai/kimi-k2.5"),
                "model_fast": os.getenv("NVIDIA_FAST_MODEL", "moonshotai/kimi-k2.5"),
                "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
                "nvidia_key_set": bool(os.getenv("NVIDIA_API_KEY")),
                "telegram_set": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
                "user_city": os.getenv("USER_CITY", ""),
                "max_history": int(os.getenv("MAX_HISTORY_TURNS", "8")),
                "wake_word": os.getenv("WAKE_WORD", "jarvis"),
                "webui_port": int(os.getenv("WEBUI_PORT", "8765")),
                "version": "5.4.0",
            }

        @self.app.post("/api/settings")
        async def update_settings(request):
            """Apply settings changes from UI."""
            from fastapi import Request
            data = await request.json()
            changed = []
            env_path = Path(".env")

            def update_env(key: str, value: str):
                """Update a key in .env file."""
                if env_path.exists():
                    lines = env_path.read_text().splitlines()
                    found = False
                    for i, line in enumerate(lines):
                        if line.startswith(f"{key}="):
                            lines[i] = f"{key}={value}"
                            found = True
                            break
                    if not found:
                        lines.append(f"{key}={value}")
                    env_path.write_text("\n".join(lines) + "\n")
                os.environ[key] = value

            # Mode
            if "mode" in data and self.kernel and hasattr(self.kernel, 'mode_manager'):
                try:
                    from core.mode_manager import Mode
                    mode_map = {"auto": Mode.AUTO, "code": Mode.CODE, "reason": Mode.REASON,
                                "plan": Mode.PLAN, "research": Mode.RESEARCH}
                    mode_val = mode_map.get(data["mode"], Mode.AUTO)
                    self.kernel.mode_manager.set_mode(mode_val)
                    changed.append(f"mode → {data['mode']}")
                except Exception as e:
                    log.warning(f"Mode change failed: {e}")

            # Proactive toggle
            if "proactive_enabled" in data and self.kernel:
                try:
                    if self.kernel.proactive:
                        if data["proactive_enabled"]:
                            self.kernel.proactive.start()
                            changed.append("proactive → started")
                        else:
                            self.kernel.proactive.stop()
                            changed.append("proactive → stopped")
                except Exception as e:
                    log.warning(f"Proactive toggle failed: {e}")

            # API Keys (write to .env)
            for key_name in ["GROQ_API_KEY", "NVIDIA_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
                if key_name in data and data[key_name]:
                    update_env(key_name, data[key_name])
                    changed.append(f"{key_name}=***")

            # Model selection
            if "model_main" in data:
                update_env("NVIDIA_MAIN_MODEL", data["model_main"])
                from core import llm_gateway
                llm_gateway.NVIDIA_MAIN_MODEL = data["model_main"]
                llm_gateway._nvidia_client = None
                changed.append(f"model → {data['model_main']}")

            # User settings
            if "user_city" in data:
                update_env("USER_CITY", data["user_city"])
                changed.append(f"city → {data['user_city']}")
            if "max_history" in data:
                update_env("MAX_HISTORY_TURNS", str(data["max_history"]))
                import core.kernel_impl as ki
                ki.MAX_HISTORY_TURNS = int(data["max_history"])
                changed.append(f"history → {data['max_history']}")
            if "wake_word" in data:
                update_env("WAKE_WORD", data["wake_word"])
                changed.append(f"wake_word → {data['wake_word']}")
            if "tts_lang" in data:
                voice = "zh-CN-YunxiNeural" if data["tts_lang"] == "zh" else "en-GB-RyanNeural"
                if data["tts_lang"] == "zh":
                    update_env("TTS_VOICE_ZH", voice)
                else:
                    update_env("TTS_VOICE_EN", voice)
                changed.append(f"tts → {data['tts_lang']}")

            log.info(f"[SETTINGS] Updated: {changed}")
            return {"success": True, "changed": changed}

        @self.app.get("/api/file")
        async def read_file(path: str):
            """Read a file for preview."""
            try:
                safe_base = Path(".").resolve()
                target = (safe_base / path).resolve()
                # Security: only allow files within project directory
                if not str(target).startswith(str(safe_base)):
                    return {"error": "Access denied"}
                if target.exists() and target.is_file():
                    content = target.read_text(encoding="utf-8", errors="replace")
                    return {"path": path, "content": content[:50000]}
                return {"error": "File not found"}
            except Exception as e:
                return {"error": str(e)}

        @self.app.websocket("/ws")
        async def ws_endpoint(ws: WebSocket):
            await ws.accept()
            self._active_ws.add(ws)
            try:
                while True:
                    raw = await ws.receive_text()
                    data = json.loads(raw)
                    if data.get("type") == "message":
                        text = data.get("text", "").strip()
                        if not text:
                            continue
                        await ws.send_json({"type": "thinking"})
                        loop = asyncio.get_event_loop()
                        try:
                            response = await asyncio.wait_for(
                                loop.run_in_executor(None, self.kernel.process, text),
                                timeout=120
                            )
                            await ws.send_json({"type": "response", "text": response})
                        except asyncio.TimeoutError:
                            await ws.send_json({"type": "response", "text": "Request timed out after 120s."})
                        except Exception as ex:
                            await ws.send_json({"type": "response", "text": f"Error: {str(ex)[:200]}"})
            except WebSocketDisconnect:
                pass
            finally:
                self._active_ws.discard(ws)

        # Print connection info
        ip = self._get_local_ip()
        url = f"http://{ip}:{port}"
        try:
            import qrcode
            qr = qrcode.QRCode(box_size=2, border=1)
            qr.add_data(url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
        except Exception:
            pass
        log.info(f"Web UI: {url}")
        uvicorn.run(self.app, host=host, port=port, log_level="warning")
