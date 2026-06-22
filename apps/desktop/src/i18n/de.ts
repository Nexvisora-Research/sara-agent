import { defineLocale } from './define-locale'

export const de = defineLocale({
  common: {
    apply: 'Übernehmen',
    back: 'Zurück',
    save: 'Speichern',
    saving: 'Speichern…',
    cancel: 'Abbrechen',
    change: 'Ändern',
    choose: 'Auswählen',
    clear: 'Löschen',
    close: 'Schließen',
    collapse: 'Einklappen',
    confirm: 'Bestätigen',
    connect: 'Verbinden',
    connecting: 'Verbinde',
    continue: 'Fortfahren',
    copied: 'Kopiert',
    copy: 'Kopieren',
    copyFailed: 'Kopieren fehlgeschlagen',
    delete: 'Löschen',
    docs: 'Dokumentation',
    done: 'Fertig',
    error: 'Fehler',
    failed: 'Fehlgeschlagen',
    free: 'Kostenlos',
    loading: 'Laden…',
    notSet: 'Nicht gesetzt',
    refresh: 'Aktualisieren',
    remove: 'Entfernen',
    replace: 'Ersetzen',
    retry: 'Wiederholen',
    run: 'Ausführen',
    send: 'Senden',
    set: 'Setzen',
    skip: 'Überspringen',
    update: 'Aktualisieren',
    on: 'Ein',
    off: 'Aus'
  },

  boot: {
    ready: 'Sara Desktop ist bereit',
    desktopBootFailedWithMessage: message => `Desktop-Start fehlgeschlagen: ${message}`,
    steps: {
      connectingGateway: 'Verbinde mit Live-Desktop-Gateway',
      loadingSettings: 'Lade Sara-Einstellungen',
      loadingSessions: 'Lade letzte Sitzungen',
      startingDesktopConnection: 'Starte Desktop-Verbindung',
      startingSaraDesktop: 'Starte Sara Desktop…'
    },
    errors: {
      backgroundExited: 'Sara-Hintergrundprozess wurde beendet.',
      backgroundExitedDuringStartup: 'Sara-Hintergrundprozess wurde während des Starts beendet.',
      backendStopped: 'Backend gestoppt',
      desktopBootFailed: 'Desktop-Start fehlgeschlagen',
      gatewaySignInRequired: 'Gateway-Anmeldung erforderlich',
      ipcBridgeUnavailable: 'Desktop-IPC-Brücke nicht verfügbar.'
    },
    failure: {
      title: 'Sara konnte nicht gestartet werden',
      description:
        'Das Hintergrund-Gateway wurde nicht gestartet. Versuchen Sie einen der Wiederherstellungsschritte unten. Ihre Chats und Einstellungen bleiben erhalten.',
      remoteTitle: 'Remote-Gateway-Anmeldung erforderlich',
      remoteDescription:
        'Ihre Remote-Gateway-Sitzung ist abgelaufen. Melden Sie sich erneut an. Ihre Chats und Einstellungen bleiben erhalten.',
      retry: 'Wiederholen',
      repairInstall: 'Installation reparieren',
      useLocalGateway: 'Lokales Gateway verwenden',
      openLogs: 'Logs öffnen',
      repairHint: 'Die Reparatur führt das Installationsprogramm erneut aus und kann einige Minuten dauern.',
      remoteSignInHint: 'Öffnet das Gateway-Anmeldefenster. Verwenden Sie das lokale Gateway, um zum integrierten Backend zu wechseln.',
      signedInTitle: 'Angemeldet',
      signedInMessage: 'Wiederherstellung der Verbindung zum Remote-Gateway…',
      signInIncompleteTitle: 'Anmeldung unvollständig',
      signInIncompleteMessage: 'Das Anmeldefenster wurde vor Abschluss der Authentifizierung geschlossen.',
      signInFailed: 'Anmeldung fehlgeschlagen',
      signInToRemoteGateway: 'Beim Remote-Gateway anmelden',
      signInWithProvider: provider => `Mit ${provider} anmelden`,
      identityProvider: 'Ihr Identitätsanbieter'
    }
  },

  language: {
    label: 'Sprache',
    description: 'Wählen Sie die Sprache für die Desktop-Oberfläche.',
    saving: 'Sprache wird gespeichert…',
    saveError: 'Sprachaktualisierung fehlgeschlagen',
    switchTo: 'Sprache wechseln',
    searchPlaceholder: 'Sprachen durchsuchen…',
    noResults: 'Keine Sprachen gefunden'
  },

  titlebar: {
    hideSidebar: 'Seitenleiste ausblenden',
    showSidebar: 'Seitenleiste anzeigen',
    search: 'Suchen',
    searchTitle: 'Sitzungen, Ansichten und Aktionen durchsuchen',
    swapSidebarSides: 'Seitenleisten-Seiten tauschen',
    swapSidebarSidesTitle: 'Sitzungen und Dateibrowser-Seiten tauschen',
    hideRightSidebar: 'Rechte Seitenleiste ausblenden',
    showRightSidebar: 'Rechte Seitenleiste anzeigen',
    muteHaptics: 'Haptik stumm',
    unmuteHaptics: 'Haptik aktivieren',
    openSettings: 'Einstellungen öffnen',
    openKeybinds: 'Tastenkürzel'
  },

  sidebar: {
    nav: {
      'new-session': 'Neue Sitzung',
      skills: 'Fähigkeiten & Werkzeuge',
      messaging: 'Nachrichten',
      artifacts: 'Artefakte',
      memory: 'Speicher'
    },
    searchAria: 'Sitzungen durchsuchen',
    searchPlaceholder: 'Sitzungen durchsuchen…',
    clearSearch: 'Suche löschen',
    noMatch: query => `Keine Sitzungen entsprechen „${query}".`,
    results: 'Ergebnisse',
    pinned: 'Angepinnt',
    sessions: 'Sitzungen',
    cronJobs: 'Cron-Jobs',
    loading: 'Laden…',
    loadMore: 'Mehr laden',
    row: {
      pin: 'Anpinnen',
      unpin: 'Lösen',
      copyId: 'ID kopieren',
      export: 'Exportieren',
      rename: 'Umbenennen',
      archive: 'Archivieren',
      newWindow: 'Neues Fenster',
      copyIdFailed: 'Sitzungs-ID konnte nicht kopiert werden',
      sessionRunning: 'Sitzung läuft',
      needsInput: 'Eingabe erforderlich',
      waitingForAnswer: 'Warte auf Ihre Antwort',
      renamed: 'Umbenannt',
      renameFailed: 'Umbenennung fehlgeschlagen',
      renameTitle: 'Sitzung umbenennen',
      renameDesc: 'Geben Sie einen einprägsamen Titel ein. Leer lassen zum Löschen.',
      untitledPlaceholder: 'Unbenannte Sitzung',
      ageNow: 'jetzt',
      ageDay: 'T',
      ageHour: 'Std',
      ageMin: 'Min'
    }
  },

  composer: {
    message: 'Nachricht',
    wakingProfile: profile => `${profile} wird gestartet…`,
    placeholderStarting: 'Sara wird gestartet...',
    placeholderReconnecting: 'Wiederverbinden mit Sara…',
    placeholderFollowUp: 'Weiterleitung senden',
    newSessionPlaceholders: [
      'Was bauen wir?',
      'Geben Sie Sara eine Aufgabe',
      'Was beschäftigt Sie?',
      'Beschreiben Sie, was Sie brauchen',
      'Was sollen wir anpacken?',
      'Fragen Sie alles',
      'Beginnen Sie mit einem Ziel'
    ],
    followUpPlaceholders: [
      'Weiterleitung senden',
      'Mehr Kontext hinzufügen',
      'Anfrage präzisieren',
      'Wie geht es weiter?',
      'Weiter machen',
      'Noch weiter gehen',
      'Anpassen oder fortsetzen'
    ],
    startVoice: 'Sprachkonversation starten',
    queueMessage: 'Nachricht in Warteschlange',
    steer: 'Aktuellen Lauf steuern',
    stop: 'Stopp',
    send: 'Senden',
    speaking: 'Spricht',
    transcribing: 'Transkribiert',
    thinking: 'Denkt',
    muted: 'Stumm',
    listening: 'Hört zu',
    muteMic: 'Mikrofon stumm',
    unmuteMic: 'Mikrofon aktivieren',
    stopListening: 'Zuhören beenden und senden',
    stopShort: 'Stopp',
    endConversation: 'Sprachkonversation beenden',
    endShort: 'Ende',
    attachLabel: 'Anhängen',
    files: 'Dateien…',
    folder: 'Ordner…',
    images: 'Bilder…',
    pasteImage: 'Bild einfügen',
    url: 'URL…',
    promptSnippets: 'Prompt-Schnipsel…',
    dropFiles: 'Dateien zum Anhängen ablegen',
    dropSession: 'Ablegen, um diesen Chat zu verknüpfen',
    snippetsTitle: 'Prompt-Schnipsel',
    snippetsDesc: 'Wählen Sie einen Start-Prompt für den Composer.',
    snippets: {
      codeReview: {
        label: 'Code-Review',
        description: 'Prüfen Sie die Änderungen auf Regressionen und fehlende Tests.',
        text: 'Bitte auf Fehler, Regressionen und fehlende Tests prüfen.'
      },
      implementationPlan: {
        label: 'Implementierungsplan',
        description: 'Skizzieren Sie einen Ansatz, bevor Sie Code ändern.',
        text: 'Bitte erstellen Sie einen kurzen Implementierungsplan, bevor Sie Code ändern.'
      },
      explainThis: {
        label: 'Erklären',
        description: 'Erklären Sie, wie der ausgewählte Code funktioniert.',
        text: 'Bitte erklären Sie, wie das funktioniert, und zeigen Sie mir die wichtigsten Dateien.'
      }
    }
  },

  shell: {
    windowControls: 'Fenstersteuerung',
    paneControls: 'Bereichssteuerung',
    appControls: 'App-Steuerung',
    modelMenu: {
      search: 'Modelle durchsuchen',
      noModels: 'Keine Modelle gefunden',
      editModels: 'Modelle bearbeiten…',
      refreshModels: 'Modelle aktualisieren',
      fast: 'Schnell',
      medium: 'Mittel'
    },
    modelOptions: {
      noOptions: 'Keine Optionen für dieses Modell',
      options: 'Optionen',
      thinking: 'Denken',
      fast: 'Schnell',
      effort: 'Aufwand',
      minimal: 'Minimal',
      low: 'Niedrig',
      medium: 'Mittel',
      high: 'Hoch',
      max: 'Max',
      updateFailed: 'Modelloption-Update fehlgeschlagen',
      fastFailed: 'Schnellmodus-Update fehlgeschlagen'
    },
    gatewayMenu: {
      gateway: 'Gateway',
      connected: 'Verbunden',
      connecting: 'Verbinde',
      offline: 'Offline',
      disconnected: 'Getrennt',
      openSystem: 'Systembereich öffnen',
      recentActivity: 'Letzte Aktivität',
      viewAllLogs: 'Alle Logs anzeigen →',
      messagingPlatforms: 'Nachrichtenplattformen'
    },
    statusbar: {
      unknown: 'Unbekannt',
      restart: 'Neustart',
      update: 'Aktualisieren',
      updateInProgress: 'Update läuft',
      closeCommandCenter: 'Befehlszentrum schließen',
      openCommandCenter: 'Befehlszentrum öffnen',
      showTerminal: 'Terminal anzeigen',
      hideTerminal: 'Terminal ausblenden',
      gateway: 'Gateway',
      gatewayReady: 'bereit',
      gatewayNeedsSetup: 'Einrichtung erforderlich',
      gatewayChecking: 'prüft',
      gatewayConnecting: 'verbindet',
      gatewayOffline: 'offline',
      gatewayRestarting: 'startet neu…',
      gatewayTitle: 'Sara-Inferenz-Gateway-Status',
      agents: 'Agenten',
      closeAgents: 'Agenten schließen',
      openAgents: 'Agenten öffnen',
      modelNone: 'kein',
      noModel: 'kein Modell',
      switchModel: 'Modell wechseln',
      openModelPicker: 'Modellauswahl öffnen'
    }
  },

  settings: {
    closeSettings: 'Einstellungen schließen',
    exportConfig: 'Konfiguration exportieren',
    importConfig: 'Konfiguration importieren',
    resetToDefaults: 'Auf Standard zurücksetzen',
    resetConfirm: 'Alle Einstellungen zurücksetzen?',
    exportFailed: 'Export fehlgeschlagen',
    resetFailed: 'Zurücksetzen fehlgeschlagen',
    nav: {
      providers: 'Anbieter',
      providerAccounts: 'Konten',
      providerApiKeys: 'API-Schlüssel',
      gateway: 'Gateway',
      apiKeys: 'Werkzeuge & Schlüssel',
      keysTools: 'Werkzeuge',
      keysSettings: 'Einstellungen',
      mcp: 'MCP',
      archivedChats: 'Archivierte Chats',
      about: 'Über',
      notifications: 'Benachrichtigungen'
    },
    sections: {
      model: 'Modell',
      chat: 'Chat',
      appearance: 'Erscheinungsbild',
      workspace: 'Arbeitsbereich',
      safety: 'Sicherheit',
      memory: 'Speicher & Kontext',
      voice: 'Sprache',
      advanced: 'Erweitert'
    },
    modeOptions: {
      light: { label: 'Hell', description: 'Helle Desktop-Oberflächen' },
      dark: { label: 'Dunkel', description: 'Augenschonender Arbeitsbereich' },
      system: { label: 'System', description: 'Systemeinstellung folgen' }
    },
    appearance: {
      title: 'Erscheinungsbild',
      intro:
        'Desktop-Anzeigeeinstellungen. Der Modus steuert die Helligkeit; das Theme steuert die Akzentpalette.',
      colorMode: 'Farbmodus',
      colorModeDesc: 'Wählen Sie einen festen Modus oder folgen Sie der Systemeinstellung.',
      themeTitle: 'Theme',
      themeDesc: 'Nur Desktop-Paletten.',
      installTitle: 'Aus VS Code installieren',
      installDesc:
        'Fügen Sie eine Marketplace-Erweiterungs-ID ein, um das Farbschema zu konvertieren.',
      installPlaceholder: 'publisher.extension',
      installButton: 'Installieren',
      installing: 'Installiere…',
      installError: 'Dieses Theme konnte nicht installiert werden.',
      removeTheme: 'Theme entfernen',
      importedBadge: 'Importiert'
    },
    about: {
      heading: 'Sara Desktop',
      version: value => `Version ${value}`,
      versionUnavailable: 'Version nicht verfügbar',
      updates: 'Updates',
      checkNow: 'Jetzt prüfen',
      checking: 'Prüfe…',
      seeWhatsNew: 'Neuerungen anzeigen',
      releaseNotes: 'Versionshinweise',
      onLatest: 'Sie haben die neueste Version.',
      never: 'nie',
      justNow: 'gerade eben'
    },
    notifications: {
      title: 'Benachrichtigungen',
      enableAll: 'Benachrichtigungen aktivieren',
      enableAllDesc: 'Hauptschalter. Deaktivieren, um alle Benachrichtigungen stummzuschalten.',
      test: 'Testbenachrichtigung senden',
      testTitle: 'Sara',
      testBody: 'Benachrichtigungen funktionieren.',
      completionSoundTitle: 'Abschlusston',
      completionSoundDesc: 'Wird abgespielt, wenn ein Agenten-Durchlauf endet.',
      completionSoundPreview: 'Vorschau'
    },
    config: {
      none: 'Keine',
      notSet: 'Nicht gesetzt',
      loading: 'Lade Sara-Konfiguration...',
      emptyTitle: 'Nichts zu konfigurieren',
      emptyDesc: 'Dieser Abschnitt hat keine einstellbaren Parameter.',
      failedLoad: 'Einstellungen konnten nicht geladen werden',
      autosaveFailed: 'Autosave fehlgeschlagen',
      imported: 'Konfiguration importiert',
      invalidJson: 'Ungültiges JSON'
    },
    model: {
      loading: 'Lade Modellkonfiguration...',
      appliesDesc: 'Gilt für neue Sitzungen.',
      provider: 'Anbieter',
      model: 'Modell',
      applying: 'Anwenden...',
      defaultsLabel: 'Standard',
      reasoning: 'Denken',
      reasoningOff: 'Aus',
      defaultsFailed: 'Standardmodelle konnten nicht gespeichert werden'
    }
  },

  notifications: {
    region: 'Benachrichtigungen',
    hide: 'Ausblenden',
    show: 'Anzeigen',
    more: count => `${count} weitere`,
    clearAll: 'Alle löschen',
    dismiss: 'Benachrichtigung schließen',
    details: 'Details',
    copyDetail: 'Detail kopieren',
    copyDetailFailed: 'Detail konnte nicht kopiert werden',
    updateSara: 'Sara aktualisieren'
  },

  statusStack: {
    agents: 'Agenten',
    background: count => `${count} Hintergrund`,
    subagents: count => `${count} Unteragent${count === 1 ? '' : 'en'}`,
    todos: (done, total) => `Aufgaben ${done}/${total}`,
    running: 'Läuft',
    stop: 'Stopp',
    dismiss: 'Schließen',
    exit: code => `Exit ${code}`
  },

  desktop: {
    sessionUnavailable: 'Sitzung nicht verfügbar',
    createSessionFailed: 'Neue Sitzung konnte nicht erstellt werden',
    promptFailed: 'Prompt fehlgeschlagen',
    stopFailed: 'Stopp fehlgeschlagen',
    regenerateFailed: 'Neugenerierung fehlgeschlagen',
    editFailed: 'Bearbeitung fehlgeschlagen',
    resumeFailed: 'Fortsetzung fehlgeschlagen',
    deleteFailed: 'Löschen fehlgeschlagen',
    archived: 'Archiviert',
    archiveFailed: 'Archivierung fehlgeschlagen',
    modelSwitchFailed: 'Modellwechsel fehlgeschlagen',
    sessionExported: 'Sitzung exportiert',
    sessionExportFailed: 'Sitzung konnte nicht exportiert werden',
    clipboard: 'Zwischenablage',
    noClipboardImage: 'Kein Bild in der Zwischenablage',
    clipboardPasteFailed: 'Einfügen fehlgeschlagen',
    dropFiles: 'Dateien ablegen'
  },

  assistant: {
    thread: {
      loadingSession: 'Lade Sitzung',
      showEarlier: 'Frühere Nachrichten anzeigen',
      loadingResponse: 'Sara lädt eine Antwort',
      thinking: 'Denkt',
      today: time => `Heute, ${time}`,
      yesterday: time => `Gestern, ${time}`,
      copy: 'Kopieren',
      refresh: 'Aktualisieren',
      moreActions: 'Weitere Aktionen',
      dismissError: 'Fehler schließen',
      editMessage: 'Nachricht bearbeiten',
      scrollToBottom: 'Nach unten scrollen',
      stop: 'Stopp',
      restorePrevious: 'Vorherigen Prüfpunkt wiederherstellen',
      restoreCheckpoint: 'Prüfpunkt wiederherstellen',
      sendEdited: 'Bearbeitete Nachricht senden',
      attachingFile: 'Datei wird angehängt…'
    },
    approval: {
      gatewayDisconnected: 'Sara-Gateway nicht verbunden',
      sendFailed: 'Antwort konnte nicht gesendet werden',
      run: 'Ausführen',
      command: 'Befehl',
      reject: 'Ablehnen',
      alwaysAllow: 'Immer erlauben'
    },
    tool: {
      code: 'Code',
      copyCode: 'Code kopieren',
      copyOutput: 'Ausgabe kopieren',
      copyCommand: 'Befehl kopieren',
      copyContent: 'Inhalt kopieren',
      copyUrl: 'URL kopieren',
      copyResults: 'Ergebnisse kopieren',
      statusRunning: 'Läuft',
      statusError: 'Fehler',
      statusRecovered: 'Wiederhergestellt',
      statusDone: 'Fertig'
    }
  },

  errors: {
    genericFailure: 'Etwas ist schiefgelaufen',
    boundaryTitle: 'Ein Fehler ist in der Oberfläche aufgetreten',
    boundaryDesc: 'Die Ansicht hat einen unerwarteten Fehler. Ihre Chats sind sicher.',
    reloadWindow: 'Fenster neu laden',
    openLogs: 'Logs öffnen'
  },

  modelPicker: {
    title: 'Modell wechseln',
    current: 'aktuell:',
    unknown: '(unbekannt)',
    search: 'Anbieter und Modelle filtern',
    noModels: 'Keine Modelle gefunden',
    addProvider: 'Anbieter hinzufügen',
    loadFailed: 'Modelle konnten nicht geladen werden',
    noAuthenticatedProviders: 'Keine authentifizierten Anbieter.',
    pro: 'Pro',
    freeTier: 'Kostenlos',
    free: 'Kostenlos'
  },

  modelVisibility: {
    title: 'Modelle',
    search: 'Modelle durchsuchen',
    noAuthenticatedProviders: 'Keine authentifizierten Anbieter.',
    addProvider: 'Anbieter hinzufügen…'
  },

  install: {
    oneTimeTitle: 'Sara benötigt eine einmalige Installation',
    copyCommand: 'Befehl kopieren',
    viewDocs: 'Installationsdokumentation anzeigen',
    error: 'Fehler',
    cancelInstall: 'Installation abbrechen'
  }
})
