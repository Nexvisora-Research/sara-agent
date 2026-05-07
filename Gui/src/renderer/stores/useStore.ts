import { create } from 'zustand';

interface Plugin {
  id: string;
  name: string;
  version: string;
  connected: boolean;
  icon: string;
  manifest?: any;
}

interface StoreState {
  plugins: Plugin[];
  voiceActive: boolean;
  currentChannel: string | null;
  messages: Record<string, any[]>;
  transcript: string;
  setPlugins: (plugins: Plugin[]) => void;
  addPlugin: (plugin: Plugin) => void;
  removePlugin: (id: string) => void;
  setVoiceActive: (active: boolean) => void;
  setCurrentChannel: (channelId: string | null) => void;
  addMessage: (channelId: string, message: any) => void;
  setTranscript: (text: string) => void;
}

export const useStore = create<StoreState>((set) => ({
  plugins: [
    { id: 'telegram', name: 'Telegram', version: '1.0.0', connected: false, icon: 'telegram' },
    { id: 'discord', name: 'Discord', version: '1.0.0', connected: false, icon: 'discord' },
  ],
  voiceActive: false,
  currentChannel: null,
  messages: {},
  transcript: '',

  setPlugins: (plugins) => set({ plugins }),
  addPlugin: (plugin) => set((s) => ({ plugins: [...s.plugins, plugin] })),
  removePlugin: (id) => set((s) => ({ plugins: s.plugins.filter(p => p.id !== id) })),
  setVoiceActive: (active) => set({ voiceActive: active }),
  setCurrentChannel: (channelId) => set({ currentChannel: channelId }),
  addMessage: (channelId, message) => set((s) => ({
    messages: {
      ...s.messages,
      [channelId]: [...(s.messages[channelId] || []), message],
    },
  })),
  setTranscript: (text) => set({ transcript: text }),
}));
