/**
 * Sidebar - File Explorer and Other Views
 *
 * Displays content based on active activity bar item.
 */

import { useState, useCallback, useEffect } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { useWorkspaceStore } from '@/stores/workspaceStore';
import { useEditorStore } from '@/stores/editorStore';
import { FileExplorer } from './FileExplorer';

export function Sidebar() {
  const { activeActivityItem } = useUIStore();

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-9 px-4 flex items-center border-b border-pulse-border">
        <span className="text-xs font-semibold uppercase tracking-wide text-pulse-fg-muted">
          {getHeaderTitle(activeActivityItem)}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeActivityItem === 'explorer' && <FileExplorer />}
        {activeActivityItem === 'search' && <SearchPanel />}
        {activeActivityItem === 'sourceControl' && <SourceControlPanel />}
        {activeActivityItem === 'extensions' && <ExtensionsPanel />}
        {activeActivityItem === 'settings' && <SettingsPanel />}
      </div>
    </div>
  );
}

function getHeaderTitle(item: string): string {
  const titles: Record<string, string> = {
    explorer: 'Explorer',
    search: 'Search',
    sourceControl: 'Source Control',
    extensions: 'Extensions',
    settings: 'Settings',
  };
  return titles[item] || item;
}

// ============================================================================
// Placeholder Panels
// ============================================================================

interface SearchResult {
  filePath: string;
  fileName: string;
  lineNumber: number;
  lineContent: string;
  matchStart: number;
  matchEnd: number;
}

function SearchPanel() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [useRegex, setUseRegex] = useState(false);
  const { projectRoot } = useWorkspaceStore();
  const { openFile } = useEditorStore();

  // Debounced search
  useEffect(() => {
    if (!query.trim() || !projectRoot) {
      setResults([]);
      return;
    }

    const timeoutId = setTimeout(() => {
      performSearch();
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [query, caseSensitive, useRegex, projectRoot]);

  const performSearch = useCallback(async () => {
    if (!query.trim() || !projectRoot) return;

    setIsSearching(true);
    try {
      // Use the workspace store's search or direct file search
      const searchResults = await searchInFiles(projectRoot, query, { caseSensitive, useRegex });
      setResults(searchResults);
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [query, projectRoot, caseSensitive, useRegex]);

  const handleResultClick = useCallback(async (result: SearchResult) => {
    try {
      const content = await window.pulseAPI.fs.readFile(result.filePath);
      openFile(result.filePath, content, { isPreview: false });
      // TODO: Navigate to specific line in Monaco editor
    } catch (error) {
      console.error('Failed to open file:', error);
    }
  }, [openFile]);

  if (!projectRoot) {
    return (
      <div className="p-4 text-center">
        <p className="text-xs text-pulse-fg-muted">
          Open a folder to search across files.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Search Input */}
      <div className="p-2 space-y-2">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search..."
            className="w-full px-3 py-1.5 pr-8 bg-pulse-input border border-pulse-border rounded text-sm focus:outline-none focus:border-pulse-primary"
          />
          {isSearching && (
            <div className="absolute right-2 top-1/2 -translate-y-1/2">
              <div className="w-4 h-4 border-2 border-pulse-primary border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>

        {/* Search Options */}
        <div className="flex items-center gap-3 text-xs">
          <label className="flex items-center gap-1 cursor-pointer text-pulse-fg-muted hover:text-pulse-fg">
            <input
              type="checkbox"
              checked={caseSensitive}
              onChange={(e) => setCaseSensitive(e.target.checked)}
              className="w-3 h-3"
            />
            <span>Aa</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer text-pulse-fg-muted hover:text-pulse-fg">
            <input
              type="checkbox"
              checked={useRegex}
              onChange={(e) => setUseRegex(e.target.checked)}
              className="w-3 h-3"
            />
            <span>.*</span>
          </label>
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-auto">
        {results.length === 0 && query.trim() && !isSearching && (
          <div className="p-4 text-center text-xs text-pulse-fg-muted">
            No results found
          </div>
        )}

        {results.length > 0 && (
          <div className="text-xs">
            <div className="px-2 py-1 text-pulse-fg-muted border-b border-pulse-border">
              {results.length} result{results.length !== 1 ? 's' : ''} in {new Set(results.map(r => r.filePath)).size} file{new Set(results.map(r => r.filePath)).size !== 1 ? 's' : ''}
            </div>
            {results.map((result, index) => (
              <button
                key={`${result.filePath}:${result.lineNumber}:${index}`}
                onClick={() => handleResultClick(result)}
                className="w-full text-left px-2 py-1 hover:bg-pulse-bg-tertiary border-b border-pulse-border/50"
              >
                <div className="flex items-center gap-1 text-pulse-fg truncate">
                  <span className="text-pulse-primary">{result.fileName}</span>
                  <span className="text-pulse-fg-muted">:{result.lineNumber}</span>
                </div>
                <div className="text-pulse-fg-muted truncate pl-2">
                  {highlightMatch(result.lineContent, result.matchStart, result.matchEnd)}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Highlight matching text
function highlightMatch(text: string, start: number, end: number): React.ReactNode {
  if (start < 0 || end <= start) return text;

  const before = text.slice(0, start);
  const match = text.slice(start, end);
  const after = text.slice(end);

  return (
    <>
      {before}
      <span className="bg-pulse-primary/30 text-pulse-fg">{match}</span>
      {after}
    </>
  );
}

// Search in files recursively
async function searchInFiles(
  rootPath: string,
  query: string,
  options: { caseSensitive: boolean; useRegex: boolean }
): Promise<SearchResult[]> {
  const results: SearchResult[] = [];
  const maxResults = 100;

  try {
    // Get all files recursively
    const files = await getAllFiles(rootPath);

    // Search patterns
    let searchPattern: RegExp;
    try {
      if (options.useRegex) {
        searchPattern = new RegExp(query, options.caseSensitive ? 'g' : 'gi');
      } else {
        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        searchPattern = new RegExp(escapedQuery, options.caseSensitive ? 'g' : 'gi');
      }
    } catch {
      // Invalid regex, return empty
      return [];
    }

    // Search each file
    for (const filePath of files) {
      if (results.length >= maxResults) break;

      try {
        const content = await window.pulseAPI.fs.readFile(filePath);
        const lines = content.split('\n');
        const fileName = filePath.split(/[\\/]/).pop() || filePath;

        for (let i = 0; i < lines.length && results.length < maxResults; i++) {
          const line = lines[i];
          searchPattern.lastIndex = 0;
          const match = searchPattern.exec(line);

          if (match) {
            results.push({
              filePath,
              fileName,
              lineNumber: i + 1,
              lineContent: line.trim(),
              matchStart: match.index - (line.length - line.trim().length),
              matchEnd: match.index + match[0].length - (line.length - line.trim().length),
            });
          }
        }
      } catch {
        // Skip files that can't be read (binary, etc.)
      }
    }
  } catch (error) {
    console.error('Search error:', error);
  }

  return results;
}

// Get all files recursively
async function getAllFiles(dirPath: string, maxDepth = 5, currentDepth = 0): Promise<string[]> {
  if (currentDepth >= maxDepth) return [];

  const files: string[] = [];

  try {
    const entries = await window.pulseAPI.fs.readDir(dirPath);

    for (const entry of entries) {
      // Skip hidden files and common non-text directories
      if (entry.name.startsWith('.') || ['node_modules', 'dist', 'build', '__pycache__', '.git'].includes(entry.name)) {
        continue;
      }

      if (entry.isDirectory) {
        const subFiles = await getAllFiles(entry.path, maxDepth, currentDepth + 1);
        files.push(...subFiles);
      } else {
        // Only include text files
        const ext = entry.name.split('.').pop()?.toLowerCase();
        const textExtensions = ['ts', 'tsx', 'js', 'jsx', 'json', 'md', 'txt', 'py', 'st', 'css', 'html', 'xml', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf'];
        if (ext && textExtensions.includes(ext)) {
          files.push(entry.path);
        }
      }
    }
  } catch {
    // Skip directories that can't be read
  }

  return files;
}

function SourceControlPanel() {
  return (
    <div className="p-4">
      <p className="text-xs text-pulse-fg-muted">
        Source control integration coming soon.
      </p>
    </div>
  );
}

function ExtensionsPanel() {
  return (
    <div className="p-4">
      <p className="text-xs text-pulse-fg-muted">
        Extensions marketplace coming soon.
      </p>
    </div>
  );
}

function SettingsPanel() {
  return (
    <div className="p-4">
      <p className="text-xs text-pulse-fg-muted">
        Settings panel coming soon.
      </p>
    </div>
  );
}
