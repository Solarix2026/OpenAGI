// Channels Page with real API data
import { useState, useEffect, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import { apiClient } from '../services/api';
import { Button, Icon, Icons } from '../components/common';
import { SkeletonList } from '../components/skeleton';
import { useToast } from '../hooks/useToast';
import styles from './Channels.module.css';

interface Channel {
  id: string;
  name: string;
  platform: 'telegram' | 'discord' | 'slack' | 'whatsapp';
  status: 'connected' | 'disconnected';
  description: string;
}

const PLATFORM_CONFIG = {
  telegram: {
    icon: Icons.send,
    color: 'var(--blue)',
    description: 'Telegram Bot integration',
  },
  discord: {
    icon: Icons.chat,
    color: 'var(--purple)',
    description: 'Discord bot support',
  },
  slack: {
    icon: Icons.listCheck,
    color: '#E01E5A',
    description: 'Slack workspace integration',
  },
  whatsapp: {
    icon: Icons.chat,
    color: 'var(--green)',
    description: 'WhatsApp Business API',
  },
};

export function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();
  const loadingStartTime = useRef<number>(0);

  // Load channel status from settings
  const loadChannels = useCallback(async () => {
    try {
      loadingStartTime.current = Date.now();
      setLoading(true);
      const settings = await apiClient.getSettings().catch(() => null);

      const channelList: Channel[] = [];

      // Check Telegram configuration
      if (settings?.telegram_set) {
        channelList.push({
          id: 'telegram',
          name: 'Telegram Bot',
          platform: 'telegram',
          status: 'connected',
          description: 'Active bot instance',
        });
      } else {
        channelList.push({
          id: 'telegram',
          name: 'Telegram Bot',
          platform: 'telegram',
          status: 'disconnected',
          description: 'Configure in Settings → API Keys',
        });
      }

      // Discord (placeholder for future)
      channelList.push({
        id: 'discord',
        name: 'Discord Bot',
        platform: 'discord',
        status: 'disconnected',
        description: 'Coming soon',
      });

      // Slack (placeholder for future)
      channelList.push({
        id: 'slack',
        name: 'Slack Workspace',
        platform: 'slack',
        status: 'disconnected',
        description: 'Coming soon',
      });

      setChannels(channelList);
    } catch (error) {
      console.error('Failed to load channels:', error);
      addToast('Failed to load channels', 'error');
    } finally {
      // Minimum loading time to prevent flash
      const elapsed = Date.now() - (loadingStartTime.current || 0);
      const minLoadingTime = 300;
      if (elapsed < minLoadingTime) {
        setTimeout(() => setLoading(false), minLoadingTime - elapsed);
      } else {
        setLoading(false);
      }
    }
  }, []); // removed addToast

  useEffect(() => {
    loadChannels();
  }, [loadChannels]);

  const handleConnect = (channelId: string) => {
    if (channelId === 'telegram') {
      addToast('Configure Telegram in Settings → API Keys', 'info');
    } else {
      addToast(`${channelId} integration coming soon`, 'info');
    }
  };

  const handleDisconnect = (channelId: string) => {
    addToast(`To disconnect ${channelId}, remove the API key from Settings`, 'info');
  };

  const getPlatformConfig = (platform: string) => {
    return PLATFORM_CONFIG[platform as keyof typeof PLATFORM_CONFIG] || {
      icon: Icons.circle,
      color: 'var(--text-muted)',
      description: 'Unknown platform',
    };
  };

  if (loading) {
    return (
      <motion.div
        className={styles.channelsContainer}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        <div className={styles.header}>
          <h1>Channels</h1>
        </div>
        <SkeletonList items={3} />
      </motion.div>
    );
  }

  return (
    <motion.div
      className={styles.channelsContainer}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className={styles.header}>
        <div>
          <h1>Channels</h1>
          <p className={styles.count}>
            {channels.filter((c) => c.status === 'connected').length} connected
          </p>
        </div>
        <Button variant="primary" size="sm" disabled>
          <Icon icon={Icons.more} size="sm" />
          Add Channel
        </Button>
      </div>

      <div className={styles.grid}>
        {channels.map((channel, index) => {
          const config = getPlatformConfig(channel.platform);
          return (
            <motion.div
              key={channel.id}
              className={`${styles.channelCard} ${channel.status === 'connected' ? styles.connected : ''}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <div className={styles.cardHeader}>
                <div
                  className={styles.platformIcon}
                  style={{ color: config.color }}
                >
                  <Icon icon={config.icon} size="lg" />
                </div>
                <div className={styles.headerInfo}>
                  <h3>{channel.name}</h3>
                  <span
                    className={`${styles.statusBadge} ${styles[channel.status]}`}
                  >
                    {channel.status === 'connected' ? '🟢' : '🔴'} {channel.status}
                  </span>
                </div>
              </div>

              <p className={styles.description}>{channel.description}</p>

              <div className={styles.actions}>
                {channel.status === 'connected' ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDisconnect(channel.id)}
                  >
                    Disconnect
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleConnect(channel.id)}
                  >
                    Connect
                  </Button>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

export default ChannelsPage;
