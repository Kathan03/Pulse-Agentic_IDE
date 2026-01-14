/**
 * PatchApproval - File Change Approval Modal
 *
 * Shows file changes and allows user to approve or deny.
 */

import { useState } from 'react';
import type { Approval, PatchApproval as PatchApprovalType } from '@/stores/approvalStore';
import type { PatchApprovalData } from '@/types/websocket';
import { useEditorStore } from '@/stores/editorStore';

interface PatchApprovalProps {
  approval: Approval;
  onApprove: (feedback?: string) => void;
  onDeny: (feedback?: string) => void;
}

export function PatchApproval({ approval, onApprove, onDeny }: PatchApprovalProps) {
  const [feedback, setFeedback] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);

  const data = approval.data as PatchApprovalData;
  const fileName = data.file_path.split(/[\\/]/).pop() || data.file_path;

  // Check for conflict
  const { hasConflict, getPatchForFile } = useEditorStore();
  const patch = getPatchForFile(data.file_path);
  const hasFileConflict = patch ? hasConflict(patch.id) : false;

  // Calculate diff stats
  const addedLines = countAddedLines(data.original_content, data.patched_content);
  const removedLines = countRemovedLines(data.original_content, data.patched_content);

  return (
    <div className="bg-pulse-bg-secondary rounded-lg shadow-modal overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-pulse-border">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-pulse-fg flex items-center">
              <FileIcon />
              <span className="ml-2">File Change Approval</span>
            </h2>
            <p className="text-sm text-pulse-fg-muted mt-1">
              The agent wants to modify <span className="font-mono text-pulse-primary">{fileName}</span>
            </p>
          </div>

          {/* Diff stats */}
          <div className="flex items-center space-x-3 text-sm">
            <span className="text-pulse-success">+{addedLines}</span>
            <span className="text-pulse-error">-{removedLines}</span>
          </div>
        </div>
      </div>

      {/* Conflict Warning */}
      {hasFileConflict && (
        <div className="px-6 py-3 bg-pulse-warning/20 border-b border-pulse-warning/50">
          <div className="flex items-center text-pulse-warning">
            <WarningIcon />
            <span className="ml-2 text-sm font-medium">
              File has been modified since this patch was proposed
            </span>
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="px-6 py-4 border-b border-pulse-border">
        <h3 className="text-sm font-medium text-pulse-fg mb-2">Summary</h3>
        <p className="text-sm text-pulse-fg-muted">{data.patch_summary || approval.description}</p>
      </div>

      {/* Expandable Diff Preview */}
      <div className="px-6 py-4 border-b border-pulse-border">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center text-sm text-pulse-primary hover:underline"
        >
          <ChevronIcon isExpanded={isExpanded} />
          <span className="ml-1">{isExpanded ? 'Hide' : 'Show'} changes</span>
        </button>

        {isExpanded && (
          <div className="mt-3 bg-pulse-bg rounded-lg overflow-hidden">
            <pre className="p-4 text-xs font-mono overflow-x-auto max-h-64 overflow-y-auto">
              <SimpleDiff
                original={data.original_content}
                modified={data.patched_content}
              />
            </pre>
          </div>
        )}
      </div>

      {/* Feedback */}
      <div className="px-6 py-4 border-b border-pulse-border">
        <label className="block text-sm font-medium text-pulse-fg mb-2">
          Feedback (optional)
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Add any notes for the agent..."
          className="w-full px-3 py-2 bg-pulse-input border border-pulse-border rounded text-sm resize-none focus:outline-none focus:border-pulse-primary"
          rows={2}
        />
      </div>

      {/* Actions */}
      <div className="px-6 py-4 flex items-center justify-end space-x-3">
        <button
          onClick={() => onDeny(feedback)}
          className="px-4 py-2 text-sm font-medium text-pulse-fg bg-pulse-bg-tertiary hover:bg-pulse-input rounded transition-colors"
        >
          Deny
        </button>
        <button
          onClick={() => onApprove(feedback)}
          className="px-4 py-2 text-sm font-medium text-white bg-pulse-success hover:bg-pulse-success/90 rounded transition-colors"
        >
          Approve Changes
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Simple Diff Display
// ============================================================================

function SimpleDiff({ original, modified }: { original: string; modified: string }) {
  const origLines = original.split('\n');
  const modLines = modified.split('\n');

  // Very simple line-by-line comparison
  const maxLines = Math.max(origLines.length, modLines.length);
  const diffLines: Array<{ type: 'same' | 'added' | 'removed'; content: string }> = [];

  for (let i = 0; i < maxLines; i++) {
    const origLine = origLines[i];
    const modLine = modLines[i];

    if (origLine === modLine) {
      if (origLine !== undefined) {
        diffLines.push({ type: 'same', content: origLine });
      }
    } else {
      if (origLine !== undefined) {
        diffLines.push({ type: 'removed', content: origLine });
      }
      if (modLine !== undefined) {
        diffLines.push({ type: 'added', content: modLine });
      }
    }
  }

  return (
    <>
      {diffLines.map((line, idx) => (
        <div
          key={idx}
          className={`
            ${line.type === 'added' ? 'bg-pulse-success/20 text-pulse-success' : ''}
            ${line.type === 'removed' ? 'bg-pulse-error/20 text-pulse-error' : ''}
          `}
        >
          <span className="inline-block w-6 text-right mr-2 text-pulse-fg-muted">
            {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
          </span>
          {line.content}
        </div>
      ))}
    </>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function countAddedLines(original: string, modified: string): number {
  const origLines = new Set(original.split('\n'));
  return modified.split('\n').filter((line) => !origLines.has(line)).length;
}

function countRemovedLines(original: string, modified: string): number {
  const modLines = new Set(modified.split('\n'));
  return original.split('\n').filter((line) => !modLines.has(line)).length;
}

// ============================================================================
// Icons
// ============================================================================

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5 text-pulse-primary" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z" />
      <polyline points="13 2 13 9 20 9" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
    </svg>
  );
}

function ChevronIcon({ isExpanded }: { isExpanded: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
      fill="currentColor"
    >
      <path d="M8 6l6 6-6 6" />
    </svg>
  );
}
