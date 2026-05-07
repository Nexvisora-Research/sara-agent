import { EventEmitter } from 'events';

interface VoiceCommand {
  pattern: RegExp;
  action: string;
  handler?: (...args: string[]) => void;
}

export class VoiceManager extends EventEmitter {
  private listening = false;
  private commands: VoiceCommand[] = [
    { pattern: /^open telegram$/i, action: 'open:telegram' },
    { pattern: /^open discord$/i, action: 'open:discord' },
    { pattern: /^open (\w+)$/i, action: 'open:plugin' },
    { pattern: /^send message to (.+)$/i, action: 'message:send' },
    { pattern: /^disconnect$/i, action: 'disconnect:all' },
    { pattern: /^search (.+)$/i, action: 'search' },
    { pattern: /^toggle voice$/i, action: 'voice:toggle' },
    { pattern: /^mute$/i, action: 'voice:mute' },
    { pattern: /^unmute$/i, action: 'voice:unmute' },
    { pattern: /^who is online$/i, action: 'contacts:online' },
    { pattern: /^new message$/i, action: 'message:new' },
    { pattern: /^reply (.+)$/i, action: 'message:reply' },
    { pattern: /^go to (chat|channel) (.+)$/i, action: 'navigate:chat' },
  ];

  start(): void {
    this.listening = true;
    this.emit('command', 'Voice control activated');
    console.log('🎤 Voice control started');
  }

  stop(): void {
    this.listening = false;
    this.emit('command', 'Voice control deactivated');
    console.log('🎤 Voice control stopped');
  }

  toggle(): void {
    if (this.listening) this.stop();
    else this.start();
  }

  processTranscript(text: string): void {
    if (!this.listening) return;
    this.emit('transcript', text);
    for (const cmd of this.commands) {
      const match = text.match(cmd.pattern);
      if (match) {
        this.emit('cmd', { action: cmd.action, args: match.slice(1) });
        this.emit('command', `Executing: ${cmd.action}`);
        return;
      }
    }
    this.emit('command', `Unknown command: "${text}"`);
  }

  isActive(): boolean { return this.listening; }
}
