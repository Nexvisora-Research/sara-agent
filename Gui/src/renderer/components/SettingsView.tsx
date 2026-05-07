import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../stores/useStore';

export default function SettingsView() {
  const [settings, setSettings] = useState<Record<string, any>>({});
  const voiceActive = useStore((s: any) => s.voiceActive);
  const setVoiceActive = useStore((s: any) => s.setVoiceActive);

  useEffect(() => {
    window.saraGUI?.settings.getAll().then(setSettings);
  }, []);

  const updateSetting = async (key: string, value: any) => {
    await window.saraGUI?.settings.set(key, value);
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const toggleVoice = () => {
    const next = !voiceActive;
    setVoiceActive(next);
    window.saraGUI?.voice.toggle(next);
  };

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="max-w-2xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
          <p className="text-text-muted mt-1">Customize your Sara Agent experience</p>
        </div>

        {/* Voice Control */}
        <Section title="🎤 Voice Control" description="Control your messenger with voice commands">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-primary">Voice Commands</p>
              <p className="text-xs text-text-muted">{voiceActive ? 'Listening...' : 'Tap to enable'}</p>
            </div>
            <button
              onClick={toggleVoice}
              className={`w-12 h-7 rounded-full transition-colors relative ${voiceActive ? 'bg-accent' : 'bg-bg-hover'}`}
            >
              <div className={`w-5 h-5 rounded-full bg-white absolute top-1 transition-all ${voiceActive ? 'left-6' : 'left-1'}`} />
            </button>
          </div>
          <div className="mt-3 p-3 bg-bg-surface rounded-lg">
            <p className="text-xs text-text-muted font-medium mb-2">Available commands:</p>
            <div className="grid grid-cols-2 gap-1 text-xs text-text-secondary">
              <span>"Open Telegram"</span>
              <span>"Open Discord"</span>
              <span>"Send message to..."</span>
              <span>"Search ..."</span>
              <span>"Disconnect"</span>
              <span>"Who is online"</span>
            </div>
          </div>
        </Section>

        {/* Appearance */}
        <Section title="🎨 Appearance" description="How Sara Agent looks">
          <div className="flex items-center justify-between">
            <p className="text-sm text-text-primary">Dark Mode</p>
            <span className="text-xs text-accent bg-accent/10 px-2 py-1 rounded-full">Always on ✨</span>
          </div>
        </Section>

        {/* Behavior */}
        <Section title="⚙️ Behavior" description="Startup and tray settings">
          <SettingRow
            label="Close to tray"
            type="toggle"
            value={settings.closeToTray !== false}
            onChange={(v) => updateSetting('closeToTray', v)}
          />
          <SettingRow
            label="Start minimized"
            type="toggle"
            value={settings.startMinimized === true}
            onChange={(v) => updateSetting('startMinimized', v)}
          />
          <SettingRow
            label="Auto-launch on startup"
            type="toggle"
            value={settings.autoLaunch === true}
            onChange={(v) => updateSetting('autoLaunch', v)}
          />
        </Section>

        {/* About */}
        <Section title="ℹ️ About">
          <div className="text-sm text-text-secondary space-y-1">
            <p><strong>Sara Agent v1.0.0</strong></p>
            <p>Cross-platform messenger with voice control</p>
            <p className="text-text-muted text-xs mt-2">Built with Electron + React + TypeScript</p>
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-2xl p-5">
      <h2 className="text-base font-semibold text-text-primary">{title}</h2>
      {description && <p className="text-xs text-text-muted mt-0.5 mb-4">{description}</p>}
      <div className="space-y-4">{children}</div>
    </motion.div>
  );
}

function SettingRow({ label, type, value, onChange }: { label: string; type: 'toggle'; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between">
      <p className="text-sm text-text-primary">{label}</p>
      <button
        onClick={() => onChange(!value)}
        className={`w-12 h-7 rounded-full transition-colors relative ${value ? 'bg-primary' : 'bg-bg-hover'}`}
      >
        <div className={`w-5 h-5 rounded-full bg-white absolute top-1 transition-all ${value ? 'left-6' : 'left-1'}`} />
      </button>
    </div>
  );
}