/**
 * Editor Store (Zustand)
 *
 * Manages file state, tabs, patches, and diff preview mode.
 * Handles the "dual-state" problem of user edits vs agent patches.
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type { FileState, EditorTab, PendingPatch } from '@/types/editor';
import { getLanguageFromPath } from '@/types/editor';

// ============================================================================
// Store State
// ============================================================================

interface EditorState {
  // Open files (path -> FileState)
  files: Map<string, FileState>;

  // Open tabs (ordered)
  tabs: EditorTab[];

  // Currently active tab path
  activeFilePath: string | null;

  // Path of file in diff preview mode (if any)
  diffPreviewPath: string | null;

  // Pending patches awaiting approval
  pendingPatches: Map<string, PendingPatch>;

  // Scroll positions per file (for restoration)
  scrollPositions: Map<string, { top: number; left: number }>;
}

// ============================================================================
// Store Actions
// ============================================================================

interface EditorActions {
  // File operations
  openFile: (path: string, content: string, options?: { isPreview?: boolean }) => void;
  closeFile: (path: string) => void;
  updateFileContent: (path: string, content: string) => void;
  saveFile: (path: string) => Promise<void>;
  markFileSaved: (path: string, content: string) => void;

  // Tab operations
  setActiveFile: (path: string | null) => void;
  reorderTabs: (fromIndex: number, toIndex: number) => void;
  promotePreviewTab: (path: string) => void;

  // Patch operations (for approval flow)
  addPendingPatch: (patch: Omit<PendingPatch, 'status'>) => void;
  approvePatch: (patchId: string) => void;
  denyPatch: (patchId: string) => void;
  clearPendingPatches: (runId: string) => void;
  getPatchForFile: (filePath: string) => PendingPatch | undefined;

  // Diff preview mode
  enterDiffPreview: (filePath: string) => void;
  exitDiffPreview: () => void;

  // Conflict detection
  hasConflict: (patchId: string) => boolean;

  // Scroll position
  setScrollPosition: (path: string, top: number, left: number) => void;
  getScrollPosition: (path: string) => { top: number; left: number } | undefined;

  // Utility
  getFile: (path: string) => FileState | undefined;
  isDirty: (path: string) => boolean;
  hasUnsavedChanges: () => boolean;
  reset: () => void;
}

// ============================================================================
// Initial State
// ============================================================================

const initialState: EditorState = {
  files: new Map(),
  tabs: [],
  activeFilePath: null,
  diffPreviewPath: null,
  pendingPatches: new Map(),
  scrollPositions: new Map(),
};

// ============================================================================
// Store Implementation
// ============================================================================

export const useEditorStore = create<EditorState & EditorActions>()(
  subscribeWithSelector((set, get) => ({
    ...initialState,

    // ========================================================================
    // File Operations
    // ========================================================================

    openFile: (path, content, options = { isPreview: true }) => {
      set((state) => {
        const files = new Map(state.files);
        const tabs = [...state.tabs];
        const isPreview = options.isPreview ?? true;

        // Check if file already open
        const existingTabIndex = tabs.findIndex((t) => t.path === path);
        if (existingTabIndex >= 0) {
          // File is already open - just activate it
          // If opening as permanent (not preview), promote the tab
          if (!isPreview && tabs[existingTabIndex].isPreview) {
            tabs[existingTabIndex] = { ...tabs[existingTabIndex], isPreview: false };
            return { tabs, activeFilePath: path };
          }
          return { activeFilePath: path };
        }

        // Create new file state
        const fileState: FileState = {
          path,
          content,
          originalContent: content,
          version: 1,
          lastModified: Date.now(),
          isDirty: false,
          language: getLanguageFromPath(path),
        };
        files.set(path, fileState);

        const fileName = path.split(/[\\/]/).pop() || path;

        const newTab: EditorTab = {
          path,
          name: fileName,
          isDirty: false,
          isPreview: isPreview,
        };

        // Only replace preview tab if opening as preview
        if (isPreview) {
          const previewIndex = tabs.findIndex((t) => t.isPreview);
          if (previewIndex >= 0) {
            // Replace existing preview tab
            const oldPreviewPath = tabs[previewIndex].path;
            files.delete(oldPreviewPath);
            tabs[previewIndex] = newTab;
          } else {
            // No preview tab exists, add new one
            tabs.push(newTab);
          }
        } else {
          // Opening as permanent tab - always add new tab
          tabs.push(newTab);
        }

        return {
          files,
          tabs,
          activeFilePath: path,
        };
      });
    },

    closeFile: (path) => {
      set((state) => {
        const files = new Map(state.files);
        const tabs = state.tabs.filter((t) => t.path !== path);
        const scrollPositions = new Map(state.scrollPositions);

        files.delete(path);
        scrollPositions.delete(path);

        // Determine new active file
        let activeFilePath = state.activeFilePath;
        if (activeFilePath === path) {
          // Activate next tab or previous if last
          const oldIndex = state.tabs.findIndex((t) => t.path === path);
          if (tabs.length > 0) {
            const newIndex = Math.min(oldIndex, tabs.length - 1);
            activeFilePath = tabs[newIndex]?.path || null;
          } else {
            activeFilePath = null;
          }
        }

        // Exit diff preview if closing that file
        const diffPreviewPath =
          state.diffPreviewPath === path ? null : state.diffPreviewPath;

        return {
          files,
          tabs,
          activeFilePath,
          diffPreviewPath,
          scrollPositions,
        };
      });
    },

    updateFileContent: (path, content) => {
      set((state) => {
        const files = new Map(state.files);
        const tabs = [...state.tabs];
        const file = files.get(path);

        if (!file) return state;

        const isDirty = content !== file.originalContent;

        files.set(path, {
          ...file,
          content,
          version: file.version + 1,
          lastModified: Date.now(),
          isDirty,
        });

        // Update tab dirty state
        const tabIndex = tabs.findIndex((t) => t.path === path);
        if (tabIndex >= 0) {
          tabs[tabIndex] = { ...tabs[tabIndex], isDirty };
        }

        return { files, tabs };
      });
    },

    saveFile: async (path) => {
      const file = get().files.get(path);
      if (!file) return;

      try {
        await window.pulseAPI.fs.writeFile(path, file.content);
        get().markFileSaved(path, file.content);
      } catch (error) {
        console.error('Failed to save file:', error);
        throw error;
      }
    },

    markFileSaved: (path, content) => {
      set((state) => {
        const files = new Map(state.files);
        const tabs = [...state.tabs];
        const file = files.get(path);

        if (!file) return state;

        files.set(path, {
          ...file,
          content,
          originalContent: content,
          isDirty: false,
        });

        const tabIndex = tabs.findIndex((t) => t.path === path);
        if (tabIndex >= 0) {
          tabs[tabIndex] = { ...tabs[tabIndex], isDirty: false };
        }

        return { files, tabs };
      });
    },

    // ========================================================================
    // Tab Operations
    // ========================================================================

    setActiveFile: (path) => {
      set({ activeFilePath: path });
    },

    reorderTabs: (fromIndex, toIndex) => {
      set((state) => {
        const tabs = [...state.tabs];
        const [removed] = tabs.splice(fromIndex, 1);
        tabs.splice(toIndex, 0, removed);
        return { tabs };
      });
    },

    promotePreviewTab: (path) => {
      set((state) => {
        const tabs = state.tabs.map((t) =>
          t.path === path ? { ...t, isPreview: false } : t
        );
        return { tabs };
      });
    },

    // ========================================================================
    // Patch Operations
    // ========================================================================

    addPendingPatch: (patch) => {
      set((state) => {
        const pendingPatches = new Map(state.pendingPatches);
        pendingPatches.set(patch.id, {
          ...patch,
          status: 'pending',
        });
        return { pendingPatches };
      });
    },

    approvePatch: (patchId) => {
      const patch = get().pendingPatches.get(patchId);
      if (!patch || patch.status !== 'pending') return;

      set((state) => {
        const pendingPatches = new Map(state.pendingPatches);
        const files = new Map(state.files);
        const tabs = [...state.tabs];

        // Mark patch as approved
        pendingPatches.set(patchId, { ...patch, status: 'approved' });

        // Apply patch to file
        const file = files.get(patch.filePath);
        if (file) {
          files.set(patch.filePath, {
            ...file,
            content: patch.patchedContent,
            originalContent: patch.patchedContent, // Mark as saved
            version: file.version + 1,
            lastModified: Date.now(),
            isDirty: false,
          });

          // Update tab
          const tabIndex = tabs.findIndex((t) => t.path === patch.filePath);
          if (tabIndex >= 0) {
            tabs[tabIndex] = { ...tabs[tabIndex], isDirty: false };
          }
        }

        return {
          pendingPatches,
          files,
          tabs,
          diffPreviewPath: null, // Exit diff preview
        };
      });

      // Save file to disk
      window.pulseAPI.fs.writeFile(patch.filePath, patch.patchedContent).catch((err) => {
        console.error('Failed to save patched file:', err);
      });
    },

    denyPatch: (patchId) => {
      set((state) => {
        const pendingPatches = new Map(state.pendingPatches);
        const patch = pendingPatches.get(patchId);

        if (patch) {
          pendingPatches.set(patchId, { ...patch, status: 'denied' });
        }

        return {
          pendingPatches,
          diffPreviewPath: null, // Exit diff preview
        };
      });
    },

    clearPendingPatches: (runId) => {
      set((state) => {
        const pendingPatches = new Map(state.pendingPatches);
        for (const [id, patch] of pendingPatches) {
          if (patch.runId === runId) {
            pendingPatches.delete(id);
          }
        }
        return { pendingPatches };
      });
    },

    getPatchForFile: (filePath) => {
      const patches = get().pendingPatches;
      for (const patch of patches.values()) {
        if (patch.filePath === filePath && patch.status === 'pending') {
          return patch;
        }
      }
      return undefined;
    },

    // ========================================================================
    // Diff Preview Mode
    // ========================================================================

    enterDiffPreview: (filePath) => {
      set({ diffPreviewPath: filePath });

      // Ensure file is open and active
      const state = get();
      if (!state.files.has(filePath)) {
        // File not open - this shouldn't happen in normal flow
        console.warn('Entering diff preview for unopened file:', filePath);
      }
      if (state.activeFilePath !== filePath) {
        set({ activeFilePath: filePath });
      }
    },

    exitDiffPreview: () => {
      set({ diffPreviewPath: null });
    },

    // ========================================================================
    // Conflict Detection
    // ========================================================================

    hasConflict: (patchId) => {
      const patch = get().pendingPatches.get(patchId);
      if (!patch) return false;

      const file = get().files.get(patch.filePath);
      if (!file) return false;

      // Conflict if file was modified after patch was proposed
      return file.lastModified > patch.timestamp;
    },

    // ========================================================================
    // Scroll Position
    // ========================================================================

    setScrollPosition: (path, top, left) => {
      set((state) => {
        const scrollPositions = new Map(state.scrollPositions);
        scrollPositions.set(path, { top, left });
        return { scrollPositions };
      });
    },

    getScrollPosition: (path) => {
      return get().scrollPositions.get(path);
    },

    // ========================================================================
    // Utility
    // ========================================================================

    getFile: (path) => {
      return get().files.get(path);
    },

    isDirty: (path) => {
      return get().files.get(path)?.isDirty ?? false;
    },

    hasUnsavedChanges: () => {
      for (const file of get().files.values()) {
        if (file.isDirty) return true;
      }
      return false;
    },

    reset: () => {
      set(initialState);
    },
  }))
);

// ============================================================================
// Selectors
// ============================================================================

export const selectActiveFile = (state: EditorState) =>
  state.activeFilePath ? state.files.get(state.activeFilePath) : undefined;

export const selectIsInDiffPreview = (state: EditorState) =>
  state.diffPreviewPath !== null;

export const selectPendingPatchCount = (state: EditorState) => {
  let count = 0;
  for (const patch of state.pendingPatches.values()) {
    if (patch.status === 'pending') count++;
  }
  return count;
};
