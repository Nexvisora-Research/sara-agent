import { defineLocale } from './define-locale'

export const fr = defineLocale({
  common: {
    apply: 'Appliquer',
    back: 'Retour',
    save: 'Enregistrer',
    saving: 'Enregistrement…',
    cancel: 'Annuler',
    change: 'Modifier',
    choose: 'Choisir',
    clear: 'Effacer',
    close: 'Fermer',
    collapse: 'Réduire',
    confirm: 'Confirmer',
    connect: 'Connecter',
    connecting: 'Connexion en cours',
    continue: 'Continuer',
    copied: 'Copié',
    copy: 'Copier',
    copyFailed: 'Échec de la copie',
    delete: 'Supprimer',
    docs: 'Documentation',
    done: 'Terminé',
    error: 'Erreur',
    failed: 'Échoué',
    free: 'Gratuit',
    loading: 'Chargement…',
    notSet: 'Non défini',
    refresh: 'Actualiser',
    remove: 'Retirer',
    replace: 'Remplacer',
    retry: 'Réessayer',
    run: 'Exécuter',
    send: 'Envoyer',
    set: 'Définir',
    skip: 'Passer',
    update: 'Mettre à jour',
    on: 'Activé',
    off: 'Désactivé'
  },

  boot: {
    ready: 'Sara Desktop est prêt',
    desktopBootFailedWithMessage: message => `Échec du démarrage du bureau : ${message}`,
    steps: {
      connectingGateway: 'Connexion à la passerelle du bureau',
      loadingSettings: 'Chargement des paramètres Sara',
      loadingSessions: 'Chargement des sessions récentes',
      startingDesktopConnection: 'Démarrage de la connexion bureau',
      startingSaraDesktop: 'Démarrage de Sara Desktop…'
    },
    errors: {
      backgroundExited: 'Le processus d\'arrière-plan Sara s\'est arrêté.',
      backgroundExitedDuringStartup: 'Le processus d\'arrière-plan Sara s\'est arrêté au démarrage.',
      backendStopped: 'Backend arrêté',
      desktopBootFailed: 'Échec du démarrage du bureau',
      gatewaySignInRequired: 'Connexion à la passerelle requise',
      ipcBridgeUnavailable: 'Le pont IPC du bureau est indisponible.'
    },
    failure: {
      title: 'Sara n\'a pas pu démarrer',
      description:
        'La passerelle d\'arrière-plan ne s\'est pas lancée. Essayez l\'une des étapes de récupération ci-dessous. Vos discussions et paramètres sont conservés.',
      remoteTitle: 'Connexion à la passerelle distante requise',
      remoteDescription:
        'Votre session de passerelle distante a expiré. Connectez-vous à nouveau. Vos discussions et paramètres sont conservés.',
      retry: 'Réessayer',
      repairInstall: 'Réparer l\'installation',
      useLocalGateway: 'Utiliser la passerelle locale',
      openLogs: 'Ouvrir les logs',
      repairHint: 'La réparation relance l\'installateur et peut prendre quelques minutes.',
      remoteSignInHint: 'Ouvre la fenêtre de connexion. Utilisez la passerelle locale pour basculer vers le backend intégré.',
      signedInTitle: 'Connecté',
      signedInMessage: 'Reconnexion à la passerelle distante…',
      signInIncompleteTitle: 'Connexion incomplète',
      signInIncompleteMessage: 'La fenêtre de connexion s\'est fermée avant la fin de l\'authentification.',
      signInFailed: 'Échec de la connexion',
      signInToRemoteGateway: 'Se connecter à la passerelle distante',
      signInWithProvider: provider => `Se connecter avec ${provider}`,
      identityProvider: 'votre fournisseur d\'identité'
    }
  },

  language: {
    label: 'Langue',
    description: 'Choisissez la langue de l\'interface du bureau.',
    saving: 'Enregistrement de la langue…',
    saveError: 'Échec de la mise à jour de la langue',
    switchTo: 'Changer de langue',
    searchPlaceholder: 'Rechercher des langues…',
    noResults: 'Aucune langue trouvée'
  },

  titlebar: {
    hideSidebar: 'Masquer la barre latérale',
    showSidebar: 'Afficher la barre latérale',
    search: 'Rechercher',
    searchTitle: 'Rechercher sessions, vues et actions',
    swapSidebarSides: 'Échanger les côtés de la barre latérale',
    swapSidebarSidesTitle: 'Échanger les côtés des sessions et de l\'explorateur',
    hideRightSidebar: 'Masquer la barre latérale droite',
    showRightSidebar: 'Afficher la barre latérale droite',
    muteHaptics: 'Désactiver les vibrations',
    unmuteHaptics: 'Activer les vibrations',
    openSettings: 'Ouvrir les paramètres',
    openKeybinds: 'Raccourcis clavier'
  },

  sidebar: {
    nav: {
      'new-session': 'Nouvelle session',
      skills: 'Compétences et outils',
      messaging: 'Messagerie',
      artifacts: 'Artéfacts',
      memory: 'Mémoire'
    },
    searchAria: 'Rechercher des sessions',
    searchPlaceholder: 'Rechercher des sessions…',
    clearSearch: 'Effacer la recherche',
    noMatch: query => `Aucune session ne correspond à « ${query} ».`,
    results: 'Résultats',
    pinned: 'Épinglées',
    sessions: 'Sessions',
    cronJobs: 'Tâches planifiées',
    loading: 'Chargement…',
    loadMore: 'Charger plus',
    row: {
      pin: 'Épingler',
      unpin: 'Détacher',
      copyId: 'Copier l\'ID',
      export: 'Exporter',
      rename: 'Renommer',
      archive: 'Archiver',
      newWindow: 'Nouvelle fenêtre',
      copyIdFailed: 'Impossible de copier l\'ID de session',
      sessionRunning: 'Session en cours',
      needsInput: 'Nécessite votre saisie',
      waitingForAnswer: 'En attente de votre réponse',
      renamed: 'Renommé',
      renameFailed: 'Échec du renommage',
      renameTitle: 'Renommer la session',
      renameDesc: 'Donnez un titre mémorable. Laissez vide pour effacer.',
      untitledPlaceholder: 'Session sans titre',
      ageNow: 'maintenant',
      ageDay: 'j',
      ageHour: 'h',
      ageMin: 'min'
    }
  },

  composer: {
    message: 'Message',
    wakingProfile: profile => `Réveil de ${profile}…`,
    placeholderStarting: 'Démarrage de Sara...',
    placeholderReconnecting: 'Reconnexion à Sara…',
    placeholderFollowUp: 'Envoyer un suivi',
    newSessionPlaceholders: [
      'Que construisons-nous ?',
      'Donnez une tâche à Sara',
      'À quoi pensez-vous ?',
      'Décrivez ce dont vous avez besoin',
      'Par où commencer ?',
      'Demandez n\'importe quoi',
      'Commencez par un objectif'
    ],
    followUpPlaceholders: [
      'Envoyer un suivi',
      'Ajouter plus de contexte',
      'Affiner la demande',
      'Et ensuite ?',
      'Continuez',
      'Allez plus loin',
      'Ajuster ou continuer'
    ],
    startVoice: 'Lancer une conversation vocale',
    queueMessage: 'Message en file d\'attente',
    steer: 'Diriger l\'exécution en cours',
    stop: 'Arrêter',
    send: 'Envoyer',
    speaking: 'Parle',
    transcribing: 'Transcription',
    thinking: 'Réfléchit',
    muted: 'En sourdine',
    listening: 'Écoute',
    muteMic: 'Couper le micro',
    unmuteMic: 'Réactiver le micro',
    stopListening: 'Arrêter d\'écouter et envoyer',
    stopShort: 'Arrêt',
    endConversation: 'Terminer la conversation vocale',
    endShort: 'Fin',
    attachLabel: 'Joindre',
    files: 'Fichiers…',
    folder: 'Dossier…',
    images: 'Images…',
    pasteImage: 'Coller une image',
    url: 'URL…',
    promptSnippets: 'Extraits de prompt…',
    dropFiles: 'Déposez des fichiers pour les joindre',
    dropSession: 'Déposer pour lier ce chat',
    snippetsTitle: 'Extraits de prompt',
    snippetsDesc: 'Choisissez un prompt de départ à insérer dans le composeur.',
    snippets: {
      codeReview: {
        label: 'Revue de code',
        description: 'Auditez les changements pour les régressions, cas limites et tests manquants.',
        text: 'Veuillez vérifier les bugs, régressions et tests manquants.'
      },
      implementationPlan: {
        label: 'Plan d\'implémentation',
        description: 'Esquissez une approche avant de toucher au code.',
        text: 'Veuillez établir un plan d\'implémentation concis avant de modifier le code.'
      },
      explainThis: {
        label: 'Expliquer',
        description: 'Expliquez le fonctionnement du code sélectionné.',
        text: 'Veuillez expliquer comment cela fonctionne et m\'indiquer les fichiers clés.'
      }
    }
  },

  shell: {
    windowControls: 'Contrôles de la fenêtre',
    paneControls: 'Contrôles du panneau',
    appControls: 'Contrôles de l\'application',
    modelMenu: {
      search: 'Rechercher des modèles',
      noModels: 'Aucun modèle trouvé',
      editModels: 'Modifier les modèles…',
      refreshModels: 'Actualiser les modèles',
      fast: 'Rapide',
      medium: 'Moyen'
    },
    modelOptions: {
      noOptions: 'Aucune option pour ce modèle',
      options: 'Options',
      thinking: 'Réflexion',
      fast: 'Rapide',
      effort: 'Effort',
      minimal: 'Minimal',
      low: 'Faible',
      medium: 'Moyen',
      high: 'Élevé',
      max: 'Max',
      updateFailed: 'Échec de la mise à jour des options',
      fastFailed: 'Échec de la mise à jour du mode rapide'
    },
    gatewayMenu: {
      gateway: 'Passerelle',
      connected: 'Connecté',
      connecting: 'Connexion',
      offline: 'Hors ligne',
      disconnected: 'Déconnecté',
      openSystem: 'Ouvrir le panneau système',
      recentActivity: 'Activité récente',
      viewAllLogs: 'Voir tous les logs →',
      messagingPlatforms: 'Plateformes de messagerie'
    },
    statusbar: {
      unknown: 'Inconnu',
      restart: 'Redémarrer',
      update: 'Mettre à jour',
      updateInProgress: 'Mise à jour en cours',
      closeCommandCenter: 'Fermer le Centre de commandes',
      openCommandCenter: 'Ouvrir le Centre de commandes',
      showTerminal: 'Afficher le terminal',
      hideTerminal: 'Masquer le terminal',
      gateway: 'Passerelle',
      gatewayReady: 'prêt',
      gatewayNeedsSetup: 'configuration requise',
      gatewayChecking: 'vérification',
      gatewayConnecting: 'connexion',
      gatewayOffline: 'hors ligne',
      gatewayRestarting: 'redémarrage…',
      gatewayTitle: 'État de la passerelle d\'inférence Sara',
      agents: 'Agents',
      closeAgents: 'Fermer les agents',
      openAgents: 'Ouvrir les agents',
      modelNone: 'aucun',
      noModel: 'pas de modèle',
      switchModel: 'Changer de modèle',
      openModelPicker: 'Ouvrir le sélecteur de modèle'
    }
  },

  settings: {
    closeSettings: 'Fermer les paramètres',
    exportConfig: 'Exporter la configuration',
    importConfig: 'Importer la configuration',
    resetToDefaults: 'Réinitialiser',
    resetConfirm: 'Réinitialiser tous les paramètres ?',
    exportFailed: 'Échec de l\'exportation',
    resetFailed: 'Échec de la réinitialisation',
    nav: {
      providers: 'Fournisseurs',
      providerAccounts: 'Comptes',
      providerApiKeys: 'Clés API',
      gateway: 'Passerelle',
      apiKeys: 'Outils et clés',
      keysTools: 'Outils',
      keysSettings: 'Paramètres',
      mcp: 'MCP',
      archivedChats: 'Chats archivés',
      about: 'À propos',
      notifications: 'Notifications'
    },
    sections: {
      model: 'Modèle',
      chat: 'Chat',
      appearance: 'Apparence',
      workspace: 'Espace de travail',
      safety: 'Sécurité',
      memory: 'Mémoire et contexte',
      voice: 'Voix',
      advanced: 'Avancé'
    },
    modeOptions: {
      light: { label: 'Clair', description: 'Surfaces de bureau lumineuses' },
      dark: { label: 'Sombre', description: 'Espace de travail faible luminosité' },
      system: { label: 'Système', description: 'Suivre l\'apparence du système' }
    },
    appearance: {
      title: 'Apparence',
      intro:
        'Préférences d\'affichage du bureau. Le mode contrôle la luminosité ; le thème contrôle la palette d\'accentuation.',
      colorMode: 'Mode couleur',
      colorModeDesc: 'Choisissez un mode fixe ou laissez Sara suivre votre système.',
      themeTitle: 'Thème',
      themeDesc: 'Palettes du bureau uniquement.',
      installTitle: 'Installer depuis VS Code',
      installDesc:
        'Collez un ID d\'extension Marketplace pour convertir son thème en palette.',
      installPlaceholder: 'publisher.extension',
      installButton: 'Installer',
      installing: 'Installation…',
      installError: 'Impossible d\'installer ce thème.',
      removeTheme: 'Supprimer le thème',
      importedBadge: 'Importé'
    },
    about: {
      heading: 'Sara Desktop',
      version: value => `Version ${value}`,
      versionUnavailable: 'Version indisponible',
      updates: 'Mises à jour',
      checkNow: 'Vérifier maintenant',
      checking: 'Vérification…',
      seeWhatsNew: 'Voir les nouveautés',
      releaseNotes: 'Notes de version',
      onLatest: 'Vous utilisez la dernière version.',
      never: 'jamais',
      justNow: 'à l\'instant'
    },
    notifications: {
      title: 'Notifications',
      enableAll: 'Activer les notifications',
      enableAllDesc: 'Interrupteur principal. Désactivez pour silencier toutes les notifications.',
      test: 'Envoyer une notification test',
      testTitle: 'Sara',
      testBody: 'Les notifications fonctionnent.',
      completionSoundTitle: 'Son de fin',
      completionSoundDesc: 'Joué quand un tour d\'agent se termine.',
      completionSoundPreview: 'Aperçu'
    },
    config: {
      none: 'Aucun',
      notSet: 'Non défini',
      loading: 'Chargement de la configuration Sara...',
      emptyTitle: 'Rien à configurer',
      emptyDesc: 'Cette section n\'a pas de paramètres ajustables.',
      failedLoad: 'Échec du chargement des paramètres',
      autosaveFailed: 'Échec de la sauvegarde automatique',
      imported: 'Configuration importée',
      invalidJson: 'JSON de configuration invalide'
    },
    model: {
      loading: 'Chargement de la configuration du modèle...',
      appliesDesc: 'S\'applique aux nouvelles sessions.',
      provider: 'Fournisseur',
      model: 'Modèle',
      applying: 'Application...',
      defaultsLabel: 'Par défaut',
      reasoning: 'Raisonnement',
      reasoningOff: 'Désactivé',
      defaultsFailed: 'Échec de l\'enregistrement des modèles par défaut'
    }
  },

  notifications: {
    region: 'Notifications',
    hide: 'Masquer',
    show: 'Afficher',
    more: count => `${count} de plus`,
    clearAll: 'Tout effacer',
    dismiss: 'Ignorer la notification',
    details: 'Détails',
    copyDetail: 'Copier le détail',
    copyDetailFailed: 'Impossible de copier le détail',
    updateSara: 'Mettre à jour Sara'
  },

  statusStack: {
    agents: 'Agents',
    background: count => `${count} Arrière-plan`,
    subagents: count => `${count} Sous-agent${count > 1 ? 's' : ''}`,
    todos: (done, total) => `Tâches ${done}/${total}`,
    running: 'En cours',
    stop: 'Arrêter',
    dismiss: 'Ignorer',
    exit: code => `code ${code}`
  },

  desktop: {
    sessionUnavailable: 'Session indisponible',
    createSessionFailed: 'Impossible de créer une session',
    promptFailed: 'Échec du prompt',
    stopFailed: 'Échec de l\'arrêt',
    regenerateFailed: 'Échec de la régénération',
    editFailed: 'Échec de la modification',
    resumeFailed: 'Échec de la reprise',
    deleteFailed: 'Échec de la suppression',
    archived: 'Archivé',
    archiveFailed: 'Échec de l\'archivage',
    modelSwitchFailed: 'Échec du changement de modèle',
    sessionExported: 'Session exportée',
    sessionExportFailed: 'Impossible d\'exporter la session',
    clipboard: 'Presse-papiers',
    noClipboardImage: 'Aucune image dans le presse-papiers',
    clipboardPasteFailed: 'Échec du collage',
    dropFiles: 'Déposer des fichiers'
  },

  assistant: {
    thread: {
      loadingSession: 'Chargement de la session',
      showEarlier: 'Afficher les messages précédents',
      loadingResponse: 'Sara charge une réponse',
      thinking: 'Réfléchit',
      today: time => `Aujourd\'hui, ${time}`,
      yesterday: time => `Hier, ${time}`,
      copy: 'Copier',
      refresh: 'Actualiser',
      moreActions: 'Plus d\'actions',
      dismissError: 'Ignorer l\'erreur',
      editMessage: 'Modifier le message',
      scrollToBottom: 'Aller en bas',
      stop: 'Arrêter',
      restorePrevious: 'Restaurer le point précédent',
      restoreCheckpoint: 'Restaurer le point',
      sendEdited: 'Envoyer le message modifié',
      attachingFile: 'Fichier joint…'
    },
    approval: {
      gatewayDisconnected: 'La passerelle Sara n\'est pas connectée',
      sendFailed: 'Impossible d\'envoyer la réponse',
      run: 'Exécuter',
      command: 'Commande',
      reject: 'Refuser',
      alwaysAllow: 'Toujours autoriser'
    },
    tool: {
      code: 'Code',
      copyCode: 'Copier le code',
      copyOutput: 'Copier la sortie',
      copyCommand: 'Copier la commande',
      copyContent: 'Copier le contenu',
      copyUrl: 'Copier l\'URL',
      copyResults: 'Copier les résultats',
      statusRunning: 'En cours',
      statusError: 'Erreur',
      statusRecovered: 'Récupéré',
      statusDone: 'Terminé'
    }
  },

  errors: {
    genericFailure: 'Quelque chose s\'est mal passé',
    boundaryTitle: 'Quelque chose a cassé dans l\'interface',
    boundaryDesc: 'La vue a rencontré une erreur inattendue. Vos discussions sont en sécurité.',
    reloadWindow: 'Recharger la fenêtre',
    openLogs: 'Ouvrir les logs'
  },

  modelPicker: {
    title: 'Changer de modèle',
    current: 'actuel :',
    unknown: '(inconnu)',
    search: 'Filtrer les fournisseurs et modèles',
    noModels: 'Aucun modèle trouvé',
    addProvider: 'Ajouter un fournisseur',
    loadFailed: 'Impossible de charger les modèles',
    noAuthenticatedProviders: 'Aucun fournisseur authentifié.',
    pro: 'Pro',
    freeTier: 'Gratuit',
    free: 'Gratuit'
  },

  modelVisibility: {
    title: 'Modèles',
    search: 'Rechercher des modèles',
    noAuthenticatedProviders: 'Aucun fournisseur authentifié.',
    addProvider: 'Ajouter un fournisseur…'
  },

  install: {
    oneTimeTitle: 'Sara nécessite une installation unique',
    copyCommand: 'Copier la commande',
    viewDocs: 'Voir la documentation',
    error: 'Erreur',
    cancelInstall: 'Annuler l\'installation'
  }
})
