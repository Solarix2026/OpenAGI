// Modern Message Component with actions
import React, { useState } from 'react';
import styles from './Message.module.css';
import { Icon, Icons } from '../common/Icon';

export interface MessageProps {
  id: string;
  type: 'user' | 'agent' | 'system' | 'thinking';
  content: string;
  timestamp?: number;
  onCopy?: () => void;
  onReply?: () => void;
  onRegenerate?: () => void;
}

export const Message: React.FC<MessageProps> = ({
  id: _id,
  type,
  content,
  timestamp,
  onCopy,
  onReply,
  onRegenerate,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    onCopy?.();
  };

  const formatTime = (timestamp?: number) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const isUser = type === 'user';
  const isThinking = type === 'thinking';

  // Parse markdown-like content
  const renderContent = (text: string) => {
    if (!text) return '';
    // Simple markdown rendering
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br />');
    return html;
  };

  return (
    <div
      className={`${styles.row} ${isUser ? styles.userRow : ''} ${isThinking ? styles.thinkingRow : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Avatar */}
      <div className={`${styles.avatar} ${styles[type + 'Avatar']}`}>
        {type === 'user' && <Icon icon={Icons.user} size="md" />}
        {type === 'agent' && <Icon icon={Icons.robot} size="md" />}
        {type === 'system' && <Icon icon={Icons.info} size="md" />}
        {type === 'thinking' && <Icon icon={Icons.spinner} size="md" className={styles.spinning} />}
      </div>

      {/* Content */}
      <div className={styles.content}>
        {/* Header with name and time */}
        <div className={styles.header}>
          <span className={styles.name}>
            {type === 'user' ? 'You' : type === 'agent' ? 'OpenAGI' : 'System'}
          </span>
          <span className={styles.time}>{formatTime(timestamp)}</span>
        </div>

        {/* Message bubble */}
        <div className={`${styles.bubble} ${styles[type + 'Bubble']}`}>
          {isThinking ? (
            <div className={styles.thinking}>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
              <span className={styles.thinkingText}>Thinking...</span>
            </div>
          ) : (
            <div
              className={styles.text}
              dangerouslySetInnerHTML={{ __html: renderContent(content) }}
            />
          )}

          {/* Action buttons on hover */}
          {!isThinking && isHovered && (
            <div className={styles.actions}>
              <button
                className={styles.actionBtn}
                onClick={handleCopy}
                title="Copy"
              >
                <Icon icon={copied ? Icons.check : Icons.copy} size="sm" />
              </button>
              {type === 'agent' && (
                <>
                  <button
                    className={styles.actionBtn}
                    onClick={onReply}
                    title="Reply"
                  >
                    <Icon icon={Icons.reply} size="sm" />
                  </button>
                  <button
                    className={styles.actionBtn}
                    onClick={onRegenerate}
                    title="Regenerate"
                  >
                    <Icon icon={Icons.regenerate} size="sm" />
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Message;
