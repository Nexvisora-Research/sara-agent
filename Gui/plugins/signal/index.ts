import { BasePlugin } from '../base/BasePlugin';
import { IPluginManifest, Contact, Channel, Message } from '../base/IPlugin';

export class SignalPlugin extends BasePlugin {
  readonly manifest: IPluginManifest = {
    id: 'signal',
    name: 'Signal',
    version: '1.0.0',
    description: 'Connect to Signal for encrypted messaging',
    author: 'Sara Agent',
    icon: 'signal',
    platforms: ['win', 'linux', 'mac', 'android'],
    requiredCredentials: [
      { key: 'phone', label: 'Phone Number', sensitive: false, placeholder: '+1234567890' },
      { key: 'signalPin', label: 'Signal PIN (if enabled)', sensitive: true, placeholder: 'Optional' },
    ],
    permissions: ['messages.read', 'messages.send', 'contacts.read', 'groups.read'],
  };

  private connected = false;

  async connect(credentials: Record<string, string>): Promise<boolean> {
    this.setStatus('connecting');
    try {
      const { phone } = credentials;
      if (!phone) throw new Error('Missing phone number');
      console.log(`Connecting to Signal with phone: ${phone}`);
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
