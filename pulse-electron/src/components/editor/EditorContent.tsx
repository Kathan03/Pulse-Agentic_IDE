/**
 * EditorContent - Editor View Switcher
 *
 * Switches between standard Monaco editor, diff view, and special tabs (settings).
 * Note: The welcome/empty state is handled by EditorArea, not here.
 */

import { useEditorStore, selectActiveFile, selectIsInDiffPreview } from '@/stores/editorStore';
import { MonacoEditor } from './MonacoEditor';
import { MonacoDiffEditor } from './MonacoDiffEditor';
import { SettingsTab } from '../settings/SettingsTab';

export function EditorContent() {
  const activeFile = useEditorStore(selectActiveFile);
  const isInDiffPreview = useEditorStore(selectIsInDiffPreview);
  const { diffPreviewPath, activeFilePath, getPatchForFile } = useEditorStore();

  // No active file - this shouldn't happen as EditorArea handles empty state
  // But just in case, return null to prevent errors
  if (!activeFile || !activeFilePath) {
    return null;
  }

  // Special tabs
  if (activeFilePath === '__settings__') {
    return (
      <div className="h-full w-full overflow-auto">
        <SettingsTab />
      </div>
    );
  }

  // Check if we should show diff view
  const showDiff = isInDiffPreview && diffPreviewPath === activeFilePath;

  if (showDiff) {
    const patch = getPatchForFile(activeFilePath);
    if (patch) {
      return (
        <div className="h-full w-full">
          <MonacoDiffEditor
            filePath={activeFilePath}
            originalContent={patch.originalContent}
            modifiedContent={patch.patchedContent}
          />
        </div>
      );
    }
  }

  // Standard editor - wrap in container with explicit dimensions
  return (
    <div className="h-full w-full">
      <MonacoEditor filePath={activeFilePath} />
    </div>
  );
}
