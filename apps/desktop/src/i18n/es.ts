import { defineLocale } from './define-locale'

export const es = defineLocale({
  common: {
    apply: 'Aplicar',
    back: 'Atrás',
    save: 'Guardar',
    saving: 'Guardando…',
    cancel: 'Cancelar',
    change: 'Cambiar',
    choose: 'Elegir',
    clear: 'Limpiar',
    close: 'Cerrar',
    collapse: 'Colapsar',
    confirm: 'Confirmar',
    connect: 'Conectar',
    connecting: 'Conectando',
    continue: 'Continuar',
    copied: 'Copiado',
    copy: 'Copiar',
    copyFailed: 'Error al copiar',
    delete: 'Eliminar',
    docs: 'Documentación',
    done: 'Hecho',
    error: 'Error',
    failed: 'Falló',
    free: 'Gratis',
    loading: 'Cargando…',
    notSet: 'No establecido',
    refresh: 'Actualizar',
    remove: 'Eliminar',
    replace: 'Reemplazar',
    retry: 'Reintentar',
    run: 'Ejecutar',
    send: 'Enviar',
    set: 'Establecer',
    skip: 'Saltar',
    update: 'Actualizar',
    on: 'Activado',
    off: 'Desactivado'
  },

  boot: {
    ready: 'Sara Desktop está listo',
    desktopBootFailedWithMessage: message => `Error al iniciar el escritorio: ${message}`,
    steps: {
      connectingGateway: 'Conectando con la puerta de enlace del escritorio',
      loadingSettings: 'Cargando configuración de Sara',
      loadingSessions: 'Cargando sesiones recientes',
      startingDesktopConnection: 'Iniciando conexión del escritorio',
      startingSaraDesktop: 'Iniciando Sara Desktop…'
    },
    errors: {
      backgroundExited: 'El proceso de fondo de Sara terminó.',
      backgroundExitedDuringStartup: 'El proceso de fondo de Sara terminó durante el inicio.',
      backendStopped: 'Backend detenido',
      desktopBootFailed: 'Error al iniciar el escritorio',
      gatewaySignInRequired: 'Inicio de sesión en la puerta de enlace requerido',
      ipcBridgeUnavailable: 'El puente IPC del escritorio no está disponible.'
    },
    failure: {
      title: 'Sara no pudo iniciar',
      description:
        'La puerta de enlace de fondo no se inició. Pruebe alguno de los pasos de recuperación. Sus chats y configuraciones no se eliminan.',
      remoteTitle: 'Inicio de sesión remoto requerido',
      remoteDescription:
        'Su sesión remota ha expirado. Inicie sesión de nuevo para reconectar.',
      retry: 'Reintentar',
      repairInstall: 'Reparar instalación',
      useLocalGateway: 'Usar puerta de enlace local',
      openLogs: 'Abrir registros',
      repairHint: 'La reparación vuelve a ejecutar el instalador y puede tomar unos minutos.',
      remoteSignInHint: 'Abre la ventana de inicio de sesión. Use la puerta de enlace local para cambiar al backend incluido.',
      signedInTitle: 'Sesión iniciada',
      signedInMessage: 'Reconectando con la puerta de enlace remota…',
      signInIncompleteTitle: 'Inicio de sesión incompleto',
      signInIncompleteMessage: 'La ventana de inicio de sesión se cerró antes de completar la autenticación.',
      signInFailed: 'Error al iniciar sesión',
      signInToRemoteGateway: 'Iniciar sesión en la puerta de enlace remota',
      signInWithProvider: provider => `Iniciar sesión con ${provider}`,
      identityProvider: 'su proveedor de identidad'
    }
  },

  language: {
    label: 'Idioma',
    description: 'Elija el idioma de la interfaz del escritorio.',
    saving: 'Guardando idioma…',
    saveError: 'Error al actualizar el idioma',
    switchTo: 'Cambiar idioma',
    searchPlaceholder: 'Buscar idiomas…',
    noResults: 'No se encontraron idiomas'
  },

  titlebar: {
    hideSidebar: 'Ocultar barra lateral',
    showSidebar: 'Mostrar barra lateral',
    search: 'Buscar',
    searchTitle: 'Buscar sesiones, vistas y acciones',
    swapSidebarSides: 'Intercambiar lados de la barra lateral',
    swapSidebarSidesTitle: 'Intercambiar los lados de sesiones y explorador',
    hideRightSidebar: 'Ocultar barra lateral derecha',
    showRightSidebar: 'Mostrar barra lateral derecha',
    muteHaptics: 'Silenciar hápticos',
    unmuteHaptics: 'Activar hápticos',
    openSettings: 'Abrir configuración',
    openKeybinds: 'Atajos de teclado'
  },

  sidebar: {
    nav: {
      'new-session': 'Nueva sesión',
      skills: 'Habilidades y herramientas',
      messaging: 'Mensajería',
      artifacts: 'Artefactos',
      memory: 'Memoria'
    },
    searchAria: 'Buscar sesiones',
    searchPlaceholder: 'Buscar sesiones…',
    clearSearch: 'Limpiar búsqueda',
    noMatch: query => `No hay sesiones que coincidan con "${query}".`,
    results: 'Resultados',
    pinned: 'Fijadas',
    sessions: 'Sesiones',
    cronJobs: 'Tareas programadas',
    loading: 'Cargando…',
    loadMore: 'Cargar más',
    row: {
      pin: 'Fijar',
      unpin: 'Desfijar',
      copyId: 'Copiar ID',
      export: 'Exportar',
      rename: 'Renombrar',
      archive: 'Archivar',
      newWindow: 'Nueva ventana',
      copyIdFailed: 'No se pudo copiar el ID de la sesión',
      sessionRunning: 'Sesión en ejecución',
      needsInput: 'Necesita su entrada',
      waitingForAnswer: 'Esperando su respuesta',
      renamed: 'Renombrado',
      renameFailed: 'Error al renombrar',
      renameTitle: 'Renombrar sesión',
      renameDesc: 'Dé un título memorable. Déjelo vacío para limpiar.',
      untitledPlaceholder: 'Sesión sin título',
      ageNow: 'ahora',
      ageDay: 'd',
      ageHour: 'h',
      ageMin: 'm'
    }
  },

  composer: {
    message: 'Mensaje',
    wakingProfile: profile => `Activando ${profile}…`,
    placeholderStarting: 'Iniciando Sara...',
    placeholderReconnecting: 'Reconectando con Sara…',
    placeholderFollowUp: 'Enviar seguimiento',
    newSessionPlaceholders: [
      '¿Qué estamos construyendo?',
      'Dale una tarea a Sara',
      '¿En qué estás pensando?',
      'Describe lo que necesitas',
      '¿Qué deberíamos abordar?',
      'Pregunta lo que sea',
      'Empieza con un objetivo'
    ],
    followUpPlaceholders: [
      'Enviar un seguimiento',
      'Añadir más contexto',
      'Refinar la solicitud',
      '¿Qué sigue?',
      'Continúa',
      'Ve más allá',
      'Ajustar o continuar'
    ],
    startVoice: 'Iniciar conversación por voz',
    queueMessage: 'Mensaje en cola',
    steer: 'Dirigir la ejecución actual',
    stop: 'Detener',
    send: 'Enviar',
    speaking: 'Hablando',
    transcribing: 'Transcribiendo',
    thinking: 'Pensando',
    muted: 'Silenciado',
    listening: 'Escuchando',
    muteMic: 'Silenciar micrófono',
    unmuteMic: 'Activar micrófono',
    stopListening: 'Dejar de escuchar y enviar',
    stopShort: 'Detener',
    endConversation: 'Finalizar conversación por voz',
    endShort: 'Fin',
    attachLabel: 'Adjuntar',
    files: 'Archivos…',
    folder: 'Carpeta…',
    images: 'Imágenes…',
    pasteImage: 'Pegar imagen',
    url: 'URL…',
    promptSnippets: 'Fragmentos de prompt…',
    dropFiles: 'Arrastre archivos para adjuntar',
    dropSession: 'Arrastre para enlazar este chat',
    snippetsTitle: 'Fragmentos de prompt',
    snippetsDesc: 'Elija un prompt de inicio para el compositor.',
    snippets: {
      codeReview: {
        label: 'Revisión de código',
        description: 'Audite los cambios para detectar regresiones y pruebas faltantes.',
        text: 'Por favor, revise errores, regresiones y pruebas faltantes.'
      },
      implementationPlan: {
        label: 'Plan de implementación',
        description: 'Esboce un enfoque antes de tocar el código.',
        text: 'Por favor, haga un plan de implementación conciso antes de cambiar el código.'
      },
      explainThis: {
        label: 'Explicar',
        description: 'Explique cómo funciona el código seleccionado.',
        text: 'Por favor, explique cómo funciona y muéstreme los archivos clave.'
      }
    }
  },

  shell: {
    windowControls: 'Controles de ventana',
    paneControls: 'Controles de panel',
    appControls: 'Controles de la aplicación',
    modelMenu: {
      search: 'Buscar modelos',
      noModels: 'No se encontraron modelos',
      editModels: 'Editar modelos…',
      refreshModels: 'Actualizar modelos',
      fast: 'Rápido',
      medium: 'Medio'
    },
    modelOptions: {
      noOptions: 'Sin opciones para este modelo',
      options: 'Opciones',
      thinking: 'Pensamiento',
      fast: 'Rápido',
      effort: 'Esfuerzo',
      minimal: 'Mínimo',
      low: 'Bajo',
      medium: 'Medio',
      high: 'Alto',
      max: 'Máximo',
      updateFailed: 'Error al actualizar opciones del modelo',
      fastFailed: 'Error al actualizar modo rápido'
    },
    gatewayMenu: {
      gateway: 'Puerta de enlace',
      connected: 'Conectado',
      connecting: 'Conectando',
      offline: 'Desconectado',
      disconnected: 'Desconectado',
      openSystem: 'Abrir panel del sistema',
      recentActivity: 'Actividad reciente',
      viewAllLogs: 'Ver todos los registros →',
      messagingPlatforms: 'Plataformas de mensajería'
    },
    statusbar: {
      unknown: 'Desconocido',
      restart: 'Reiniciar',
      update: 'Actualizar',
      updateInProgress: 'Actualización en curso',
      closeCommandCenter: 'Cerrar Centro de comandos',
      openCommandCenter: 'Abrir Centro de comandos',
      showTerminal: 'Mostrar terminal',
      hideTerminal: 'Ocultar terminal',
      gateway: 'Puerta de enlace',
      gatewayReady: 'listo',
      gatewayNeedsSetup: 'configuración necesaria',
      gatewayChecking: 'verificando',
      gatewayConnecting: 'conectando',
      gatewayOffline: 'desconectado',
      gatewayRestarting: 'reiniciando…',
      gatewayTitle: 'Estado de la puerta de enlace de Sara',
      agents: 'Agentes',
      closeAgents: 'Cerrar agentes',
      openAgents: 'Abrir agentes',
      modelNone: 'ninguno',
      noModel: 'sin modelo',
      switchModel: 'Cambiar modelo',
      openModelPicker: 'Abrir selector de modelo'
    }
  },

  settings: {
    closeSettings: 'Cerrar configuración',
    exportConfig: 'Exportar configuración',
    importConfig: 'Importar configuración',
    resetToDefaults: 'Restablecer valores predeterminados',
    resetConfirm: '¿Restablecer toda la configuración?',
    exportFailed: 'Error al exportar',
    resetFailed: 'Error al restablecer',
    nav: {
      providers: 'Proveedores',
      providerAccounts: 'Cuentas',
      providerApiKeys: 'Claves API',
      gateway: 'Puerta de enlace',
      apiKeys: 'Herramientas y claves',
      keysTools: 'Herramientas',
      keysSettings: 'Ajustes',
      mcp: 'MCP',
      archivedChats: 'Chats archivados',
      about: 'Acerca de',
      notifications: 'Notificaciones'
    },
    sections: {
      model: 'Modelo',
      chat: 'Chat',
      appearance: 'Apariencia',
      workspace: 'Espacio de trabajo',
      safety: 'Seguridad',
      memory: 'Memoria y contexto',
      voice: 'Voz',
      advanced: 'Avanzado'
    },
    modeOptions: {
      light: { label: 'Claro', description: 'Superficies de escritorio brillantes' },
      dark: { label: 'Oscuro', description: 'Espacio de trabajo de bajo brillo' },
      system: { label: 'Sistema', description: 'Seguir la apariencia del sistema' }
    },
    appearance: {
      title: 'Apariencia',
      intro:
        'Preferencias de visualización del escritorio. El modo controla el brillo; el tema controla la paleta de acentos.',
      colorMode: 'Modo de color',
      colorModeDesc: 'Elija un modo fijo o permita que Sara siga su sistema.',
      themeTitle: 'Tema',
      themeDesc: 'Solo paletas del escritorio.',
      installTitle: 'Instalar desde VS Code',
      installDesc:
        'Pegue un ID de extensión de Marketplace para convertir su tema en paleta.',
      installPlaceholder: 'publisher.extension',
      installButton: 'Instalar',
      installing: 'Instalando…',
      installError: 'No se pudo instalar ese tema.',
      removeTheme: 'Eliminar tema',
      importedBadge: 'Importado'
    },
    about: {
      heading: 'Sara Desktop',
      version: value => `Versión ${value}`,
      versionUnavailable: 'Versión no disponible',
      updates: 'Actualizaciones',
      checkNow: 'Comprobar ahora',
      checking: 'Comprobando…',
      seeWhatsNew: 'Ver novedades',
      releaseNotes: 'Notas de la versión',
      onLatest: 'Ya tiene la última versión.',
      never: 'nunca',
      justNow: 'justo ahora'
    },
    notifications: {
      title: 'Notificaciones',
      enableAll: 'Activar notificaciones',
      enableAllDesc: 'Interruptor general. Desactive para silenciar todas las notificaciones.',
      test: 'Enviar notificación de prueba',
      testTitle: 'Sara',
      testBody: 'Las notificaciones funcionan.',
      completionSoundTitle: 'Sonido de finalización',
      completionSoundDesc: 'Se reproduce cuando un agente termina.',
      completionSoundPreview: 'Vista previa'
    },
    config: {
      none: 'Ninguno',
      notSet: 'No establecido',
      loading: 'Cargando configuración de Sara...',
      emptyTitle: 'Nada que configurar',
      emptyDesc: 'Esta sección no tiene parámetros ajustables.',
      failedLoad: 'Error al cargar la configuración',
      autosaveFailed: 'Error al guardar automáticamente',
      imported: 'Configuración importada',
      invalidJson: 'JSON de configuración no válido'
    },
    model: {
      loading: 'Cargando configuración del modelo...',
      appliesDesc: 'Se aplica a nuevas sesiones.',
      provider: 'Proveedor',
      model: 'Modelo',
      applying: 'Aplicando...',
      defaultsLabel: 'Predeterminado',
      reasoning: 'Razonamiento',
      reasoningOff: 'Desactivado',
      defaultsFailed: 'Error al guardar modelos predeterminados'
    }
  },

  notifications: {
    region: 'Notificaciones',
    hide: 'Ocultar',
    show: 'Mostrar',
    more: count => `${count} más`,
    clearAll: 'Limpiar todo',
    dismiss: 'Descartar notificación',
    details: 'Detalles',
    copyDetail: 'Copiar detalle',
    copyDetailFailed: 'No se pudo copiar el detalle',
    updateSara: 'Actualizar Sara'
  },

  statusStack: {
    agents: 'Agentes',
    background: count => `${count} Fondo`,
    subagents: count => `${count} Subagente${count === 1 ? '' : 's'}`,
    todos: (done, total) => `Tareas ${done}/${total}`,
    running: 'Ejecutando',
    stop: 'Detener',
    dismiss: 'Descartar',
    exit: code => `código ${code}`
  },

  desktop: {
    sessionUnavailable: 'Sesión no disponible',
    createSessionFailed: 'No se pudo crear una nueva sesión',
    promptFailed: 'Error al ejecutar el prompt',
    stopFailed: 'Error al detener',
    regenerateFailed: 'Error al regenerar',
    editFailed: 'Error al editar',
    resumeFailed: 'Error al reanudar',
    deleteFailed: 'Error al eliminar',
    archived: 'Archivado',
    archiveFailed: 'Error al archivar',
    modelSwitchFailed: 'Error al cambiar de modelo',
    sessionExported: 'Sesión exportada',
    sessionExportFailed: 'No se pudo exportar la sesión',
    clipboard: 'Portapapeles',
    noClipboardImage: 'No hay imagen en el portapapeles',
    clipboardPasteFailed: 'Error al pegar',
    dropFiles: 'Soltar archivos'
  },

  assistant: {
    thread: {
      loadingSession: 'Cargando sesión',
      showEarlier: 'Mostrar mensajes anteriores',
      loadingResponse: 'Sara está cargando una respuesta',
      thinking: 'Pensando',
      today: time => `Hoy, ${time}`,
      yesterday: time => `Ayer, ${time}`,
      copy: 'Copiar',
      refresh: 'Actualizar',
      moreActions: 'Más acciones',
      dismissError: 'Descartar error',
      editMessage: 'Editar mensaje',
      scrollToBottom: 'Desplazarse al final',
      stop: 'Detener',
      restorePrevious: 'Restaurar punto anterior',
      restoreCheckpoint: 'Restaurar punto',
      sendEdited: 'Enviar mensaje editado',
      attachingFile: 'Adjuntando archivo…'
    },
    approval: {
      gatewayDisconnected: 'La puerta de enlace de Sara no está conectada',
      sendFailed: 'No se pudo enviar la respuesta',
      run: 'Ejecutar',
      command: 'Comando',
      reject: 'Rechazar',
      alwaysAllow: 'Permitir siempre'
    },
    tool: {
      code: 'Código',
      copyCode: 'Copiar código',
      copyOutput: 'Copiar salida',
      copyCommand: 'Copiar comando',
      copyContent: 'Copiar contenido',
      copyUrl: 'Copiar URL',
      copyResults: 'Copiar resultados',
      statusRunning: 'Ejecutando',
      statusError: 'Error',
      statusRecovered: 'Recuperado',
      statusDone: 'Hecho'
    }
  },

  errors: {
    genericFailure: 'Algo salió mal',
    boundaryTitle: 'Algo se rompió en la interfaz',
    boundaryDesc: 'La vista encontró un error inesperado. Sus chats están a salvo.',
    reloadWindow: 'Recargar ventana',
    openLogs: 'Abrir registros'
  },

  modelPicker: {
    title: 'Cambiar modelo',
    current: 'actual:',
    unknown: '(desconocido)',
    search: 'Filtrar proveedores y modelos',
    noModels: 'No se encontraron modelos',
    addProvider: 'Añadir proveedor',
    loadFailed: 'No se pudieron cargar los modelos',
    noAuthenticatedProviders: 'No hay proveedores autenticados.',
    pro: 'Pro',
    freeTier: 'Gratis',
    free: 'Gratis'
  },

  modelVisibility: {
    title: 'Modelos',
    search: 'Buscar modelos',
    noAuthenticatedProviders: 'No hay proveedores autenticados.',
    addProvider: 'Añadir proveedor…'
  },

  install: {
    oneTimeTitle: 'Sara necesita una instalación única',
    copyCommand: 'Copiar comando',
    viewDocs: 'Ver documentación de instalación',
    error: 'Error',
    cancelInstall: 'Cancelar instalación'
  }
})
