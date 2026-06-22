import { defineLocale } from './define-locale'

export const ko = defineLocale({
  common: {
    apply: '적용',
    back: '뒤로',
    save: '저장',
    saving: '저장 중…',
    cancel: '취소',
    change: '변경',
    choose: '선택',
    clear: '지우기',
    close: '닫기',
    collapse: '접기',
    confirm: '확인',
    connect: '연결',
    connecting: '연결 중',
    continue: '계속',
    copied: '복사됨',
    copy: '복사',
    copyFailed: '복사 실패',
    delete: '삭제',
    docs: '문서',
    done: '완료',
    error: '오류',
    failed: '실패',
    free: '무료',
    loading: '로딩 중…',
    notSet: '설정되지 않음',
    refresh: '새로고침',
    remove: '제거',
    replace: '교체',
    retry: '재시도',
    run: '실행',
    send: '보내기',
    set: '설정',
    skip: '건너뛰기',
    update: '업데이트',
    on: '켜짐',
    off: '꺼짐'
  },

  boot: {
    ready: 'Sara Desktop이 준비되었습니다',
    desktopBootFailedWithMessage: message => `데스크톱 부팅 실패: ${message}`,
    steps: {
      connectingGateway: '라이브 데스크톱 게이트웨이 연결 중',
      loadingSettings: 'Sara 설정 로딩 중',
      loadingSessions: '최근 세션 로딩 중',
      startingDesktopConnection: '데스크톱 연결 시작 중',
      startingSaraDesktop: 'Sara Desktop 시작 중…'
    },
    errors: {
      backgroundExited: 'Sara 백그라운드 프로세스가 종료되었습니다.',
      backgroundExitedDuringStartup: '시작 중 Sara 백그라운드 프로세스가 종료되었습니다.',
      backendStopped: '백엔드가 중지되었습니다',
      desktopBootFailed: '데스크톱 부팅 실패',
      gatewaySignInRequired: '게이트웨이 로그인 필요',
      ipcBridgeUnavailable: '데스크톱 IPC 브릿지를 사용할 수 없습니다.'
    },
    failure: {
      title: 'Sara를 시작할 수 없습니다',
      description:
        '백그라운드 게이트웨이가 작동하지 않습니다. 아래 복구 단계를 시도해보세요. 채팅이나 설정은 삭제되지 않습니다.',
      remoteTitle: '원격 게이트웨이 로그인 필요',
      remoteDescription:
        '원격 게이트웨이 세션이 만료되었습니다. 다시 로그인하여 재연결하세요. 채팅이나 설정은 삭제되지 않습니다.',
      retry: '재시도',
      repairInstall: '설치 복구',
      useLocalGateway: '로컬 게이트웨이 사용',
      openLogs: '로그 열기',
      repairHint: '복구는 설치 프로그램을 다시 실행하며, 새 기기에서는 몇 분이 소요될 수 있습니다.',
      remoteSignInHint: '게이트웨이 로그인 창을 엽니다. 대신 번들 백엔드를 사용하려면 로컬 게이트웨이를 선택하세요.',
      hideRecentLogs: '최근 로그 숨기기',
      showRecentLogs: '최근 로그 보기',
      signedInTitle: '로그인됨',
      signedInMessage: '원격 게이트웨이에 재연결 중…',
      signInIncompleteTitle: '로그인 불완전',
      signInIncompleteMessage: '인증이 완료되기 전에 로그인 창이 닫혔습니다.',
      signInFailed: '로그인 실패',
      signInToRemoteGateway: '원격 게이트웨이에 로그인',
      signInWithProvider: provider => `${provider}(으)로 로그인`,
      identityProvider: '귀하의 ID 제공자'
    }
  },

  language: {
    label: '언어',
    description: '데스크톱 인터페이스 언어를 선택하세요.',
    saving: '언어 저장 중…',
    saveError: '언어 업데이트 실패',
    switchTo: '언어 전환',
    searchPlaceholder: '언어 검색…',
    noResults: '검색 결과가 없습니다'
  },

  titlebar: {
    hideSidebar: '사이드바 숨기기',
    showSidebar: '사이드바 보이기',
    search: '검색',
    searchTitle: '세션, 보기 및 작업 검색',
    swapSidebarSides: '사이드바 위치 바꾸기',
    swapSidebarSidesTitle: '세션과 파일 브라우저 위치 바꾸기',
    hideRightSidebar: '오른쪽 사이드바 숨기기',
    showRightSidebar: '오른쪽 사이드바 보이기',
    muteHaptics: '햅틱 음소거',
    unmuteHaptics: '햅틱 음소거 해제',
    openSettings: '설정 열기',
    openKeybinds: '키보드 단축키'
  },

  sidebar: {
    nav: {
      'new-session': '새 세션',
      skills: '스킬 및 도구',
      messaging: '메시징',
      artifacts: '아티팩트',
      memory: '메모리'
    },
    searchAria: '세션 검색',
    searchPlaceholder: '세션 검색…',
    clearSearch: '검색 지우기',
    noMatch: query => `"${query}"와 일치하는 세션이 없습니다.`,
    results: '결과',
    pinned: '고정됨',
    sessions: '세션',
    cronJobs: '크론 작업',
    loading: '로딩 중…',
    loadMore: '더 불러오기',
    row: {
      pin: '고정',
      unpin: '고정 해제',
      copyId: 'ID 복사',
      export: '내보내기',
      rename: '이름 변경',
      archive: '보관',
      newWindow: '새 창',
      copyIdFailed: '세션 ID를 복사할 수 없습니다',
      sessionRunning: '세션 실행 중',
      needsInput: '입력 필요',
      waitingForAnswer: '답변을 기다리는 중',
      renamed: '이름이 변경되었습니다',
      renameFailed: '이름 변경 실패',
      renameTitle: '세션 이름 변경',
      renameDesc: '기억에 남는 제목을 입력하세요. 비우려면 비워두세요.',
      untitledPlaceholder: '제목 없는 세션',
      ageNow: '지금',
      ageDay: '일',
      ageHour: '시간',
      ageMin: '분'
    }
  },

  composer: {
    message: '메시지',
    wakingProfile: profile => `${profile} 깨우는 중…`,
    placeholderStarting: 'Sara 시작 중...',
    placeholderReconnecting: 'Sara에 재연결 중…',
    placeholderFollowUp: '후속 메시지 보내기',
    newSessionPlaceholders: [
      '무엇을 만들까요?',
      'Sara에게 작업을 지정하세요',
      '무엇을 하고 계신가요?',
      '필요한 것을 설명해주세요',
      '무엇부터 시작할까요?',
      '무엇이든 물어보세요',
      '목표부터 정해볼까요'
    ],
    followUpPlaceholders: [
      '후속 메시지 보내기',
      '더 많은 맥락 추가',
      '요청 구체화',
      '다음 단계는?',
      '계속 진행',
      '더 발전시키기',
      '조정하거나 계속하기'
    ],
    startVoice: '음성 대화 시작',
    queueMessage: '메시지 대기열에 추가',
    steer: '현재 실행 제어',
    stop: '중지',
    send: '보내기',
    speaking: '말하는 중',
    transcribing: '변환 중',
    thinking: '생각하는 중',
    muted: '음소거됨',
    listening: '듣는 중',
    muteMic: '마이크 음소거',
    unmuteMic: '마이크 음소거 해제',
    stopListening: '듣기 중지 및 보내기',
    stopShort: '중지',
    endConversation: '음성 대화 종료',
    endShort: '종료',
    attachLabel: '첨부',
    files: '파일…',
    folder: '폴더…',
    images: '이미지…',
    pasteImage: '이미지 붙여넣기',
    url: 'URL…',
    promptSnippets: '프롬프트 스니펫…',
    dropFiles: '파일을 끌어다 놓으세요',
    dropSession: '이 채팅을 연결하려면 드롭',
    snippetsTitle: '프롬프트 스니펫',
    snippetsDesc: '컴포저에 넣을 시작 프롬프트를 선택하세요.',
    snippets: {
      codeReview: {
        label: '코드 리뷰',
        description: '현재 변경사항에서 회귀, 누락된 엣지 케이스, 빠진 테스트를 감사합니다.',
        text: '버그, 회귀, 빠진 테스트가 있는지 리뷰해주세요.'
      },
      implementationPlan: {
        label: '구현 계획',
        description: '코드를 건드리기 전에 접근 방식을 개략적으로 설명하여 diff가 집중되도록 합니다.',
        text: '코드를 변경하기 전에 간결한 구현 계획을 세워주세요.'
      },
      explainThis: {
        label: '설명',
        description: '선택한 코드가 어떻게 작동하는지 설명하고 핵심 파일을 알려줍니다.',
        text: '이것이 어떻게 작동하는지 설명하고 핵심 파일을 알려주세요.'
      }
    }
  },

  shell: {
    windowControls: '창 컨트롤',
    paneControls: '패널 컨트롤',
    appControls: '앱 컨트롤',
    modelMenu: {
      search: '모델 검색',
      noModels: '모델을 찾을 수 없음',
      editModels: '모델 편집…',
      refreshModels: '모델 새로고침',
      fast: '빠름',
      medium: '중간'
    },
    modelOptions: {
      noOptions: '이 모델에 옵션 없음',
      options: '옵션',
      thinking: '생각',
      fast: '빠름',
      effort: '노력',
      minimal: '최소',
      low: '낮음',
      medium: '중간',
      high: '높음',
      max: '최대',
      updateFailed: '모델 옵션 업데이트 실패',
      fastFailed: '빠른 모드 업데이트 실패'
    },
    gatewayMenu: {
      gateway: '게이트웨이',
      connected: '연결됨',
      connecting: '연결 중',
      offline: '오프라인',
      disconnected: '연결 끊김',
      openSystem: '시스템 패널 열기',
      recentActivity: '최근 활동',
      viewAllLogs: '모든 로그 보기 →',
      messagingPlatforms: '메시징 플랫폼'
    },
    statusbar: {
      unknown: '알 수 없음',
      restart: '재시작',
      update: '업데이트',
      updateInProgress: '업데이트 진행 중',
      closeCommandCenter: '명령 센터 닫기',
      openCommandCenter: '명령 센터 열기',
      showTerminal: '터미널 보기',
      hideTerminal: '터미널 숨기기',
      gateway: '게이트웨이',
      gatewayReady: '준비',
      gatewayNeedsSetup: '설정 필요',
      gatewayChecking: '확인 중',
      gatewayConnecting: '연결 중',
      gatewayOffline: '오프라인',
      gatewayRestarting: '재시작 중…',
      gatewayTitle: 'Sara 추론 게이트웨이 상태',
      agents: '에이전트',
      closeAgents: '에이전트 닫기',
      openAgents: '에이전트 열기',
      modelNone: '없음',
      noModel: '모델 없음',
      switchModel: '모델 전환',
      openModelPicker: '모델 선택기 열기'
    }
  },

  settings: {
    closeSettings: '설정 닫기',
    exportConfig: '설정 내보내기',
    importConfig: '설정 가져오기',
    resetToDefaults: '기본값으로 초기화',
    resetConfirm: '모든 설정을 기본값으로 초기화할까요?',
    exportFailed: '내보내기 실패',
    resetFailed: '초기화 실패',
    nav: {
      providers: '제공자',
      providerAccounts: '계정',
      providerApiKeys: 'API 키',
      gateway: '게이트웨이',
      apiKeys: '도구 및 키',
      keysTools: '도구',
      keysSettings: '설정',
      mcp: 'MCP',
      archivedChats: '보관된 채팅',
      about: '정보',
      notifications: '알림'
    },
    sections: {
      model: '모델',
      chat: '채팅',
      appearance: '외관',
      workspace: '작업 공간',
      safety: '안전',
      memory: '메모리 및 컨텍스트',
      voice: '음성',
      advanced: '고급'
    },
    modeOptions: {
      light: { label: '라이트', description: '밝은 데스크톱 화면' },
      dark: { label: '다크', description: '눈에 편한 작업 공간' },
      system: { label: '시스템', description: 'OS 외관 설정 따르기' }
    },
    appearance: {
      title: '외관',
      intro:
        '데스크톱 전용 표시 설정입니다. 모드는 밝기를 제어하고, 테마는 강조 팔레트와 채팅 화면 스타일을 제어합니다.',
      colorMode: '색상 모드',
      colorModeDesc: '고정 모드를 선택하거나 시스템 설정을 따르도록 할 수 있습니다.',
      themeTitle: '테마',
      themeDesc: '데스크톱 팔레트만 해당됩니다. 선택한 모드가 위에 적용됩니다.',
      installTitle: 'VS Code에서 설치',
      installDesc:
        '마켓플레이스 확장 ID를 붙여넣어 색상 테마를 데스크톱 팔레트로 변환하세요.',
      installPlaceholder: 'publisher.extension',
      installButton: '설치',
      installing: '설치 중…',
      installError: '해당 테마를 설치할 수 없습니다.',
      removeTheme: '테마 제거',
      importedBadge: '가져옴'
    },
    about: {
      heading: 'Sara Desktop',
      version: value => `버전 ${value}`,
      versionUnavailable: '버전 정보 없음',
      updates: '업데이트',
      checkNow: '지금 확인',
      checking: '확인 중…',
      seeWhatsNew: '새로운 기능 보기',
      releaseNotes: '릴리스 노트',
      onLatest: '최신 버전입니다.',
      never: '없음',
      justNow: '방금'
    },
    notifications: {
      title: '알림',
      enableAll: '알림 활성화',
      enableAllDesc: '마스터 스위치. 아래의 모든 알림을 끄려면 비활성화하세요.',
      test: '테스트 알림 보내기',
      testTitle: 'Sara',
      testBody: '알림이 작동 중입니다.',
      completionSoundTitle: '완료음',
      completionSoundDesc: '에이전트 작업이 완료되면 재생됩니다. 여기서 사전 설정을 선택하고 미리 들을 수 있습니다.',
      completionSoundPreview: '미리 듣기'
    },
    config: {
      none: '없음',
      notSet: '설정되지 않음',
      loading: 'Sara 설정 로딩 중...',
      emptyTitle: '설정할 항목이 없습니다',
      emptyDesc: '이 섹션에는 조정 가능한 설정이 없습니다.',
      failedLoad: '설정을 불러오지 못했습니다',
      autosaveFailed: '자동 저장 실패',
      imported: '설정을 가져왔습니다',
      invalidJson: '잘못된 JSON 설정'
    },
    model: {
      loading: '모델 설정 로딩 중...',
      appliesDesc: '새 세션에 적용됩니다. 컴포저의 모델 선택기를 사용하여 활성 채팅을 전환할 수 있습니다.',
      provider: '제공자',
      model: '모델',
      applying: '적용 중...',
      defaultsLabel: '기본값',
      reasoning: '추론',
      reasoningOff: '끄기',
      defaultsFailed: '모델 기본값 저장 실패'
    }
  },

  notifications: {
    region: '알림',
    hide: '숨기기',
    show: '보기',
    more: count => `${count}개 더`,
    clearAll: '모두 지우기',
    dismiss: '알림 닫기',
    details: '세부사항',
    copyDetail: '세부사항 복사',
    copyDetailFailed: '알림 세부사항을 복사할 수 없습니다',
    updateSara: 'Sara 업데이트'
  },

  statusStack: {
    agents: '에이전트',
    background: count => `${count} 백그라운드`,
    subagents: count => `서브에이전트 ${count}개`,
    todos: (done, total) => `작업 ${done}/${total}`,
    running: '실행 중',
    stop: '중지',
    dismiss: '닫기',
    exit: code => `종료 코드 ${code}`
  },

  desktop: {
    sessionUnavailable: '세션을 사용할 수 없음',
    createSessionFailed: '새 세션을 만들 수 없습니다',
    promptFailed: '프롬프트 실패',
    profileStatus: current => `프로필: ${current}.`,
    stopFailed: '중지 실패',
    regenerateFailed: '재생성 실패',
    editFailed: '편집 실패',
    resumeFailed: '재개 실패',
    deleteFailed: '삭제 실패',
    archived: '보관됨',
    archiveFailed: '보관 실패',
    modelSwitchFailed: '모델 전환 실패',
    sessionExported: '세션 내보내기 완료',
    sessionExportFailed: '세션을 내보낼 수 없습니다',
    clipboard: '클립보드',
    noClipboardImage: '클립보드에 이미지가 없습니다',
    clipboardPasteFailed: '클립보드 붙여넣기 실패',
    dropFiles: '파일 끌어다 놓기'
  },

  assistant: {
    thread: {
      loadingSession: '세션 로딩 중',
      showEarlier: '이전 메시지 보기',
      loadingResponse: 'Sara가 응답을 로딩 중입니다',
      thinking: '생각하는 중',
      today: time => `오늘, ${time}`,
      yesterday: time => `어제, ${time}`,
      copy: '복사',
      refresh: '새로고침',
      moreActions: '더 많은 작업',
      dismissError: '오류 닫기',
      editMessage: '메시지 편집',
      scrollToBottom: '맨 아래로 스크롤',
      stop: '중지',
      restorePrevious: '이전 체크포인트 복원',
      restoreCheckpoint: '체크포인트 복원',
      sendEdited: '수정된 메시지 보내기',
      attachingFile: '파일 첨부 중…'
    },
    approval: {
      gatewayDisconnected: 'Sara 게이트웨이가 연결되지 않았습니다',
      sendFailed: '승인 응답을 보낼 수 없습니다',
      run: '실행',
      command: '명령',
      reject: '거부',
      alwaysAllow: '항상 허용'
    },
    tool: {
      code: '코드',
      copyCode: '코드 복사',
      copyOutput: '출력 복사',
      copyCommand: '명령 복사',
      copyContent: '내용 복사',
      copyUrl: 'URL 복사',
      copyResults: '결과 복사',
      statusRunning: '실행 중',
      statusError: '오류',
      statusRecovered: '복구됨',
      statusDone: '완료'
    }
  },

  errors: {
    genericFailure: '문제가 발생했습니다',
    boundaryTitle: '인터페이스에 문제가 발생했습니다',
    boundaryDesc: '보기에 예상치 못한 오류가 발생했습니다. 채팅과 설정은 안전합니다.',
    reloadWindow: '창 다시 로드',
    openLogs: '로그 열기'
  },

  modelPicker: {
    title: '모델 전환',
    current: '현재:',
    unknown: '(알 수 없음)',
    search: '제공자 및 모델 필터',
    noModels: '모델을 찾을 수 없음',
    addProvider: '제공자 추가',
    loadFailed: '모델을 불러올 수 없음',
    noAuthenticatedProviders: '인증된 제공자가 없습니다.',
    pro: 'Pro',
    freeTier: '무료 등급',
    free: '무료'
  },

  modelVisibility: {
    title: '모델',
    search: '모델 검색',
    noAuthenticatedProviders: '인증된 제공자가 없습니다.',
    addProvider: '제공자 추가…'
  },

  install: {
    oneTimeTitle: 'Sara에 일회성 설치가 필요합니다',
    copyCommand: '명령 복사',
    viewDocs: '설치 문서 보기',
    error: '오류',
    cancelInstall: '설치 취소'
  }
})
