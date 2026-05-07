import { EventEmitter } from 'events';
import { askSara } from './sara-backend';

export class VoiceAIEngine extends EventEmitter {
  private isProcessing = false;

  constructor() {
    super();
  }

  async processVoiceCommand(transcript: string): Promise<string> {
    if (this.isProcessing) {
      console.log('Already processing a command');
      return '';
    }

    this.isProcessing = true;
    try {
      console.log(`Processing voice command: ${transcript}`);
      const response = await this.generateResponse(transcript);
      this.emit('response', response);
      return response;
    } catch (err) {
      console.error('Voice AI error:', err);
      this.emit('error', err);
      return '';
    } finally {
      this.isProcessing = false;
    }
  }

  private async generateResponse(command: string): Promise<string> {
    const saraResult = await askSara(command, {
      userId: 'gui_voice',
      channel: 'voice',
    });
    if (saraResult.reply?.trim()) {
      return saraResult.reply;
    }

    return 'Sara Agent backend is unavailable right now.';
  }

  async prepareVoiceResponse(text: string): Promise<void> {
    console.log(`Prepared response for TTS: ${text}`);
  }
}
