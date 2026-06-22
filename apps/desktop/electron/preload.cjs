const { contextBridge, ipcRenderer, webUtils } = require('electron')

contextBridge.exposeInMainWorld('SaraDesktop', {
  getConnection: profile => ipcRenderer.invoke('Sara:connection', profile),
  revalidateConnection: () => ipcRenderer.invoke('Sara:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('Sara:backend:touch', profile),
  getGatewayWsUrl: profile => ipcRenderer.invoke('Sara:gateway:ws-url', profile),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('Sara:window:openSession', sessionId, opts),
  openNewSessionWindow: () => ipcRenderer.invoke('Sara:window:openNewSession'),
  getBootProgress: () => ipcRenderer.invoke('Sara:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('Sara:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('Sara:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('Sara:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('Sara:connection-config:test', payload),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('Sara:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('Sara:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('Sara:connection-config:oauth-logout', remoteUrl),
  profile: {
    get: () => ipcRenderer.invoke('Sara:profile:get'),
    set: name => ipcRenderer.invoke('Sara:profile:set', name)
  },
  api: request => ipcRenderer.invoke('Sara:api', request),
  notify: payload => ipcRenderer.invoke('Sara:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('Sara:requestMicrophoneAccess'),
  readFileDataUrl: filePath => ipcRenderer.invoke('Sara:readFileDataUrl', filePath),
  readFileText: filePath => ipcRenderer.invoke('Sara:readFileText', filePath),
  selectPaths: options => ipcRenderer.invoke('Sara:selectPaths', options),
  writeClipboard: text => ipcRenderer.invoke('Sara:writeClipboard', text),
  saveImageFromUrl: url => ipcRenderer.invoke('Sara:saveImageFromUrl', url),
  saveImageBuffer: (data, ext) => ipcRenderer.invoke('Sara:saveImageBuffer', { data, ext }),
  saveClipboardImage: () => ipcRenderer.invoke('Sara:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('Sara:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('Sara:watchPreviewFile', url),
  stopPreviewFileWatch: id => ipcRenderer.invoke('Sara:stopPreviewFileWatch', id),
  setTitleBarTheme: payload => ipcRenderer.send('Sara:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('Sara:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('Sara:translucency', payload),
  setPreviewShortcutActive: active => ipcRenderer.send('Sara:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('Sara:openExternal', url),
  fetchLinkTitle: url => ipcRenderer.invoke('Sara:fetchLinkTitle', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('Sara:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('Sara:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('Sara:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('Sara:setting:defaultProjectDir:pick')
  },
  revealLogs: () => ipcRenderer.invoke('Sara:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('Sara:logs:recent'),
  readDir: dirPath => ipcRenderer.invoke('Sara:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('Sara:fs:gitRoot', startPath),
  worktrees: cwds => ipcRenderer.invoke('Sara:fs:worktrees', cwds),
  terminal: {
    dispose: id => ipcRenderer.invoke('Sara:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('Sara:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('Sara:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('Sara:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `Sara:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `Sara:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('Sara:close-preview-requested', listener)
    return () => ipcRenderer.removeListener('Sara:close-preview-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('Sara:open-updates', listener)
    return () => ipcRenderer.removeListener('Sara:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('Sara:deep-link', listener)
    return () => ipcRenderer.removeListener('Sara:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('Sara:deep-link-ready'),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('Sara:window-state-changed', listener)
    return () => ipcRenderer.removeListener('Sara:window-state-changed', listener)
  },
  onFocusSession: callback => {
    const listener = (_event, sessionId) => callback(sessionId)
    ipcRenderer.on('Sara:focus-session', listener)
    return () => ipcRenderer.removeListener('Sara:focus-session', listener)
  },
  onNotificationAction: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('Sara:notification-action', listener)
    return () => ipcRenderer.removeListener('Sara:notification-action', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('Sara:preview-file-changed', listener)
    return () => ipcRenderer.removeListener('Sara:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('Sara:backend-exit', listener)
    return () => ipcRenderer.removeListener('Sara:backend-exit', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('Sara:power-resume', listener)
    return () => ipcRenderer.removeListener('Sara:power-resume', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('Sara:boot-progress', listener)
    return () => ipcRenderer.removeListener('Sara:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.cjs (apps/desktop/electron/bootstrap-runner.cjs).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('Sara:bootstrap:get'),
  resetBootstrap: () => ipcRenderer.invoke('Sara:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('Sara:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('Sara:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('Sara:bootstrap:event', listener)
    return () => ipcRenderer.removeListener('Sara:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('Sara:version'),
  getRemoteDisplayReason: () => ipcRenderer.invoke('Sara:get-remote-display-reason'),
  uninstall: {
    summary: () => ipcRenderer.invoke('Sara:uninstall:summary'),
    run: mode => ipcRenderer.invoke('Sara:uninstall:run', { mode })
  },
  updates: {
    check: () => ipcRenderer.invoke('Sara:updates:check'),
    apply: opts => ipcRenderer.invoke('Sara:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('Sara:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('Sara:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('Sara:updates:progress', listener)
      return () => ipcRenderer.removeListener('Sara:updates:progress', listener)
    }
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('Sara:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('Sara:vscode-theme:search', query)
  }
})
