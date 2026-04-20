// Enhanced Chat Message with animations, thinking states, and message actions
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import styles from './AnimatedMessage.module.css';
import { Icon, Icons } from '../common';

export type MessageType = 'user' | 'agent' | 'system' | 'thinking';

interface MessageProps {
  id: string;
  type: MessageType;
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  onRegenerate?: () => void;
  onCopy?: () => void;
  onDelete?: () => void;
}

// Typing animation for message content
function TypingText({
  text,
  speed = 20,
  onComplete,
}: {
  text: string;
  speed?: number;
  onComplete?: () => void;
}) {
  const [displayText, setDisplayText] = useState('');

  useEffect(() => {
    let currentIndex = 0;
    const timer = setInterval(() => {
      if (currentIndex < text.length) {
        setDisplayText(text.slice(0, currentIndex + 1));
        currentIndex++;
      } else {
        clearInterval(timer);
        onComplete?.();
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, speed, onComplete]);

  return <span>{displayText}</span>;
}

// Thinking animation component
function ThinkingState() {
  return (
    <motion.div
      className={styles.thinking}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className={styles.thinkingIcon}>
        <div className={styles.thinkingRing} />
        <div className={styles.thinkingRing} />
        <div className={styles.thinkingRing} />
      </div>
      <div className={styles.thinkingText}>
        <span>Thinking</span>
        <motion.span
          className={styles.thinkingDots}
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          ...
        </motion.span>
      </div>
    </motion.div>
  );
}

// Message actions menu
function MessageActions({
  onCopy,
  onRegenerate,
  onDelete,
  isVisible,
}: {
  onCopy?: () => void;
  onRegenerate?: () => void;
  onDelete?: () => void;
  isVisible: boolean;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    onCopy?.();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          className={styles.messageActions}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          transition={{ duration: 0.15 }}
        >
          <button
            className={styles.actionBtn}
            onClick={handleCopy}
            title={copied ? 'Copied!' : 'Copy'}
          >
            <Icon icon={copied ? Icons.check : Icons.copy} size="sm" />
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
          {onRegenerate && (
            <button
              className={styles.actionBtn}
              onClick={onRegenerate}
              title="Regenerate"
            >
              <Icon icon={Icons.refresh} size="sm" />
              <span>Regenerate</span>
            </button>
          )}
          {onDelete && (
            <button
              className={`${styles.actionBtn} ${styles.actionBtnDanger}`}
              onClick={onDelete}
              title="Delete"
            >
              <Icon icon={Icons.trash} size="sm" />
              <span>Delete</span>
            </button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Main message component
export function AnimatedMessage({
  id,
  type,
  content,
  timestamp,
  isStreaming = false,
  onRegenerate,
  onCopy,
  onDelete,
}: MessageProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const [isTyping, setIsTyping] = useState(type === 'agent' && !isStreaming);
  const messageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (type === 'agent') {
      setIsTyping(true);
    }
  }, [type, content]);

  // Auto-scroll to message on mount
  useEffect(() => {
    messageRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, []);

  const formatTime = (ts: number) => {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    onCopy?.();
  };

  // Markdown components customization
  const markdownComponents = {
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={match[1]}
          PreTag="div"
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      ) : (
        <code className={styles.inlineCode} {...props}>
          {children}
        </code>
      );
    },
    p({ children }: any) {
      return <p className={styles.paragraph}>{children}</p>;
    },
    ul({ children }: any) {
      return <ul className={styles.list}>{children}</ul>;
    },
    ol({ children }: any) {
      return <ol className={styles.orderedList}>{children}</ol>;
    },
    li({ children }: any) {
      return <li className={styles.listItem}>{children}</li>;
    },
    h1({ children }: any) {
      return <h1 className={styles.heading1}>{children}</h1>;
    },
    h2({ children }: any) {
      return <h2 className={styles.heading2}>{children}</h2>;
    },
    h3({ children }: any) {
      return <h3 className={styles.heading3}>{children}</h3>;
    },
    blockquote({ children }: any) {
      return <blockquote className={styles.blockquote}>{children}</blockquote>;
    },
    a({ children, href }: any) {
      return (
        <a href={href} className={styles.link} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    },
    table({ children }: any) {
      return (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>{children}</table>
        </div>
      );
    },
    thead({ children }: any) {
      return <thead className={styles.tableHead}>{children}</thead>;
    },
    tbody({ children }: any) {
      return <tbody className={styles.tableBody}>{children}</tbody>;
    },
    tr({ children }: any) {
      return <tr className={styles.tableRow}>{children}</tr>;
    },
    th({ children }: any) {
      return <th className={styles.tableHeader}>{children}</th>;
    },
    td({ children }: any) {
      return <td className={styles.tableCell}>{children}</td>;
    },
  };

  if (type === 'thinking') {
    return (
      <motion.div
        className={`${styles.message} ${styles.thinkingMessage}`}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.2 }}
      >
        <div className={styles.avatar}>
          <div className={styles.avatarThinking}>
            <motion.div
              className={styles.pulseRing}
              animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
          </div>
        </div>
        <div className={styles.content}>
          <ThinkingState />
        </div>
      </motion.div>
    );
  }

  if (type === 'system') {
    return (
      <motion.div
        className={styles.systemMessage}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
      >
        <span className={styles.systemBadge}>System</span>
        <span className={styles.systemText}>{content}</span>
        <span className={styles.systemTime}>{formatTime(timestamp)}</span>
      </motion.div>
    );
  }

  const isUser = type === 'user';

  return (
    <motion.div
      ref={messageRef}
      className={`${styles.message} ${isUser ? styles.userMessage : styles.agentMessage}`}
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      onMouseEnter={() => {
        setIsHovered(true);
        setShowActions(true);
      }}
      onMouseLeave={() => {
        setIsHovered(false);
        setShowActions(false);
      }}
    >
      <div className={styles.messageInner}>
        {/* Avatar */}
        <div className={`${styles.avatar} ${isUser ? styles.userAvatar : styles.agentAvatar}`}>
          {isUser ? (
            <Icon icon={Icons.user} size="md" />
          ) : (
            <Icon icon={Icons.robot} size="md" />
          )}
        </div>

        {/* Content */}
        <div className={styles.contentWrapper}>
          {/* Header with name and time */}
          <div className={styles.messageHeader}>
            <span className={styles.authorName}>
              {isUser ? 'You' : 'OpenAGI'}
            </span>
            <span className={styles.timestamp}>{formatTime(timestamp)}</span>
          </div>

          {/* Message body */}
          <div className={`${styles.messageBody} ${isUser ? styles.userBody : styles.agentBody}`}>
            {isUser ? (
              <p className={styles.userText}>{content}</p>
            ) : (
              <div className={styles.markdownBody}>
                {isTyping ? (
                  <TypingText
                    text={content}
                    speed={15}
                    onComplete={() => setIsTyping(false)}
                  />
                ) : (
                  <ReactMarkdown components={markdownComponents}>
                    {content}
                  </ReactMarkdown>
                )}
              </div>
            )}
          </div>

          {/* Message Actions */}
          <MessageActions
            onCopy={handleCopy}
            onRegenerate={onRegenerate}
            onDelete={onDelete}
            isVisible={showActions && !isUser}
          />
        </div>
      </div>
    </motion.div>
  );
}

// Skeleton message placeholder
export function MessageSkeleton({
  type = 'agent',
}: {
  type?: 'user' | 'agent';
}) {
  return (
    <div className={`${styles.message} ${type === 'user' ? styles.userMessage : styles.agentMessage}`}>
      <div className={styles.messageInner}>
        <div className={`${styles.avatar} ${type === 'user' ? styles.userAvatar : styles.agentAvatar}`}>
          <div className={styles.skeletonAvatar} />
        </div>
        <div className={styles.contentWrapper}>
          <div className={styles.messageHeader}>
            <div className={`${styles.skeletonText} ${styles.skeletonName}`} />
          </div>
          <div className={styles.messageBody}>
            <div className={styles.skeletonLines}>
              <div className={`${styles.skeletonText} ${styles.skeletonLine1}`} />
              <div className={`${styles.skeletonText} ${styles.skeletonLine2}`} />
              <div className={`${styles.skeletonText} ${styles.skeletonLine3}`} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
