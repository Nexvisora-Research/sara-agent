import { EventEmitter } from 'events';
import { IPlugin, IPluginManifest, Contact, Channel, Message } from './IPlugin';

export abstract class BasePlugin extends EventEmitter implements IPlugin {
  abstract readonly manifest: IPluginManifest;
  protected _status: 'disconnected' | 'connecting' | 'connected' | 'error' = 'disconnected';
  protected messageQueue: Array<{ channelId: string; content: string; resolve: (v: string) => void; reject: (e: Error) => void }> = [];
  protected rateLimitPerSecond = 5;

  get status() { return this._status; }

  protected setStatus(s: typeof this._status) {
    this._status = s;
    this.emit('statusChange', s);
  }

  async init(): Promise<void> { /* override */ }
  abstract connect(credentials: Record<string, string>): Promise<boolean>;
  abstract disconnect(): Promise<void>;

  async destroy(): Promise<void> {
    await this.disconnect();
    this.removeAllListeners();
  }

  abstract getContacts(): Promise<Contact[]>;
  abstract getChannels(): Promise<Channel[]>;
  abstract sendMessage(channelId: string, content: string): Promise<string>;

  async editMessage(messageId: string, newContent: string): Promise<boolean> { return false; }
  async deleteMessage(messageId: string): Promise<boolean> { return false; }

  onMessage(callback: (message: Message) => void): void {
    this.on('message', callback);
  }
  onError(callback: (error: Error) => void): void {
    this.on('error', callback);
  }
  onStatusChange(callback: (status: string) => void): void {
    this.on('statusChange', callback);
  }

  protected enqueueMessage(channelId: string, content: string): Promise<string> {
    return new Promise((resolve, reject) => {
      this.messageQueue.push({ channelId, content, resolve, reject });
      this.processQueue();
    });
  }

  private async processQueue(): Promise<void> {
    if (this.messageQueue.length === 0) return;
    const msg = this.messageQueue.shift()!;
    try {
      const id = await this.sendMessage(msg.channelId, msg.content);
      msg.resolve(id);
    } catch (err) {
      msg.reject(err as Error);
    }
    setTimeout(() => this.processQueue(), 1000 / this.rateLimitPerSecond);
  }
}
