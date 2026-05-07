import { BasePlugin } from '../base/BasePlugin';
import { IPluginManifest, Contact, Channel, Message } from '../base/IPlugin';

export class OwnAppPlugin extends BasePlugin {
  readonly manifest: IPluginManifest = {
    id: 'sara-agent',
    name: 'Sara Agent',
    version: '1.0.0',
    description: 'Internal messaging within Sara Agent',
    author: 'Sara Agent',
    icon: 'app',
    platforms: ['win', 'linux', 'mac', 'android'],
    requiredCredentials: [],
    permissions: ['messages.read', 'messages.send', 'contacts.read'],
  };

  private connected = false;
  private messages: Map<string, Message[]> = new Map();

  async connect(_credentials: Record<string, string>): Promise<boolean> {
    this.setStatus('connecting');
    try {
      console.log('Connecting to Sara Agent (internal messaging)...');
      this.connected = true;
      this.setStatus('connected');
      return true;
    } catch (err) {
      this.setStatus('error');
      this.emit('error', err);
      return false;
    }
  }

  async disconnect(): Promise<void> {
    this.connected = false;
    this.setStatus('disconnected');
  }

  async getContacts(): Promise<Contact[]> {
    return [
      { id: 'sara', name: 'Sara AI Assistant', avatar: '🤖', status: 'online' },
      { id: 'user', name: 'You', avatar: '👤', status: 'online' },
    ];
  }

  async getChannels(): Promise<Channel[]> {
    return [
      { id: 'general', name: 'General Chat', type: 'group', lastMessage: 'Start chatting!' },
      { id: 'sara', name: 'Sara Assistant', type: 'dm', lastMessage: 'How can I help?' },
    ];
  }

  async sendMessage(channelId: string, content: string): Promise<string> {
    if (!this.connected) throw new Error('Not connected');
    const messageId = `msg_${Date.now()}`;
    const message: Message = {
      id: messageId,
      channelId,
      senderId: 'user',
      senderName: 'You',
      content,
      timestamp: new Date(),
      isOutgoing: true,
    };
    
    if (!this.messages.has(channelId)) {
      this.messages.set(channelId, []);
    }
    this.messages.get(channelId)?.push(message);
    this.emit('message', message);
    
    return messageId;
  }

  async editMessage(messageId: string, newContent: string): Promise<boolean> {
    for (const messages of this.messages.values()) {
      const msg = messages.find(m => m.id === messageId);
      if (msg) {
        msg.content = newContent;
        return true;
      }
    }
    return false;
  }

  async deleteMessage(messageId: string): Promise<boolean> {
    for (const messages of this.messages.values()) {
      const idx = messages.findIndex(m => m.id === messageId);
      if (idx >= 0) {
        messages.splice(idx, 1);
        return true;
      }
    }
    return false;
  }
}
