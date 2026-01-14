/**
 * Workspace Store (Zustand)
 *
 * Manages workspace state including project root, file tree, and recent workspaces.
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type { FileTreeNode } from '@/types/editor';

// ============================================================================
// Store State
// ============================================================================

interface WorkspaceState {
  // Current workspace
  projectRoot: string | null;
  workspaceName: string | null;

  // File tree
  fileTree: FileTreeNode[];
  isLoadingTree: boolean;

  // Expanded folders (paths)
  expandedFolders: Set<string>;

  // Selected file in tree (not necessarily open in editor)
  selectedPath: string | null;

  // Recent workspaces
  recentWorkspaces: string[];

  // Search
  searchQuery: string;
  searchResults: string[];
}

// ============================================================================
// Store Actions
// ============================================================================

interface WorkspaceActions {
  // Workspace management
  openWorkspace: (path: string) => Promise<void>;
  closeWorkspace: () => void;

  // File tree
  loadFileTree: () => Promise<void>;
  refreshFileTree: () => Promise<void>;
  refreshTree: () => Promise<void>; // Alias for refreshFileTree
  expandFolder: (path: string) => Promise<void>;
  collapseFolder: (path: string) => void;
  collapseAllFolders: () => void;
  toggleFolder: (path: string) => Promise<void>;

  // Selection
  selectPath: (path: string | null) => void;

  // Recent workspaces
  loadRecentWorkspaces: () => Promise<void>;
  addRecentWorkspace: (path: string) => Promise<void>;
  clearRecentWorkspaces: () => Promise<void>;

  // Search
  setSearchQuery: (query: string) => void;
  searchFiles: (query: string) => void;

  // Utility
  getNode: (path: string) => FileTreeNode | undefined;
  reset: () => void;
}

// ============================================================================
// Initial State
// ============================================================================

const initialState: WorkspaceState = {
  projectRoot: null,
  workspaceName: null,
  fileTree: [],
  isLoadingTree: false,
  expandedFolders: new Set(),
  selectedPath: null,
  recentWorkspaces: [],
  searchQuery: '',
  searchResults: [],
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Recursively find a node in the file tree.
 */
function findNode(
  nodes: FileTreeNode[],
  path: string
): FileTreeNode | undefined {
  for (const node of nodes) {
    if (node.path === path) return node;
    if (node.children) {
      const found = findNode(node.children, path);
      if (found) return found;
    }
  }
  return undefined;
}

/**
 * Build file tree from directory entries.
 */
async function buildTreeNode(
  path: string,
  depth: number = 0,
  maxDepth: number = 1
): Promise<FileTreeNode[]> {
  if (depth > maxDepth) return [];

  try {
    const entries = await window.pulseAPI.fs.readDir(path);

    return entries.map((entry) => ({
      name: entry.name,
      path: entry.path,
      isDirectory: entry.isDirectory,
      size: entry.size,
      modified: entry.modified,
      children: entry.isDirectory ? [] : undefined,
      isExpanded: false,
    }));
  } catch (error) {
    console.error('Failed to read directory:', path, error);
    return [];
  }
}

// ============================================================================
// Store Implementation
// ============================================================================

export const useWorkspaceStore = create<WorkspaceState & WorkspaceActions>()(
  subscribeWithSelector((set, get) => ({
    ...initialState,

    // ========================================================================
    // Workspace Management
    // ========================================================================

    openWorkspace: async (path) => {
      set({ isLoadingTree: true });

      try {
        // Get workspace name from path
        const name = path.split(/[\\/]/).pop() || path;

        // Load initial file tree
        const fileTree = await buildTreeNode(path);

        // Start file watcher
        window.pulseAPI.fs.watch(path);

        set({
          projectRoot: path,
          workspaceName: name,
          fileTree,
          isLoadingTree: false,
          expandedFolders: new Set(),
          selectedPath: null,
        });

        // Add to recent workspaces
        get().addRecentWorkspace(path);
      } catch (error) {
        console.error('Failed to open workspace:', error);
        set({ isLoadingTree: false });
        throw error;
      }
    },

    closeWorkspace: () => {
      const { projectRoot } = get();
      if (projectRoot) {
        window.pulseAPI.fs.unwatch(projectRoot);
      }

      set({
        projectRoot: null,
        workspaceName: null,
        fileTree: [],
        expandedFolders: new Set(),
        selectedPath: null,
        searchQuery: '',
        searchResults: [],
      });
    },

    // ========================================================================
    // File Tree
    // ========================================================================

    loadFileTree: async () => {
      const { projectRoot } = get();
      if (!projectRoot) return;

      set({ isLoadingTree: true });

      try {
        const fileTree = await buildTreeNode(projectRoot);
        set({ fileTree, isLoadingTree: false });
      } catch (error) {
        console.error('Failed to load file tree:', error);
        set({ isLoadingTree: false });
      }
    },

    refreshFileTree: async () => {
      await get().loadFileTree();
    },

    // Alias for refreshFileTree
    refreshTree: async () => {
      await get().refreshFileTree();
    },

    expandFolder: async (path) => {
      const { expandedFolders } = get();

      // Already expanded
      if (expandedFolders.has(path)) return;

      try {
        // Load children
        const children = await buildTreeNode(path);

        set((state) => {
          // Update the node's children in the tree
          const updateChildren = (nodes: FileTreeNode[]): FileTreeNode[] => {
            return nodes.map((node) => {
              if (node.path === path) {
                return { ...node, children, isExpanded: true };
              }
              if (node.children) {
                return { ...node, children: updateChildren(node.children) };
              }
              return node;
            });
          };

          return {
            fileTree: updateChildren(state.fileTree),
            expandedFolders: new Set([...state.expandedFolders, path]),
          };
        });
      } catch (error) {
        console.error('Failed to expand folder:', path, error);
      }
    },

    collapseFolder: (path) => {
      set((state) => {
        const expandedFolders = new Set(state.expandedFolders);
        expandedFolders.delete(path);

        // Update node's isExpanded state
        const updateExpanded = (nodes: FileTreeNode[]): FileTreeNode[] => {
          return nodes.map((node) => {
            if (node.path === path) {
              return { ...node, isExpanded: false };
            }
            if (node.children) {
              return { ...node, children: updateExpanded(node.children) };
            }
            return node;
          });
        };

        return {
          fileTree: updateExpanded(state.fileTree),
          expandedFolders,
        };
      });
    },

    collapseAllFolders: () => {
      set((state) => {
        // Collapse all nodes in the tree
        const collapseAll = (nodes: FileTreeNode[]): FileTreeNode[] => {
          return nodes.map((node) => ({
            ...node,
            isExpanded: false,
            children: node.children ? collapseAll(node.children) : undefined,
          }));
        };

        return {
          fileTree: collapseAll(state.fileTree),
          expandedFolders: new Set(),
        };
      });
    },

    toggleFolder: async (path) => {
      const { expandedFolders } = get();
      if (expandedFolders.has(path)) {
        get().collapseFolder(path);
      } else {
        await get().expandFolder(path);
      }
    },

    // ========================================================================
    // Selection
    // ========================================================================

    selectPath: (path) => {
      set({ selectedPath: path });
    },

    // ========================================================================
    // Recent Workspaces
    // ========================================================================

    loadRecentWorkspaces: async () => {
      try {
        const recent = await window.pulseAPI.workspace.getRecentWorkspaces();
        set({ recentWorkspaces: recent });
      } catch (error) {
        console.error('Failed to load recent workspaces:', error);
      }
    },

    addRecentWorkspace: async (path) => {
      try {
        await window.pulseAPI.workspace.addRecentWorkspace(path);
        await get().loadRecentWorkspaces();
      } catch (error) {
        console.error('Failed to add recent workspace:', error);
      }
    },

    clearRecentWorkspaces: async () => {
      try {
        await window.pulseAPI.workspace.clearRecentWorkspaces();
        set({ recentWorkspaces: [] });
      } catch (error) {
        console.error('Failed to clear recent workspaces:', error);
      }
    },

    // ========================================================================
    // Search
    // ========================================================================

    setSearchQuery: (query) => {
      set({ searchQuery: query });
      if (query) {
        get().searchFiles(query);
      } else {
        set({ searchResults: [] });
      }
    },

    searchFiles: (query) => {
      const { fileTree } = get();
      const results: string[] = [];
      const lowerQuery = query.toLowerCase();

      // Recursive search through loaded tree
      const searchNodes = (nodes: FileTreeNode[]) => {
        for (const node of nodes) {
          if (node.name.toLowerCase().includes(lowerQuery)) {
            results.push(node.path);
          }
          if (node.children) {
            searchNodes(node.children);
          }
        }
      };

      searchNodes(fileTree);
      set({ searchResults: results.slice(0, 50) }); // Limit results
    },

    // ========================================================================
    // Utility
    // ========================================================================

    getNode: (path) => {
      return findNode(get().fileTree, path);
    },

    reset: () => {
      const { projectRoot } = get();
      if (projectRoot) {
        window.pulseAPI.fs.unwatch(projectRoot);
      }
      set(initialState);
    },
  }))
);

// ============================================================================
// Selectors
// ============================================================================

export const selectHasWorkspace = (state: WorkspaceState) =>
  state.projectRoot !== null;

export const selectIsExpanded = (path: string) => (state: WorkspaceState) =>
  state.expandedFolders.has(path);

export const selectFileCount = (state: WorkspaceState) => {
  let count = 0;
  const countNodes = (nodes: FileTreeNode[]) => {
    for (const node of nodes) {
      if (!node.isDirectory) count++;
      if (node.children) countNodes(node.children);
    }
  };
  countNodes(state.fileTree);
  return count;
};
