export interface IPluginManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  icon: string;
  platforms: ('win' | 'linux' | 'android' | 'mac')[];
  requiredCredentials: Array<{ key: string; label: string; sensitive: boolean; placeholder?: string }>;
  permissions: string[];
}

export interface Contact {
  id: string;
  name: string;
  avatar?: string;
  status?: 'online' | 'offline' | 'away' | 'busy';
  lastSeen?: Date;
}

export interface Channel {
  id: string;
  name: string;
  type: 'dm' | 'group' | 'channel' | 'voice';
  unreadCount?: number;
  lastMessage?: string;
  avatar?: string;
}

export interface Message {
  id: string;
  channelId: string;
  senderId: string;
  senderName: string;
  content: string;
  timestamp: Date;
  isOutgoing: boolean;
  attachments?: Array<{ type: string; url: string; name?: string }>;
}

export interface IPlugin {
  readonly manifest: IPluginManifest;
  readonly status: 'disconnected' | 'connecting' | 'connected' | 'error';

  init(): Promise<void>;
  connect(credentials: Record<string, string>): Promise<boolean>;
  disconnect(): Promise<void>;
  destroy(): Promise<void>;

  getContacts(): Promise<Contact[]>;
  getChannels(): Promise<Channel[]>;
  sendMessage(channelId: string, content: string): Promise<string>;
  editMessage(messageId: string, newContent: string): Promise<boolean>;
  deleteMessage(messageId: string): Promise<boolean>;

  onMessage(callback: (message: Message) => void): void;
  onError(callback: (error: Error) => void): void;
  onStatusChange(callback: (status: string) => void): void;
}
