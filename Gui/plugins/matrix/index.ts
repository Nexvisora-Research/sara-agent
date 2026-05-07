import { BasePlugin } from '../base/BasePlugin';
import { IPluginManifest, Contact, Channel, Message } from '../base/IPlugin';

export class MatrixPlugin extends BasePlugin {
  readonly manifest: IPluginManifest = {
    id: 'matrix',
    name: 'Matrix',
    version: '1.0.0',
    description: 'Connect to Matrix for decentralized messaging',
    author: 'Sara Agent',
    icon: 'matrix',
    platforms: ['win', 'linux', 'mac'],
    requiredCredentials: [
      { key: 'homeserverUrl', label: 'Homeserver URL', sensitive: false, placeholder: 'https://matrix.org' },
      { key: 'userId', label: 'User ID', sensitive: false, placeholder: '@user:example.com' },
      { key: 'password', label: 'Password', sensitive: true, placeholder: 'Your password' },
    ],
    permissions: ['messages.read', 'messages.send', 'rooms.read', 'users.read'],
  };

  private connected = false;

  async connect(credentials: Record<string, string>): Promise<boolean> {
    this.setStatus('connecting');
    try {
      const { homeserverUrl, userId, password } = credentials;
      if (!homeserverUrl || !userId || !password) throw new Error('Missing Matrix credentials');
      console.log(`Connecting to Matrix: ${homeserverUrl}`);
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
