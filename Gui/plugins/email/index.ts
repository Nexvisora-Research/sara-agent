import { BasePlugin } from '../base/BasePlugin';
import { IPluginManifest, Contact, Channel, Message } from '../base/IPlugin';

export class EmailPlugin extends BasePlugin {
  readonly manifest: IPluginManifest = {
    id: 'email',
    name: 'Email',
    version: '1.0.0',
    description: 'Connect to Email via IMAP/SMTP',
    author: 'Sara Agent',
    icon: 'email',
    platforms: ['win', 'linux', 'mac'],
    requiredCredentials: [
      { key: 'email', label: 'Email Address', sensitive: false, placeholder: 'user@example.com' },
      { key: 'password', label: 'Password or App Token', sensitive: true, placeholder: 'Your email password' },
      { key: 'imapServer', label: 'IMAP Server (optional)', sensitive: false, placeholder: 'imap.gmail.com' },
      { key: 'smtpServer', label: 'SMTP Server (optional)', sensitive: false, placeholder: 'smtp.gmail.com' },
    ],
    permissions: ['messages.read', 'messages.send', 'contacts.read'],
  };

  private connected = false;

  async connect(credentials: Record<string, string>): Promise<boolean> {
    this.setStatus('connecting');
    try {
      const { email, password } = credentials;
      if (!email || !password) throw new Error('Missing email or password');
      console.log(`Connecting to Email: ${email}`);
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
