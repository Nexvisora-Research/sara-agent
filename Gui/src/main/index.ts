import { app, BrowserWindow, Tray, Menu, ipcMain, nativeTheme } from 'electron';
import path from 'path';
import Store from 'electron-store';
import { PluginManager } from './plugin-manager';
import { VoiceManager } from './voice-manager';
import { createTray } from './tray-manager';
import { setupAutoLaunch } from './auto-launch';

import { VoiceAIEngine } from './voice-ai-engine';

// Suppress harmless Chromium warnings on Linux
if (process.platform === 'linux') {
  app.commandLine.appendSwitch('disable-gpu');
  app.commandLine.appendSwitch('disable-gpu-compositing');
}

const store = new Store();

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
const pluginManager = new PluginManager();
const voiceManager = new VoiceManager();
const voiceAIEngine = new VoiceAIEngine();

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200, height: 750,
    minWidth: 900, minHeight: 600,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#0f0f23',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
    icon: path.join(__dirname, '../../resources/icon.png'),
  });

  mainWindow.webContents.on('did-fail-load', (_, errorCode, errorDescription, validatedURL) => {
    console.error('Renderer failed to load:', { errorCode, errorDescription, validatedURL });
  });

  mainWindow.webContents.on('render-process-gone', (_, details) => {
    console.error('Renderer process gone:', details);
  });

  mainWindow.webContents.on('console-message', (_, level, message, line, sourceId) => {
    if (level >= 2) {
      console.error(`Renderer console [${level}] ${sourceId}:${line} - ${message}`);
    }
  });

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../../renderer/index.html'));
  }

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── IPC: Window controls ──
ipcMain.on('window:minimize', () => mainWindow?.minimize());
ipcMain.on('window:maximize', () => mainWindow?.isMaximized() ? mainWindow.unmaximize() : mainWindow?.maximize());
ipcMain.on('window:close', () => {
  const closeToTray = store.get('closeToTray', true) as boolean;
  if (closeToTray && tray) mainWindow?.hide();
  else app.quit();
});

// ── IPC: Plugins ──
ipcMain.handle('plugins:list', async () => pluginManager.listPlugins());
ipcMain.handle('plugins:activate', async (_, id: string, creds: Record<string, string>) => {
  const result = await pluginManager.activatePlugin(id, creds);
  if (result && mainWindow) {
    mainWindow.webContents.send('plugin:connected', { id, status: 'connected' });
  }
  return result;
});
ipcMain.handle('plugins:deactivate', async (_, id: string) => {
  await pluginManager.deactivatePlugin(id);
  mainWindow?.webContents.send('plugin:disconnected', { id });
});
ipcMain.handle('plugins:sendMessage', async (_, pluginId: string, channelId: string, content: string) => {
  return pluginManager.sendMessage(pluginId, channelId, content);
});

// ── IPC: Settings ──
ipcMain.handle('settings:get', (_, key: string, defaultValue?: unknown) => store.get(key, defaultValue));
ipcMain.handle('settings:set', (_, key: string, value: unknown) => store.set(key, value));
ipcMain.handle('settings:getAll', () => store.store);

// ── IPC: Voice ──
ipcMain.on('voice:toggle', (_, enabled: boolean) => {
  if (enabled) voiceManager.start();
  else voiceManager.stop();
});
voiceManager.on('command', (cmd: string) => mainWindow?.webContents.send('voice:command', cmd));
voiceManager.on('transcript', (text: string) => mainWindow?.webContents.send('voice:transcript', text));

// ── IPC: Voice AI ──
ipcMain.handle('voiceAI:processCommand', async (_, transcript: string) => {
  return voiceAIEngine.processVoiceCommand(transcript);
});
ipcMain.handle('voiceAI:textToSpeech', async (_, text: string) => {
  return voiceAIEngine.prepareVoiceResponse(text);
});
voiceAIEngine.on('response', (response: string) => {
  mainWindow?.webContents.send('voiceAI:response', response);
});
voiceAIEngine.on('error', (error: Error) => {
  mainWindow?.webContents.send('voiceAI:error', error.message);
});
// ── IPC: Platform ──
ipcMain.handle('platform', () => process.platform);

// ── App lifecycle ──
app.whenReady().then(() => {
  nativeTheme.themeSource = 'dark';
  createWindow();

  // Keep internal app chat available out of the box.
  pluginManager.activatePlugin('sara-agent', {}).then((ok) => {
    if (ok) {
      mainWindow?.webContents.send('plugin:connected', { id: 'sara-agent', status: 'connected' });
    }
  });

  tray = createTray({
    onShow: () => mainWindow?.show(),
    onVoiceToggle: () => voiceManager.toggle(),
    onQuit: () => app.quit(),
  });
  setupAutoLaunch(store);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught exception in main process:', error);
});

process.on('unhandledRejection', (reason) => {
  console.error('Unhandled rejection in main process:', reason);
});

// Forward plugin events to renderer
pluginManager.on('message', (data) => mainWindow?.webContents.send('plugin:message', data));
pluginManager.on('event', (data) => mainWindow?.webContents.send('plugin:event', data));
