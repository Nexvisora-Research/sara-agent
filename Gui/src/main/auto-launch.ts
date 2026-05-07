import { app } from 'electron';
import Store from 'electron-store';

export function setupAutoLaunch(store: Store): void {
  const shouldAutoLaunch = store.get('autoLaunch', false) as boolean;
  app.setLoginItemSettings({
    openAtLogin: shouldAutoLaunch,
    openAsHidden: store.get('startMinimized', false) as boolean,
  });
}
