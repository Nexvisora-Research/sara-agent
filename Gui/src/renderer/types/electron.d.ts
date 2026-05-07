export {};

declare global {
  interface Window {
    saraGUI: {
      platform: string;
      windowControls: {
        minimize: () => void;
        maximize: () => void;
        close: () => void;
      };
      plugins: {
        list: () => Promise<Array<{ id: string; name: string; version: string; connected: boolean; icon: string; manifest?: any }>>;
        activate: (id: string, credentials: Record<string, string>) => Promise<boolean>;
        deactivate: (id: string) => Promise<void>;
        sendMessage: (pluginId: string, channelId: string, content: string) => Promise<string>;
        onMessage: (callback: (data: unknown) => void) => void;
        onEvent: (callback: (data: unknown) => void) => void;
        onConnected: (callback: (data: unknown) => void) => void;
        onDisconnected: (callback: (data: unknown) => void) => void;
      };
      settings: {
        get: (key: string, defaultValue?: unknown) => Promise<unknown>;
        set: (key: string, value: unknown) => Promise<void>;
        getAll: () => Promise<Record<string, unknown>>;
      };
      voice: {
        toggle: (enabled: boolean) => void;
        onCommand: (callback: (command: string) => void) => void;
        onTranscript: (callback: (text: string) => void) => void;
      };
      voiceAI: {
        processCommand: (transcript: string) => Promise<string>;
        textToSpeech: (text: string) => Promise<void>;
        onResponse: (callback: (response: string) => void) => void;
        onError: (callback: (error: string) => void) => void;
      };
      getPlatform: () => Promise<string>;
    };
  }
}
