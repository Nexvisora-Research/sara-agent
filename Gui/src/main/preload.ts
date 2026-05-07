import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('saraGUI', {
  // Platform
  platform: process.platform,

  // Window controls
  windowControls: {
    minimize: () => ipcRenderer.send('window:minimize'),
    maximize: () => ipcRenderer.send('window:maximize'),
    close: () => ipcRenderer.send('window:close'),
  },

  // Plugins
  plugins: {
    list: () => ipcRenderer.invoke('plugins:list'),
    activate: (id: string, creds: Record<string, string>) => ipcRenderer.invoke('plugins:activate', id, creds),
    deactivate: (id: string) => ipcRenderer.invoke('plugins:deactivate', id),
    sendMessage: (pluginId: string, channelId: string, content: string) => ipcRenderer.invoke('plugins:sendMessage', pluginId, channelId, content),
    onMessage: (cb: (data: unknown) => void) => ipcRenderer.on('plugin:message', (_, d) => cb(d)),
    onEvent: (cb: (data: unknown) => void) => ipcRenderer.on('plugin:event', (_, d) => cb(d)),
    onConnected: (cb: (data: unknown) => void) => ipcRenderer.on('plugin:connected', (_, d) => cb(d)),
    onDisconnected: (cb: (data: unknown) => void) => ipcRenderer.on('plugin:disconnected', (_, d) => cb(d)),
  },

  // Settings
  settings: {
    get: (key: string, defaultValue?: unknown) => ipcRenderer.invoke('settings:get', key, defaultValue),
    set: (key: string, value: unknown) => ipcRenderer.invoke('settings:set', key, value),
    getAll: () => ipcRenderer.invoke('settings:getAll'),
  },

  // Voice
  voice: {
    toggle: (enabled: boolean) => ipcRenderer.send('voice:toggle', enabled),
    onCommand: (cb: (cmd: string) => void) => ipcRenderer.on('voice:command', (_, c) => cb(c)),
    onTranscript: (cb: (text: string) => void) => ipcRenderer.on('voice:transcript', (_, t) => cb(t)),
  },

  // Voice AI
  voiceAI: {
    processCommand: (transcript: string) => ipcRenderer.invoke('voiceAI:processCommand', transcript),
    textToSpeech: (text: string) => ipcRenderer.invoke('voiceAI:textToSpeech', text),
    onResponse: (cb: (response: string) => void) => ipcRenderer.on('voiceAI:response', (_, r) => cb(r)),
    onError: (cb: (error: string) => void) => ipcRenderer.on('voiceAI:error', (_, e) => cb(e)),
  },

  // Platform info
  getPlatform: () => ipcRenderer.invoke('platform'),
});
