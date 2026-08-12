import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// MAS execution state
export const useMASStore = create(
  persist(
    (set, get) => ({
      // Current execution state
      isExecuting: false,
      currentRunId: null,
      progress: [],
      result: null,
      error: null,

      // History
      history: [],

      // Actions
      startExecution: (runId) => {
        set({
          isExecuting: true,
          currentRunId: runId,
          progress: [],
          result: null,
          error: null,
        });
      },

      addProgress: (progressData) => {
        set((state) => ({
          progress: [...state.progress, progressData],
        }));
      },

      setResult: (result) => {
        const { currentRunId, history } = get();
        set({
          isExecuting: false,
          result,
          history: [
            {
              runId: currentRunId,
              result,
              timestamp: new Date().toISOString(),
            },
            ...history.slice(0, 49), // Keep last 50
          ],
        });
      },

      setError: (error) => {
        set({
          isExecuting: false,
          error,
        });
      },

      reset: () => {
        set({
          isExecuting: false,
          currentRunId: null,
          progress: [],
          result: null,
          error: null,
        });
      },

      clearHistory: () => {
        set({ history: [] });
      },
    }),
    {
      name: 'mas-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ history: state.history }),
    }
  )
);

// Skill state
export const useSkillStore = create((set) => ({
  skills: [],
  selectedSkill: null,
  recommendedSkill: null,
  isLoading: false,
  error: null,

  setSkills: (skills) => set({ skills }),
  setSelectedSkill: (skill) => set({ selectedSkill: skill }),
  setRecommendedSkill: (skill) => set({ recommendedSkill: skill }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      selectedSkill: null,
      recommendedSkill: null,
      error: null,
    }),
}));

// Settings state
export const useSettingsStore = create(
  persist(
    (set) => ({
      llmProvider: 'openai',
      apiBaseUrl: 'http://127.0.0.1:8000',
      theme: 'light',
      enableCache: true,
      useLangGraph: true,

      setLLMProvider: (provider) => set({ llmProvider: provider }),
      setApiBaseUrl: (url) => set({ apiBaseUrl: url }),
      setTheme: (theme) => set({ theme: theme }),
      setEnableCache: (enable) => set({ enableCache: enable }),
      setUseLangGraph: () => set({ useLangGraph: true }),
    }),
    {
      name: 'settings-storage',
      storage: createJSONStorage(() => localStorage),
      merge: (persistedState, currentState) => ({
        ...currentState,
        ...(persistedState || {}),
        useLangGraph: true,
      }),
    }
  )
);

// UI state
export const useUIStore = create((set) => ({
  sidebarOpen: true,
  activeTab: 'generate',
  notifications: [],

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActiveTab: (tab) => set({ activeTab: tab }),
  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        { id: Date.now(), ...notification },
      ],
    })),
  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
  clearNotifications: () => set({ notifications: [] }),
}));

const DEFAULT_RUNTIME_CONSTRAINTS = {
  standards: 'ISO 19650 参考 / ISO 27001 / 项目验收规则',
  performance: '模型交付可验证，工地遥测可回放',
  language: 'Python 优先，按需补 C++ 伪代码',
  deliveryFormat: '伪代码 + 可运行代码 + 企业报告 + 证据包',
};

// Runtime Console draft state. It intentionally keeps stable program ids such as
// `stream` and `execute` unchanged while exposing Chinese-first labels in views.
export const useRunDraftStore = create(
  persist(
    (set) => ({
      requirement: '',
      constraints: DEFAULT_RUNTIME_CONSTRAINTS,
      runMode: 'stream',
      allowAutoPatch: true,
      maxRegressionRounds: 1,
      evidenceEnhanced: true,

      setRequirement: (requirement) => set({ requirement }),
      setConstraint: (key, value) =>
        set((state) => ({
          constraints: {
            ...(state.constraints || DEFAULT_RUNTIME_CONSTRAINTS),
            [key]: value,
          },
        })),
      setRunMode: (runMode) => set({ runMode }),
      setAllowAutoPatch: (allowAutoPatch) => set({ allowAutoPatch }),
      setMaxRegressionRounds: (maxRegressionRounds) => set({ maxRegressionRounds }),
      setEvidenceEnhanced: (evidenceEnhanced) => set({ evidenceEnhanced }),
      hydrateFromApp: (snapshot = {}) =>
        set((state) => ({
          requirement: snapshot.requirement ?? state.requirement,
          runMode: snapshot.streaming === false ? 'execute' : state.runMode || 'stream',
          maxRegressionRounds: snapshot.maxRegressionRounds ?? state.maxRegressionRounds,
        })),
    }),
    {
      name: 'runtime-run-draft-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

export const useRunSessionStore = create((set) => ({
  activeRunId: '',
  caseId: '',
  status: 'idle',
  startedAt: '',
  latestEngineLabel: '',
  lastResultAt: '',

  hydrateFromApp: (snapshot = {}) =>
    set((state) => ({
      activeRunId: snapshot.activeRunId ?? state.activeRunId,
      caseId: snapshot.caseId ?? state.caseId,
      status: snapshot.loading ? 'running' : snapshot.result ? 'finished' : state.status || 'idle',
      startedAt: snapshot.loading && !state.startedAt ? new Date().toISOString() : state.startedAt,
      latestEngineLabel: snapshot.latestEngineLabel ?? state.latestEngineLabel,
      lastResultAt: snapshot.result ? new Date().toISOString() : state.lastResultAt,
    })),
  resetSession: () =>
    set({
      activeRunId: '',
      status: 'idle',
      startedAt: '',
      lastResultAt: '',
    }),
}));

export const useStageConsoleStore = create((set) => ({
  selectedStage: 'analyst',
  stages: [],
  events: [],

  setSelectedStage: (selectedStage) => set({ selectedStage }),
  hydrateFromApp: (snapshot = {}) =>
    set((state) => ({
      stages: Array.isArray(snapshot.workflowProgress) ? snapshot.workflowProgress : state.stages,
      events: Array.isArray(snapshot.events) ? snapshot.events.slice(-120) : state.events,
      selectedStage:
        state.selectedStage ||
        (Array.isArray(snapshot.workflowProgress) && snapshot.workflowProgress[0]?.phase) ||
        'analyst',
    })),
}));

export const useAttackLoopStore = create((set) => ({
  selectedRoundId: '',
  loopStatus: 'idle',
  rounds: [],
  telemetry: [],
  findings: [],

  setSelectedRoundId: (selectedRoundId) => set({ selectedRoundId }),
  hydrateFromApp: (snapshot = {}) =>
    set((state) => {
      const rounds = Array.isArray(snapshot.rounds) ? snapshot.rounds : state.rounds;
      return {
        rounds,
        loopStatus: snapshot.loopStatus || (rounds.length ? 'observed' : state.loopStatus),
        telemetry: Array.isArray(snapshot.telemetry) ? snapshot.telemetry.slice(-80) : state.telemetry,
        findings: Array.isArray(snapshot.findings) ? snapshot.findings : state.findings,
        selectedRoundId: state.selectedRoundId || String(rounds[0]?.round_id || rounds[0]?.id || ''),
      };
    }),
}));
