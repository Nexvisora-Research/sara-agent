import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useStore } from '../stores/useStore';

type UIMessage = {
  id: string;
  senderName: string;
  content: string;
  isOutgoing: boolean;
};

export default function ChatView() {
  const [inputValue, setInputValue] = useState('');
  const [pendingChannels, setPendingChannels] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const plugins = useStore((s: any) => s.plugins);
  const messages = useStore((s: any) => s.messages as Record<string, UIMessage[]>);
  const currentChannel = useStore((s: any) => s.currentChannel as string | null);
  const setCurrentChannel = useStore((s: any) => s.setCurrentChannel as (channelId: string | null) => void);
  const activePlugins = plugins.filter((p: any) => p.connected);
  const selectedChannel = currentChannel ?? (activePlugins.length ? `${activePlugins[0].id}:default` : null);
  const thread = selectedChannel ? (messages[selectedChannel] || []) : [];
  const selectedPluginId = selectedChannel?.split(':')[0];
  const selectedPlugin = activePlugins.find((plugin: any) => plugin.id === selectedPluginId) || activePlugins[0];
  const isThinking = selectedChannel ? pendingChannels.has(selectedChannel) : false;
  const showChannelList = activePlugins.length > 1;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thread.length, isThinking, selectedChannel]);

  const iconFor = (id: string) => ({
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
  } as Record<string, string>)[id] || '•';

  const setChannelPending = (channelKey: string, pending: boolean) => {
    setPendingChannels((prev) => {
      const next = new Set(prev);
      if (pending) next.add(channelKey);
      else next.delete(channelKey);
      return next;
    });
  };

  const sendContent = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;
    if (!activePlugins.length) {
      console.error('No active plugins available');
      return;
    }

    setInputValue('');

    try {
      const targetPlugins = selectedChannel
        ? [selectedChannel.split(':')[0]]
        : activePlugins.map((plugin: any) => plugin.id);

      targetPlugins.forEach((pluginId: string) => setChannelPending(`${pluginId}:default`, true));
      await Promise.allSettled(
        targetPlugins.map((pluginId: string) =>
          window.saraGUI?.plugins.sendMessage(pluginId, 'default', trimmed)
        )
      );
    } catch (err) {
      console.error('Send failed:', err);
    } finally {
      const targetPlugins = selectedChannel
        ? [selectedChannel.split(':')[0]]
        : activePlugins.map((plugin: any) => plugin.id);
      targetPlugins.forEach((pluginId: string) => setChannelPending(`${pluginId}:default`, false));
    }
  };

  const handleSend = async () => sendContent(inputValue);

  return (
    <div className="flex flex-1 min-h-0 overflow-hidden bg-[#0d0d1f]">
      {showChannelList && <div className="w-60 bg-[#13132c] border-r border-white/8 flex flex-col">
        <div className="px-5 py-4 border-b border-white/8">
          <h2 className="text-lg font-semibold text-text-primary">Messages</h2>
          <p className="text-xs text-text-muted mt-1">
            {activePlugins.length} {activePlugins.length === 1 ? 'connection' : 'connections'} active
          </p>
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {activePlugins.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-text-muted">
              <p className="text-4xl mb-3">📱</p>
              <p className="text-sm">No connections yet</p>
              <p className="text-xs mt-1">Connect a plugin to start chatting</p>
            </div>
          ) : (
            activePlugins.map((p: any) => (
              <motion.div
                key={p.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className={`p-3 rounded-lg cursor-pointer transition-colors border ${
                  selectedChannel === `${p.id}:default` ? 'bg-bg-hover border-primary/30' : 'border-transparent hover:bg-bg-hover/70'
                }`}
                onClick={() => setCurrentChannel(`${p.id}:default`)}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent to-primary flex items-center justify-center text-sm font-bold text-white">
                    {iconFor(p.id)}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text-primary">{p.name}</p>
                    <p className="text-xs text-success">● Connected</p>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>}

      {/* Chat area */}
      <div className="flex-1 min-w-0 min-h-0 flex flex-col">
        {activePlugins.length > 0 ? (
          <>
            <div className="h-16 shrink-0 border-b border-white/8 bg-[#101027]/80 px-5 flex items-center justify-between">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent to-primary flex items-center justify-center text-xs font-bold text-white">
                  {selectedPlugin ? iconFor(selectedPlugin.id) : 'S'}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-text-primary truncate">{selectedPlugin?.name || 'Sara Agent'}</p>
                  <p className="text-xs text-success">{isThinking ? 'Sara is thinking...' : 'Connected'}</p>
                </div>
              </div>
              <div className="hidden md:flex items-center gap-2">
                {[
                  ['/memory', 'Memory'],
                  ['/skills', 'Skills'],
                  ['/tools', 'Tools'],
                  ['/features', 'Features'],
                ].map(([command, label]) => (
                  <button
                    key={command}
                    onClick={() => sendContent(command)}
                    disabled={isThinking}
                    className="px-3 py-2 rounded-lg border border-white/10 text-xs text-text-secondary hover:text-text-primary hover:border-primary/50 hover:bg-primary/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-4 py-5">
              {thread.length === 0 ? (
                <div className="flex h-full items-center justify-center text-text-muted">
                  <div className="text-center">
                    <p className="text-6xl mb-4">💬</p>
                    <p className="text-lg">No messages yet</p>
                    <p className="text-sm mt-1">Send a message to start this conversation.</p>
                  </div>
                </div>
              ) : (
                <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 pb-4">
                  {thread.map((msg) => (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex w-full ${msg.isOutgoing ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[min(840px,86%)] rounded-lg px-4 py-3 text-sm leading-relaxed shadow-sm ${
                          msg.isOutgoing
                            ? 'bg-primary text-white shadow-primary/10'
                            : 'bg-[#171735] border border-white/10 text-text-primary'
                        }`}
                      >
                        <p className="text-[11px] opacity-75 mb-1">{msg.senderName}</p>
                        <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                      </div>
                    </motion.div>
                  ))}
                  <AnimatePresence>
                    {isThinking && <ThinkingBubble />}
                  </AnimatePresence>
                  <div ref={bottomRef} />
                </div>
              )}
            </div>
            <div className="shrink-0 p-4 border-t border-white/8 bg-[#101027]">
              <div className="mx-auto flex w-full max-w-5xl gap-2">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Type a message or use voice..."
                  disabled={isThinking}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSend();
                  }}
                  className="flex-1 bg-[#191936] border border-white/10 rounded-lg px-4 py-3 text-text-primary placeholder-text-muted focus:outline-none focus:border-primary transition-colors disabled:opacity-60"
                />
                <button
                  onClick={handleSend}
                  disabled={isThinking || !inputValue.trim()}
                  className="px-6 py-3 bg-primary hover:bg-primary-light disabled:bg-bg-hover disabled:text-text-muted text-white rounded-lg font-medium transition-colors"
                >
                  {isThinking ? 'Wait' : 'Send'}
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 min-h-0 flex items-center justify-center text-text-muted">
            <div className="text-center">
              <p className="text-6xl mb-4">🔌</p>
              <p className="text-lg">No plugins connected</p>
              <p className="text-sm mt-1">Click + in the sidebar to connect Telegram, Discord, etc.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ThinkingBubble() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="flex justify-start"
    >
      <div className="rounded-lg bg-[#171735] border border-white/10 px-4 py-3 shadow-sm">
        <p className="text-[11px] text-text-muted mb-2">Sara Agent</p>
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-secondary">Thinking</span>
          <span className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                animate={{ opacity: [0.25, 1, 0.25], y: [0, -3, 0] }}
                transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }}
                className="h-1.5 w-1.5 rounded-full bg-accent"
              />
            ))}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
