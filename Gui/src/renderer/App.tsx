import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import TitleBar from './components/TitleBar';
import Sidebar from './components/Sidebar';
import ChatView from './components/ChatView';
import SettingsView from './components/SettingsView';
import VoiceIndicator from './components/VoiceIndicator';
import { useStore } from './stores/useStore';

import PlatformConfigModal from './components/PlatformConfigModal';

declare global {
  interface Window {
    saraGUI: {
      platform: string;
      windowControls: { minimize: () => void; maximize: () => void; close: () => void };
      plugins: {
        list: () => Promise<Array<{ id: string; name: string; version: string; connected: boolean; icon: string }>>;
        activate: (id: string, creds: Record<string, string>) => Promise<boolean>;
        deactivate: (id: string) => Promise<void>;
        sendMessage: (pluginId: string, channelId: string, content: string) => Promise<string>;
        onMessage: (cb: (data: unknown) => void) => void;
        onEvent: (cb: (data: unknown) => void) => void;
        onConnected: (cb: (data: unknown) => void) => void;
        onDisconnected: (cb: (data: unknown) => void) => void;
      };
      settings: { get: (key: string, defaultValue?: unknown) => Promise<unknown>; set: (key: string, value: unknown) => Promise<void>; getAll: () => Promise<Record<string, unknown>> };
      voice: { toggle: (enabled: boolean) => void; onCommand: (cb: (cmd: string) => void) => void; onTranscript: (cb: (text: string) => void) => void };
      voiceAI: {
        processCommand: (transcript: string) => Promise<string>;
        textToSpeech: (text: string) => Promise<void>;
        onResponse: (cb: (response: string) => void) => void;
        onError: (cb: (error: string) => void) => void;
      };
      getPlatform: () => Promise<string>;
    };
  }
}

type View = 'chat' | 'settings';

export default function App() {
  const [view, setView] = useState<View>('chat');
  const [showPluginModal, setShowPluginModal] = useState(false);
  const { setPlugins, addMessage, setCurrentChannel, voiceActive } = useStore();

  useEffect(() => {
    const reloadPlugins = () => window.saraGUI.plugins.list().then(setPlugins);

    // Load plugins on mount
    reloadPlugins();

    // Listen for plugin connections
    window.saraGUI.plugins.onConnected((data: any) => {
      updatePluginStatus(data.id, true);
    });
    window.saraGUI.plugins.onDisconnected((data: any) => {
      updatePluginStatus(data.id, false);
    });

    // Voice listener
    window.saraGUI.voice.onCommand((cmd) => {
      console.log('Voice command:', cmd);
    });

    // Voice AI listeners
    window.saraGUI.voiceAI.onResponse((response: string) => {
      console.log('Voice AI response:', response);

      addMessage('sara-agent:default', {
        id: `voice-ai-${Date.now()}`,
        pluginId: 'sara-agent',
        channelId: 'default',
        senderId: 'sara',
        senderName: 'Sara Agent',
        content: response,
        timestamp: new Date().toISOString(),
        isOutgoing: false,
      });

      // Play voice response using Web Speech API
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(response);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        window.speechSynthesis.speak(utterance);
      }
    });

    window.saraGUI.voiceAI.onError((error: string) => {
      console.error('Voice AI error:', error);
    });

    // Process voice commands through AI
    window.saraGUI.voice.onTranscript((text: string) => {
      if (text && text.trim()) {
        const channelKey = 'sara-agent:default';
        addMessage(channelKey, {
          id: `voice-user-${Date.now()}`,
          pluginId: 'sara-agent',
          channelId: 'default',
          senderId: 'user',
          senderName: 'You',
          content: text,
          timestamp: new Date().toISOString(),
          isOutgoing: true,
        });
        setCurrentChannel(channelKey);
        window.saraGUI.voiceAI.processCommand(text);
      }
    });

    window.saraGUI.plugins.onMessage((raw: any) => {
      const message = raw as {
        id: string;
        pluginId: string;
        channelId: string;
        senderId: string;
        senderName: string;
        content: string;
        timestamp: string;
        isOutgoing: boolean;
      };

      const channelKey = `${message.pluginId}:${message.channelId}`;
      addMessage(channelKey, message);
      setCurrentChannel(channelKey);
    });

    function updatePluginStatus(_id: string, _connected: boolean) {
      reloadPlugins();
    }
  }, [addMessage, setCurrentChannel, setPlugins]);

  return (
    <div className="flex flex-col h-full w-full bg-bg-dark">
      <TitleBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          currentView={view}
          onViewChange={setView}
          onConnectPlugin={() => setShowPluginModal(true)}
        />
        <main className="flex-1 flex flex-col overflow-hidden">
          <AnimatePresence mode="wait">
            {view === 'chat' ? (
              <motion.div key="chat" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="flex-1 flex flex-col">
                <ChatView />
              </motion.div>
            ) : (
              <motion.div key="settings" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="flex-1 flex flex-col overflow-auto">
                <SettingsView />
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>

      <AnimatePresence>
        {voiceActive && <VoiceIndicator />}
      </AnimatePresence>

      <AnimatePresence>
        {showPluginModal && (
          <PlatformConfigModal isOpen={showPluginModal} onClose={() => setShowPluginModal(false)} />
        )}
      </AnimatePresence>
    </div>
  );
}
