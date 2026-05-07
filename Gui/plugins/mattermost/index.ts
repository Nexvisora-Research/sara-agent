import { BasePlugin } from '../base/BasePlugin';
import { IPluginManifest, Contact, Channel, Message } from '../base/IPlugin';

export class MattermostPlugin extends BasePlugin {
  readonly manifest: IPluginManifest = {
    id: 'mattermost',
    name: 'Mattermost',
    version: '1.0.0',
    description: 'Connect to Mattermost for team collaboration',
    author: 'Sara Agent',
    icon: 'mattermost',
    platforms: ['win', 'linux', 'mac'],
    requiredCredentials: [
      { key: 'serverUrl', label: 'Mattermost Server URL', sensitive: false, placeholder: 'https://mattermost.example.com' },
      { key: 'token', label: 'Personal Access Token', sensitive: true, placeholder: 'Your token' },
    ],
    permissions: ['messages.read', 'messages.send', 'channels.read', 'users.read'],
  };

  private connected = false;

  async connect(credentials: Record<string, string>): Promise<boolean> {
    this.setStatus('connecting');
    try {
      const { serverUrl, token } = credentials;
      if (!serverUrl || !token) throw new Error('Missing Mattermost credentials');
      console.log(`Connecting to Mattermost: ${serverUrl}`);
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
