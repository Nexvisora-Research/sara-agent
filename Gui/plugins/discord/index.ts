import { BasePlugin } from '../base/BasePlugin';
import { IPluginManifest, Contact, Channel, Message } from '../base/IPlugin';

export class DiscordPlugin extends BasePlugin {
  readonly manifest: IPluginManifest = {
    id: 'discord',
    name: 'Discord',
    version: '1.0.0',
    description: 'Connect to Discord via API',
    author: 'Sara Agent',
    icon: 'discord',
    platforms: ['win', 'linux', 'android', 'mac'],
    requiredCredentials: [
      { key: 'token', label: 'Discord Token', sensitive: true, placeholder: 'Your Discord Token' },
    ],
    permissions: ['messages.read', 'messages.send', 'guilds.read', 'channels.read'],
  };

  private connected = false;

  async connect(credentials: Record<string, string>): Promise<boolean> {
    this.setStatus('connecting');
    try {
      const { token } = credentials;
      if (!token) throw new Error('Missing token');
      console.log('Connecting to Discord...');
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

export default new DiscordPlugin();
