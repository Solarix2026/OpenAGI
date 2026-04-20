#!/usr/bin/env python3
"""Add session tables to memory_core.py schema."""

with open('core/memory_core.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''CREATE INDEX IF NOT EXISTS idx_ep_type ON episodic(event_type);
CREATE INDEX IF NOT EXISTS idx_ep_ts ON episodic(ts);
CREATE INDEX IF NOT EXISTS idx_proc_tool ON procedural(tool);
""")'''

new = '''CREATE INDEX IF NOT EXISTS idx_ep_type ON episodic(event_type);
CREATE INDEX IF NOT EXISTS idx_ep_ts ON episodic(ts);
CREATE INDEX IF NOT EXISTS idx_proc_tool ON procedural(tool);

-- Chat Sessions for multi-session history
CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    last_message_at TEXT DEFAULT (datetime('now')),
    message_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS session_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT,
    content TEXT,
    ts TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);
CREATE INDEX IF NOT EXISTS idx_session_msgs ON session_messages(session_id, ts);
""")'''

if old in content:
    content = content.replace(old, new)
    with open('core/memory_core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully added session tables to schema")
else:
    print("Could not find target string")
    # Show nearby
    idx = content.find('idx_proc_tool')
    if idx >= 0:
        print("Found at:", repr(content[idx-50:idx+100]))
