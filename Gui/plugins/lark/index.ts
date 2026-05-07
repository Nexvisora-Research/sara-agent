import { BasePlugin } from '../base/BasePlugin';
import { IPluginManifest, Contact, Channel, Message } from '../base/IPlugin';

export class LarkPlugin extends BasePlugin {
  readonly manifest: IPluginManifest = {
    id: 'lark',
    name: 'Feishu / Lark',
    version: '1.0.0',
    description: 'Connect to Feishu/Lark for enterprise messaging',
    author: 'Sara Agent',
    icon: 'lark',
    platforms: ['win', 'linux', 'mac'],
    requiredCredentials: [
      { key: 'appId', label: 'App ID', sensitive: false, placeholder: 'Your App ID' },
      { key: 'appSecret', label: 'App Secret', sensitive: true, placeholder: 'Your App Secret' },
    ],
    permissions: ['messages.read', 'messages.send', 'contacts.read', 'groups.read'],
  };

  private connected = false;

  async connect(credentials: Record<string, string>): Promise<boolean> {
    this.setStatus('connecting');
    try {
      const { appId, appSecret } = credentials;
      if (!appId || !appSecret) throw new Error('Missing Lark credentials');
      console.log('Connecting to Lark...');
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

  async getContacts(): Promise<Contact[]> { return []; }
  async getChannels(): Promise<Channel[]> { return []; }
  async sendMessage(channelId: string, content: string): Promise<string> {
    if (!this.connected) throw new Error('Not connected');
    return this.enqueueMessage(channelId, content);
  }
}
