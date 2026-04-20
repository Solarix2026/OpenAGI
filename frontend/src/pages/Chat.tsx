// Chat Page with V2 animations, skeleton loading, and enhanced UX
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from '../context/WebSocketContext';
import { CommandPalette, Icon, Icons } from '../components/common';
import { AnimatedMessage, MessageSkeleton } from '../components/chat/AnimatedMessage';
import { SkeletonChat } from '../components/skeleton';
import { useSessionStore } from '../store/appStore';
import { useToast } from '../hooks/useToast';
import styles from './Chat.module.css';

interface ChatMessage {
  id: string;
  type: 'user' | 'agent' | 'system' | 'thinking';
  content: string;
  timestamp: number;
}

interface QuickAction {
  icon: string;
  label: string;
  cmd: string;
  color?: string;
}

const quickActions: QuickAction[] = [
  { icon: Icons.sun, label: 'Morning', cmd: 'morning briefing', color: 'orange' },
  { icon: Icons.dashboard, label: 'Status', cmd: 'status', color: 'blue' },
  { icon: Icons.globe, label: 'World', cmd: 'what is happening in the world', color: 'green' },
  { icon: Icons.dna, label: 'Evolve', cmd: 'evolve', color: 'purple' },
  { icon: Icons.code, label: 'Code', cmd: '/mode code', color: 'cyan' },
  { icon: Icons.brain, label: 'Reason', cmd: '/mode reason', color: 'yellow' },
];

// Page transition variants
const pageVariants = {
  initial: { opacity: 0, x: 20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -20 },
};

// Message list animation
const messageListVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
};

const messageItemVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.3,
      ease: [0.4, 0, 0.2, 1],
    },
  },
};

export function ChatPage() {
  const { send: wsSend, isConnected, messages: wsMessages } = useWebSocket();
  const { addToast } = useToast();
  const {
    addSession,
    currentSessionId,
    addMessage,
  } = useSessionStore();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isCmdOpen, setIsCmdOpen] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [showSkeleton, setShowSkeleton] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const inputAreaRef = useRef<HTMLDivElement>(null);
  const hasInitialized = useRef(false);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Initialize session with skeleton loading
  useEffect(() => {
    if (!hasInitialized.current) {
      hasInitialized.current = true;
      // Simulate loading for skeleton
      const skeletonTimer = setTimeout(() => setShowSkeleton(false), 800);

      // Create new session if none exists
      if (!currentSessionId) {
        addSession({
          id: `session-${Date.now()}`,
          title: 'New Conversation',
        });
      }

      return () => clearTimeout(skeletonTimer);
    }
  }, [addSession, currentSessionId]);

  // Load messages from current session
  useEffect(() => {
    if (currentSessionId) {
      const session = useSessionStore.getState().sessions.find(s => s.id === currentSessionId);
      if (session && session.messages.length > 0) {
        // Convert stored messages to ChatMessage format
        const loadedMessages: ChatMessage[] = session.messages.map((msg) => ({
          id: `${msg.role}-${msg.timestamp}`,
          type: msg.role === 'user' ? 'user' : 'agent',
          content: msg.content,
          timestamp: msg.timestamp,
        }));
        setMessages(loadedMessages);
        // Scroll to bottom after loading messages
        setTimeout(() => scrollToBottom(), 100);
      }
    }
  }, [currentSessionId, scrollToBottom]);

  // Handle WebSocket messages
  useEffect(() => {
    if (wsMessages.length === 0) return;

    const lastMsg = wsMessages[wsMessages.length - 1];

    if (lastMsg.type === 'thinking') {
      setIsLoading(true);
      // Add thinking indicator
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.type !== 'thinking');
        return [...filtered, {
          id: `thinking-${Date.now()}`,
          type: 'thinking',
          content: '',
          timestamp: Date.now(),
        }];
      });
    } else if (lastMsg.type === 'response') {
      setIsLoading(false);
      setIsTyping(true);
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.type !== 'thinking');
        return [...filtered, {
          id: `msg-${Date.now()}`,
          type: 'agent',
          content: lastMsg.text || '',
          timestamp: Date.now(),
        }];
      });

      // Store message in session
      if (currentSessionId && lastMsg.text) {
        addMessage(currentSessionId, {
          role: 'assistant',
          content: lastMsg.text,
        });
      }

      setTimeout(() => setIsTyping(false), 500);
    }
  }, [wsMessages, currentSessionId, addMessage]);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text || !isConnected || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: text,
      timestamp: Date.now(),
    };

    // Optimistic UI: immediately show user message
    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    // Store user message
    if (currentSessionId) {
      addMessage(currentSessionId, {
        role: 'user',
        content: text,
      });
    }

    wsSend(text);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const target = e.currentTarget;
    target.style.height = 'auto';
    target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
  };

  const handleRegenerate = (messageId: string) => {
    addToast('Regenerating response...', 'info');
    // Could implement regeneration logic here
  };

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    addToast('Message copied to clipboard', 'success');
  };

  const handleDelete = (messageId: string) => {
    // Optimistic delete - remove immediately from UI
    setMessages((prev) => prev.filter((m) => m.id !== messageId));
    addToast('Message deleted', 'success');
  };

  const handleCommand = (commandId: string) => {
    const cmdMap: Record<string, string> = {
      morning: 'morning briefing',
      status: 'status',
      world: 'what is happening in the world',
      evolve: 'evolve',
      'mode-auto': '/mode auto',
      'mode-code': '/mode code',
      'mode-reason': '/mode reason',
      'mode-plan': '/mode plan',
      'mode-research': '/mode research',
    };

    const text = cmdMap[commandId];
    if (text) {
      setInputValue(text);
      textareaRef.current?.focus();
    }
    setIsCmdOpen(false);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsCmdOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Skeleton loading state
  if (showSkeleton) {
    return <SkeletonChat />;
  }

  return (
    <motion.div
      className={styles.container}
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      {/* Command Palette */}
      <CommandPalette
        isOpen={isCmdOpen}
        onClose={() => setIsCmdOpen(false)}
        onExecute={handleCommand}
      />

      {/* Messages Area */}
      <div className={styles.messages}>
        <AnimatePresence mode="wait">
          {messages.length === 0 ? (
            <motion.div
              key="welcome"
              className={styles.welcome}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              <div className={styles.welcomeContent}>
                <motion.div
                  className={styles.welcomeIcon}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                >
                  <Icon icon={Icons.robot} size="xl" />
                </motion.div>
                <motion.h1
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  OpenAGI v5.5
                </motion.h1>
                <motion.p
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  Autonomous Intelligence System
                </motion.p>
                <motion.div
                  className={styles.welcomeHints}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <div className={styles.hint}>
                    <kbd><Icon icon={Icons.bolt} size="sm" /></kbd>
                    <span>Press <kbd>⌘K</kbd> for commands</span>
                  </div>
                  <div className={styles.hint}>
                    <kbd><Icon icon={Icons.code} size="sm" /></kbd>
                    <span>Type <code>/mode code</code> for coding</span>
                  </div>
                </motion.div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="messages"
              className={styles.messageList}
              variants={messageListVariants}
              initial="hidden"
              animate="visible"
            >
              {messages.map((msg) => (
                <motion.div key={msg.id} variants={messageItemVariants}>
                  <AnimatedMessage
                    id={msg.id}
                    type={msg.type}
                    content={msg.content}
                    timestamp={msg.timestamp}
                    isStreaming={isTyping && msg.type === 'agent'}
                    onRegenerate={() => handleRegenerate(msg.id)}
                    onCopy={() => handleCopy(msg.content)}
                    onDelete={() => handleDelete(msg.id)}
                  />
                </motion.div>
              ))}
              {isLoading && <MessageSkeleton type="agent" />}
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      <AnimatePresence>
        {messages.length === 0 && (
          <motion.div
            className={styles.quickActions}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ delay: 0.6 }}
          >
            <div className={styles.quickActionsLabel}>Quick Actions</div>
            <div className={styles.quickActionsGrid}>
              {quickActions.map((action, index) => (
                <motion.button
                  key={action.label}
                  className={styles.quickBtn}
                  style={{ '--btn-color': `var(--${action.color || 'blue'})` } as React.CSSProperties}
                  onClick={() => {
                    setInputValue(action.cmd);
                    textareaRef.current?.focus();
                  }}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.7 + index * 0.05 }}
                  whileHover={{ scale: 1.02, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <span className={styles.quickBtnIcon}>
                    <Icon icon={action.icon} size="sm" />
                  </span>
                  <span>{action.label}</span>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Area */}
      <div className={styles.inputArea} ref={inputAreaRef}>
        <motion.div
          className={styles.inputWrapper}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
        >
          <div className={styles.inputRow}>
            <motion.button
              className={styles.iconBtn}
              onClick={() => setIsCmdOpen(true)}
              title="Command palette (⌘K)"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              <Icon icon={Icons.search} size="md" />
            </motion.button>

            <textarea
              ref={textareaRef}
              className={styles.textarea}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onInput={handleInput}
              placeholder={isConnected ? 'Message OpenAGI...' : 'Connecting to server...'}
              rows={1}
              disabled={!isConnected || isLoading}
            />

            {inputValue.trim() ? (
              <motion.button
                className={`${styles.sendBtn} ${isLoading ? styles.loading : ''}`}
                onClick={handleSend}
                disabled={!isConnected || isLoading}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {isLoading ? (
                  <Icon icon={Icons.spinner} size="md" className={styles.spin} />
                ) : (
                  <Icon icon={Icons.send} size="md" />
                )}
              </motion.button>
            ) : (
              <motion.button
                className={styles.iconBtn}
                title="Voice input"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
              >
                <Icon icon={Icons.microphone} size="md" />
              </motion.button>
            )}
          </div>

          <div className={styles.inputFooter}>
            <div className={styles.status}>
              {!isConnected && (
                <span className={styles.statusOffline}>
                  <Icon icon={Icons.warning} size="sm" /> Disconnected
                </span>
              )}
            </div>
            <div className={styles.hints}>
              <span><kbd>⌘K</kbd> Command</span>
              <span><kbd>↵</kbd> Send</span>
              <span><kbd>Shift+↵</kbd> New line</span>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

export default ChatPage;
