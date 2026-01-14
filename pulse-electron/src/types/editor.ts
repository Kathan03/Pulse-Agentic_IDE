/**
 * Editor Types
 *
 * Types for the Monaco editor integration and file management.
 */

// ============================================================================
// File State
// ============================================================================

export interface FileState {
  /** Absolute path to the file */
  path: string;

  /** Current file content */
  content: string;

  /** Original content when file was opened (for dirty detection) */
  originalContent: string;

  /** Incrementing version for conflict detection */
  version: number;

  /** Last modified timestamp */
  lastModified: number;

  /** Whether file has unsaved changes */
  isDirty: boolean;

  /** Language ID for syntax highlighting */
  language: string;
}

// ============================================================================
// Tab
// ============================================================================

export interface EditorTab {
  /** Absolute path to the file */
  path: string;

  /** Display name (filename) */
  name: string;

  /** Whether tab has unsaved changes */
  isDirty: boolean;

  /** Whether this is a preview tab (italic, replaced on next open) */
  isPreview: boolean;
}

// ============================================================================
// Pending Patch (for approval flow)
// ============================================================================

export interface PendingPatch {
  /** Unique patch ID */
  id: string;

  /** Run ID that proposed this patch */
  runId: string;

  /** File path being patched */
  filePath: string;

  /** Content before patch */
  originalContent: string;

  /** Content after patch */
  patchedContent: string;

  /** Summary of changes */
  patchSummary: string;

  /** When patch was proposed */
  timestamp: number;

  /** Approval status */
  status: 'pending' | 'approved' | 'denied';
}

// ============================================================================
// File Tree
// ============================================================================

export interface FileTreeNode {
  /** Node name (file/folder name) */
  name: string;

  /** Absolute path */
  path: string;

  /** Whether this is a directory */
  isDirectory: boolean;

  /** Children (only for directories) */
  children?: FileTreeNode[];

  /** Whether directory is expanded in tree view */
  isExpanded?: boolean;

  /** File size in bytes (only for files) */
  size?: number;

  /** Last modified timestamp */
  modified?: number;
}

// ============================================================================
// Monaco Configuration
// ============================================================================

export interface MonacoTheme {
  base: 'vs-dark' | 'vs' | 'hc-black';
  inherit: boolean;
  rules: MonacoTokenRule[];
  colors: Record<string, string>;
}

export interface MonacoTokenRule {
  token: string;
  foreground?: string;
  fontStyle?: string;
}

// ============================================================================
// Language Configuration
// ============================================================================

export interface LanguageConfig {
  id: string;
  extensions: string[];
  aliases: string[];
  mimetypes?: string[];
}

// Supported languages with their configurations
export const LANGUAGE_MAP: Record<string, LanguageConfig> = {
  st: {
    id: 'structured-text',
    extensions: ['.st', '.ST'],
    aliases: ['Structured Text', 'ST', 'IEC 61131-3'],
  },
  python: {
    id: 'python',
    extensions: ['.py', '.pyw', '.pyi'],
    aliases: ['Python', 'py'],
  },
  typescript: {
    id: 'typescript',
    extensions: ['.ts', '.tsx'],
    aliases: ['TypeScript', 'ts'],
  },
  javascript: {
    id: 'javascript',
    extensions: ['.js', '.jsx', '.mjs'],
    aliases: ['JavaScript', 'js'],
  },
  json: {
    id: 'json',
    extensions: ['.json', '.jsonc'],
    aliases: ['JSON'],
  },
  markdown: {
    id: 'markdown',
    extensions: ['.md', '.markdown'],
    aliases: ['Markdown', 'md'],
  },
  yaml: {
    id: 'yaml',
    extensions: ['.yml', '.yaml'],
    aliases: ['YAML', 'yml'],
  },
  xml: {
    id: 'xml',
    extensions: ['.xml', '.xsl', '.xsd'],
    aliases: ['XML'],
  },
  plaintext: {
    id: 'plaintext',
    extensions: ['.txt', '.text', '.log'],
    aliases: ['Plain Text', 'text'],
  },
};

/**
 * Get language ID from file extension.
 */
export function getLanguageFromPath(filePath: string): string {
  const ext = filePath.toLowerCase().split('.').pop() || '';

  for (const [, config] of Object.entries(LANGUAGE_MAP)) {
    if (config.extensions.some((e) => e.toLowerCase() === `.${ext}`)) {
      return config.id;
    }
  }

  return 'plaintext';
}
