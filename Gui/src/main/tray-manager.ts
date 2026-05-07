import { Tray, Menu, nativeImage } from 'electron';
import path from 'path';

interface TrayCallbacks {
  onShow: () => void;
  onVoiceToggle: () => void;
  onQuit: () => void;
}

export function createTray(callbacks: TrayCallbacks): Tray | null {
  try {
    const iconPath = path.join(__dirname, '../../resources/tray-icon.png');
    const icon = nativeImage.createFromPath(iconPath);
    const tray = new Tray(icon.isEmpty() ? nativeImage.createEmpty() : icon);

    const contextMenu = Menu.buildFromTemplate([
      { label: '📱 Open Sara Agent', click: callbacks.onShow },
      { type: 'separator' },
      { label: '🎤 Toggle Voice Control', click: callbacks.onVoiceToggle },
      { type: 'separator' },
      { label: '❌ Quit', click: callbacks.onQuit },
    ]);

    tray.setToolTip('Sara Agent — Messenger');
    tray.setContextMenu(contextMenu);
    tray.on('double-click', callbacks.onShow);
    return tray;
  } catch {
    return null;
  }
}
