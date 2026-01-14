/**
 * UI Store (Zustand)
 *
 * Manages UI state including panel visibility, sizes, and theme.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ============================================================================
// Panel Types
// ============================================================================

export type PanelId = 'sidebar' | 'agentPanel' | 'terminal' | 'output';

export type ActivityBarItem =
  | 'explorer'
  | 'search'
  | 'sourceControl'
  | 'extensions'
  | 'settings';

// ============================================================================
// Store State
// ============================================================================

interface UIState {
  // Panel visibility
  sidebarVisible: boolean;
  agentPanelVisible: boolean;
  terminalVisible: boolean;
  outputVisible: boolean;
  commandPaletteVisible: boolean;

  // Panel sizes (in pixels)
  sidebarWidth: number;
  agentPanelWidth: number;
  terminalHeight: number;

  // Activity bar
  activeActivityItem: ActivityBarItem;

  // Theme
  theme: 'dark' | 'light';

  // Window state
  isMaximized: boolean;

  // Notifications
  notifications: Notification[];
}

// ============================================================================
// Notification Type
// ============================================================================

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  timestamp: number;
  autoDismiss?: boolean;
  duration?: number;
}

// ============================================================================
// Store Actions
// ============================================================================

interface UIActions {
  // Panel visibility
  toggleSidebar: () => void;
  toggleAgentPanel: () => void;
  toggleTerminal: () => void;
  toggleOutput: () => void;
  showPanel: (panel: PanelId) => void;
  hidePanel: (panel: PanelId) => void;

  // Command palette
  showCommandPalette: () => void;
  hideCommandPalette: () => void;
  toggleCommandPalette: () => void;

  // Panel sizes
  setSidebarWidth: (width: number) => void;
  setAgentPanelWidth: (width: number) => void;
  setTerminalHeight: (height: number) => void;

  // Activity bar
  setActiveActivityItem: (item: ActivityBarItem) => void;

  // Theme
  setTheme: (theme: 'dark' | 'light') => void;
  toggleTheme: () => void;

  // Window state
  setMaximized: (maximized: boolean) => void;

  // Notifications
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;

  // Utility
  reset: () => void;
}

// ============================================================================
// Initial State
// ============================================================================

const initialState: UIState = {
  sidebarVisible: true,
  agentPanelVisible: true,
  terminalVisible: false,
  outputVisible: false,
  commandPaletteVisible: false,
  sidebarWidth: 240,
  agentPanelWidth: 360,
  terminalHeight: 200,
  activeActivityItem: 'explorer',
  theme: 'dark',
  isMaximized: false,
  notifications: [],
};

// ============================================================================
// Store Implementation
// ============================================================================

export const useUIStore = create<UIState & UIActions>()(
  persist(
    (set, get) => ({
      ...initialState,

      // ======================================================================
      // Panel Visibility
      // ======================================================================

      toggleSidebar: () => {
        set((state) => ({ sidebarVisible: !state.sidebarVisible }));
      },

      toggleAgentPanel: () => {
        set((state) => ({ agentPanelVisible: !state.agentPanelVisible }));
      },

      toggleTerminal: () => {
        set((state) => ({ terminalVisible: !state.terminalVisible }));
      },

      toggleOutput: () => {
        set((state) => ({ outputVisible: !state.outputVisible }));
      },

      showPanel: (panel) => {
        switch (panel) {
          case 'sidebar':
            set({ sidebarVisible: true });
            break;
          case 'agentPanel':
            set({ agentPanelVisible: true });
            break;
          case 'terminal':
            set({ terminalVisible: true });
            break;
          case 'output':
            set({ outputVisible: true });
            break;
        }
      },

      hidePanel: (panel) => {
        switch (panel) {
          case 'sidebar':
            set({ sidebarVisible: false });
            break;
          case 'agentPanel':
            set({ agentPanelVisible: false });
            break;
          case 'terminal':
            set({ terminalVisible: false });
            break;
          case 'output':
            set({ outputVisible: false });
            break;
        }
      },

      // ======================================================================
      // Command Palette
      // ======================================================================

      showCommandPalette: () => {
        set({ commandPaletteVisible: true });
      },

      hideCommandPalette: () => {
        set({ commandPaletteVisible: false });
      },

      toggleCommandPalette: () => {
        set((state) => ({ commandPaletteVisible: !state.commandPaletteVisible }));
      },

      // ======================================================================
      // Panel Sizes
      // ======================================================================

      setSidebarWidth: (width) => {
        // Clamp to reasonable bounds
        const clamped = Math.max(150, Math.min(500, width));
        set({ sidebarWidth: clamped });
      },

      setAgentPanelWidth: (width) => {
        const clamped = Math.max(280, Math.min(600, width));
        set({ agentPanelWidth: clamped });
      },

      setTerminalHeight: (height) => {
        const clamped = Math.max(100, Math.min(400, height));
        set({ terminalHeight: clamped });
      },

      // ======================================================================
      // Activity Bar
      // ======================================================================

      setActiveActivityItem: (item) => {
        const state = get();

        // If clicking same item, toggle sidebar
        if (item === state.activeActivityItem && state.sidebarVisible) {
          set({ sidebarVisible: false });
        } else {
          set({ activeActivityItem: item, sidebarVisible: true });
        }
      },

      // ======================================================================
      // Theme
      // ======================================================================

      setTheme: (theme) => {
        set({ theme });
        // Apply to document
        document.documentElement.classList.toggle('dark', theme === 'dark');
        document.documentElement.classList.toggle('light', theme === 'light');
      },

      toggleTheme: () => {
        const newTheme = get().theme === 'dark' ? 'light' : 'dark';
        get().setTheme(newTheme);
      },

      // ======================================================================
      // Window State
      // ======================================================================

      setMaximized: (maximized) => {
        set({ isMaximized: maximized });
      },

      // ======================================================================
      // Notifications
      // ======================================================================

      addNotification: (notification) => {
        const newNotification: Notification = {
          ...notification,
          id: crypto.randomUUID(),
          timestamp: Date.now(),
        };

        set((state) => ({
          notifications: [...state.notifications, newNotification],
        }));

        // Auto-dismiss if enabled
        if (notification.autoDismiss !== false) {
          const duration = notification.duration || 5000;
          setTimeout(() => {
            get().removeNotification(newNotification.id);
          }, duration);
        }
      },

      removeNotification: (id) => {
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        }));
      },

      clearNotifications: () => {
        set({ notifications: [] });
      },

      // ======================================================================
      // Utility
      // ======================================================================

      reset: () => {
        set(initialState);
      },
    }),
    {
      name: 'pulse-ui-storage',
      partialize: (state) => ({
        sidebarVisible: state.sidebarVisible,
        agentPanelVisible: state.agentPanelVisible,
        sidebarWidth: state.sidebarWidth,
        agentPanelWidth: state.agentPanelWidth,
        terminalHeight: state.terminalHeight,
        theme: state.theme,
      }),
    }
  )
);

// ============================================================================
// Selectors
// ============================================================================

export const selectHasNotifications = (state: UIState) =>
  state.notifications.length > 0;

export const selectUnreadNotificationCount = (state: UIState) =>
  state.notifications.length;
