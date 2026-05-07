import React from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../stores/useStore';

interface Props {
  currentView: string;
  onViewChange: (view: 'chat' | 'settings') => void;
  onConnectPlugin: () => void;
}

export default function Sidebar({ currentView, onViewChange, onConnectPlugin }: Props) {
  const plugins = useStore((s: any) => s.plugins);
  const voiceActive = useStore((s: any) => s.voiceActive);
  const setVoiceActive = useStore((s: any) => s.setVoiceActive);
  const setCurrentChannel = useStore((s: any) => s.setCurrentChannel);
  const connectedPlugins = plugins.filter((p: any) => p.connected);

  const toggleVoice = () => {
    const next = !voiceActive;
    setVoiceActive(next);
    window.saraGUI?.voice.toggle(next);
  };

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

  return (
    <div className="w-16 bg-[#111129] border-r border-white/8 flex flex-col items-center py-3 gap-2">
      <button
        onClick={() => onViewChange('chat')}
        title="Messages"
        className={`w-11 h-11 rounded-lg flex items-center justify-center transition-all ${currentView === 'chat' ? 'bg-primary text-white shadow-lg shadow-primary/20' : 'text-text-muted hover:bg-bg-hover hover:text-text-primary'}`}
      >
        💬
      </button>

      <div className="w-8 h-px bg-white/10 my-1" />

      {connectedPlugins.map((p: any) => (
        <motion.div key={p.id} whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }}>
          <button
            className="relative w-11 h-11 rounded-lg flex items-center justify-center bg-bg-hover text-text-primary hover:bg-primary/20 hover:text-white transition-all"
            title={p.name}
            onClick={() => {
              onViewChange('chat');
              setCurrentChannel(`${p.id}:default`);
            }}
          >
            <span className="text-sm font-semibold">{iconFor(p.id)}</span>
            <span className="absolute right-1.5 bottom-1.5 h-2 w-2 rounded-full bg-success ring-2 ring-[#111129]" />
          </button>
        </motion.div>
      ))}

      <button
        onClick={onConnectPlugin}
        title="Configure platforms"
        className="w-11 h-11 rounded-lg flex items-center justify-center border border-dashed border-white/15 text-text-muted hover:border-primary hover:text-primary hover:bg-primary/10 transition-all"
      >
        +
      </button>

      <div className="flex-1" />

      {/* Voice */}
      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={toggleVoice}
        title="Voice"
        className={`w-11 h-11 rounded-lg flex items-center justify-center transition-all ${
          voiceActive ? 'bg-accent text-white voice-active' : 'text-text-muted hover:bg-bg-hover'
        }`}
      >
        🎤
      </motion.button>

      {/* Settings */}
      <button
        onClick={() => onViewChange('settings')}
        title="Settings"
        className={`w-11 h-11 rounded-lg flex items-center justify-center transition-all ${currentView === 'settings' ? 'bg-primary text-white shadow-lg shadow-primary/20' : 'text-text-muted hover:bg-bg-hover hover:text-text-primary'}`}
      >
        ⚙️
      </button>
    </div>
  );
}
