import { EventEmitter } from 'events';
import path from 'path';
import fs from 'fs';
import { IPlugin } from '../../plugins/base/IPlugin';
import { askSara } from './sara-backend';

type PluginManifest = {
  id: string;
  name: string;
  version: string;
  icon: string;
  requiredCredentials?: Array<{ key: string; label: string; sensitive: boolean; placeholder?: string }>;
};

export class PluginManager extends EventEmitter {
  private plugins = new Map<string, IPlugin>();
  private activePlugins = new Set<string>();
  private pluginDir: string;
  private readonly platformDirs = ['telegram', 'discord', 'slack', 'whatsapp', 'signal', 'email', 'twilio-sms', 'mattermost', 'matrix', 'lark', 'wecom', 'own-app'];

  constructor() {
    super();
    // Resolve to the project root's plugins directory
    // In development: src/main -> ../../plugins
    // In production: dist/src/main -> ../../../plugins
    this.pluginDir = path.resolve(__dirname, '../../..', 'plugins');
    console.log(`Plugin directory: ${this.pluginDir}`);
    this.discoverPlugins();
  }

  private discoverPlugins(): void {
    for (const dir of this.platformDirs) {
      const manifest = this.readManifest(dir);
      if (manifest) {
        console.log(`Discovered plugin: ${manifest.name} (${manifest.id})`);
      }
    }
  }

  private readManifest(dir: string): PluginManifest | null {
    const manifestPath = path.join(this.pluginDir, dir, 'manifest.json');
    if (!fs.existsSync(manifestPath)) return null;

    const raw = fs.readFileSync(manifestPath, 'utf-8');
    return JSON.parse(raw) as PluginManifest;
  }

  private getManifestById(id: string): PluginManifest | null {
    const match = this.getManifestEntryById(id);
    return match?.manifest ?? null;
  }

  private getManifestEntryById(id: string): { dir: string; manifest: PluginManifest } | null {
    for (const dir of this.platformDirs) {
      const manifest = this.readManifest(dir);
      if (manifest?.id === id) return { dir, manifest };
    }

    return null;
  }

  private getMissingCredentialKeys(manifest: PluginManifest, credentials: Record<string, string>): string[] {
    if (!manifest.requiredCredentials?.length) return [];

    return manifest.requiredCredentials
      .filter((field) => !credentials[field.key]?.trim())
      .map((field) => field.key);
  }

  async listPlugins(): Promise<Array<{ id: string; name: string; version: string; connected: boolean; icon: string }>> {
    const result: Array<{ id: string; name: string; version: string; connected: boolean; icon: string }> = [];

    for (const dir of this.platformDirs) {
      const manifest = this.readManifest(dir);
      if (manifest) {
        result.push({
          id: manifest.id,
          name: manifest.name,
          version: manifest.version,
          connected: this.activePlugins.has(manifest.id),
          icon: manifest.icon,
        });
      }
    }

    return result;
  }

  async activatePlugin(id: string, credentials: Record<string, string>): Promise<boolean> {
    try {
      const entry = this.getManifestEntryById(id);
      if (!entry) throw new Error(`Plugin ${id} not found`);

      const missing = this.getMissingCredentialKeys(entry.manifest, credentials);
      if (missing.length) {
        throw new Error(`Missing required credentials for ${id}: ${missing.join(', ')}`);
      }

      const pluginPath = path.join(this.pluginDir, entry.dir, 'index.ts');
      if (!fs.existsSync(pluginPath)) {
        // Try .js
        const jsPath = path.join(this.pluginDir, entry.dir, 'index.js');
        if (!fs.existsSync(jsPath)) throw new Error(`Plugin ${id} not found`);
      }
      // Dynamic import would happen here in real impl
      this.activePlugins.add(id);
      console.log(`Plugin ${id} activated`);
      return true;
    } catch (err) {
      console.error(`Failed to activate ${id}:`, err);
      return false;
    }
  }

  async deactivatePlugin(id: string): Promise<void> {
    this.activePlugins.delete(id);
    console.log(`Plugin ${id} deactivated`);
  }

  async sendMessage(pluginId: string, channelId: string, content: string): Promise<string> {
    if (!this.activePlugins.has(pluginId)) {
      throw new Error(`Plugin ${pluginId} is not connected`);
    }

    const messageId = `${pluginId}-${Date.now()}`;
    const outgoing = {
      id: messageId,
      pluginId,
      channelId,
      senderId: 'user',
      senderName: 'You',
      content,
      timestamp: new Date().toISOString(),
      isOutgoing: true,
    };

    this.emit('message', outgoing);

    const backend = await askSara(content, {
      userId: `gui_${pluginId}`,
      channel: pluginId,
    });

    const incoming = {
      id: `${pluginId}-reply-${Date.now()}`,
      pluginId,
      channelId,
      senderId: 'sara',
      senderName: 'Sara Agent',
      content: backend.reply || 'Sara Agent backend is unavailable right now.',
      timestamp: new Date().toISOString(),
      isOutgoing: false,
    };
    this.emit('message', incoming);

    console.log(`Sending message via ${pluginId} to ${channelId}`);
    return messageId;
  }
}
