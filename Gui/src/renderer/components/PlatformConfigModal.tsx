import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Platform {
  id: string;
  name: string;
  version: string;
  connected: boolean;
  icon: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

const platformIcons: Record<string, string> = {
  telegram: '✈',
  discord: '🎮',
  slack: '▦',
  whatsapp: '☎',
  signal: '◆',
  email: '✉',
  'twilio-sms': 'SMS',
  mattermost: 'M',
  matrix: '⌂',
  lark: '◈',
  wecom: '企',
  'sara-agent': 'S',
};

const platformDescriptions: Record<string, string> = {
  telegram: 'Connect to Telegram via MTProto',
  discord: 'Connect to Discord via API',
  slack: 'Connect to Slack for team messaging',
  whatsapp: 'Connect to WhatsApp for personal messaging',
  signal: 'Connect to Signal for encrypted messaging',
  email: 'Connect to Email via IMAP/SMTP',
  'twilio-sms': 'Send SMS via Twilio',
  mattermost: 'Connect to Mattermost for team collaboration',
  matrix: 'Connect to Matrix for decentralized messaging',
  lark: 'Connect to Feishu/Lark for enterprise messaging',
  wecom: 'Connect to WeCom for enterprise communication',
  'sara-agent': 'Internal messaging within Sara Agent',
};

export default function PlatformConfigModal({ isOpen, onClose }: Props) {
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(new Set());
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      window.saraGUI?.plugins.list().then((list) => {
        setPlatforms(list);
        const configured = new Set(list.filter(p => p.connected).map(p => p.id));
        setSelectedPlatforms(configured);
        setHighlightedIndex(0);
      });

      setTimeout(() => panelRef.current?.focus(), 0);
    }
  }, [isOpen]);

  const togglePlatform = (platformId: string) => {
    const next = new Set(selectedPlatforms);
    if (next.has(platformId)) {
      next.delete(platformId);
    } else {
      next.add(platformId);
    }
    setSelectedPlatforms(next);
  };

  const handleConfirm = async () => {
    // Activate/deactivate selected platforms
    for (const platform of platforms) {
      const isSelected = selectedPlatforms.has(platform.id);
      const isCurrentlyActive = platform.connected;

      if (isSelected && !isCurrentlyActive) {
        // Activate platform (without credentials for now)
        await window.saraGUI?.plugins.activate(platform.id, {});
      } else if (!isSelected && isCurrentlyActive) {
        // Deactivate platform
        await window.saraGUI?.plugins.deactivate(platform.id);
      }
    }
    onClose();
  };

  const handlePanelKeyDown = async (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (!platforms.length) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      onClose();
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setHighlightedIndex((prev) => (prev + 1) % platforms.length);
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setHighlightedIndex((prev) => (prev - 1 + platforms.length) % platforms.length);
      return;
    }

    if (event.key === ' ' || event.key === 'Spacebar') {
      event.preventDefault();
      const current = platforms[highlightedIndex];
      if (current) togglePlatform(current.id);
      return;
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      await handleConfirm();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="modal-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
        >
          <motion.div
            key="modal-content"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            onClick={(e) => e.stopPropagation()}
            className="fixed inset-0 flex items-center justify-center z-50"
            tabIndex={0}
            ref={panelRef}
            onKeyDown={handlePanelKeyDown}
          >
            <div className="bg-[#13132c] border border-white/10 rounded-lg w-full max-w-2xl max-h-96 overflow-y-auto shadow-2xl">
              {/* Header */}
              <div className="p-6 border-b border-white/8 sticky top-0 bg-[#13132c]">
                <h2 className="text-xl font-bold text-text-primary">Configure platforms</h2>
                <p className="text-text-muted text-sm mt-1">↑↓ navigate  SPACE toggle  ENTER confirm  ESC cancel</p>
              </div>

              {/* Platform List */}
              <div className="p-6 space-y-2">
                {platforms.map((platform, idx) => (
                  <motion.div
                    key={platform.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    onClick={() => togglePlatform(platform.id)}
                    className={`p-4 rounded-lg border cursor-pointer transition-all ${
                      idx === highlightedIndex
                        ? 'border-primary/70 bg-bg-hover/50'
                        : 'border-white/10 hover:border-primary/50 hover:bg-bg-hover/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded border border-white/20 flex items-center justify-center">
                        {selectedPlatforms.has(platform.id) ? (
                          <span className="text-success">✓</span>
                        ) : (
                          <span className="text-transparent">✓</span>
                        )}
                      </div>
                      <div className="w-9 h-9 rounded-lg bg-bg-hover flex items-center justify-center text-sm font-semibold text-text-primary">
                        {platformIcons[platform.id] || '•'}
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-text-primary">{platform.name}</p>
                        <p className="text-xs text-text-muted">{platformDescriptions[platform.id]}</p>
                      </div>
                      {platform.connected && (
                        <span className="text-xs px-2 py-1 bg-success/20 text-success rounded">configured</span>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Footer */}
              <div className="p-6 border-t border-white/5 bg-bg-card flex gap-3 justify-end sticky bottom-0">
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg border border-white/10 text-text-primary hover:border-white/20 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirm}
                  className="px-6 py-2 rounded-lg bg-primary hover:bg-primary-light text-white font-medium transition-colors"
                >
                  Confirm
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
