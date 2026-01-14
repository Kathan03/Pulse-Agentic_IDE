/**
 * TerminalApproval - Command Execution Approval Modal
 *
 * Shows terminal command and risk level, allows user to approve or deny.
 */

import { useState } from 'react';
import type { Approval } from '@/stores/approvalStore';
import type { TerminalApprovalData } from '@/types/websocket';

interface TerminalApprovalProps {
  approval: Approval;
  onApprove: (feedback?: string) => void;
  onDeny: (feedback?: string) => void;
}

export function TerminalApproval({ approval, onApprove, onDeny }: TerminalApprovalProps) {
  const [feedback, setFeedback] = useState('');

  const data = approval.data as TerminalApprovalData;

  const riskColors = {
    low: 'bg-pulse-success/20 text-pulse-success border-pulse-success',
    medium: 'bg-pulse-warning/20 text-pulse-warning border-pulse-warning',
    high: 'bg-pulse-error/20 text-pulse-error border-pulse-error',
  };

  const riskLabels = {
    low: 'Low Risk',
    medium: 'Medium Risk',
    high: 'High Risk',
  };

  return (
    <div className="bg-pulse-bg-secondary rounded-lg shadow-modal overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-pulse-border">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-pulse-fg flex items-center">
              <TerminalIcon />
              <span className="ml-2">Terminal Command Approval</span>
            </h2>
            <p className="text-sm text-pulse-fg-muted mt-1">
              The agent wants to execute a terminal command
            </p>
          </div>

          {/* Risk Badge */}
          <div
            className={`px-3 py-1 rounded-full text-xs font-medium border ${riskColors[data.risk_level]}`}
          >
            {riskLabels[data.risk_level]}
          </div>
        </div>
      </div>

      {/* High Risk Warning */}
      {data.risk_level === 'high' && (
        <div className="px-6 py-3 bg-pulse-error/20 border-b border-pulse-error/50">
          <div className="flex items-start text-pulse-error">
            <WarningIcon />
            <div className="ml-2">
              <span className="text-sm font-medium">High Risk Command</span>
              <p className="text-xs mt-1 opacity-80">
                This command could potentially modify system state or delete data.
                Please review carefully before approving.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Command */}
      <div className="px-6 py-4 border-b border-pulse-border">
        <h3 className="text-sm font-medium text-pulse-fg mb-2">Command</h3>
        <div className="bg-pulse-bg rounded-lg p-4 font-mono text-sm overflow-x-auto">
          <span className="text-pulse-success">$</span>{' '}
          <span className="text-pulse-fg">{data.command}</span>
        </div>
      </div>

      {/* Working Directory */}
      <div className="px-6 py-4 border-b border-pulse-border">
        <h3 className="text-sm font-medium text-pulse-fg mb-2">Working Directory</h3>
        <p className="text-sm text-pulse-fg-muted font-mono">{data.working_directory}</p>
      </div>

      {/* Explanation */}
      <div className="px-6 py-4 border-b border-pulse-border">
        <h3 className="text-sm font-medium text-pulse-fg mb-2">Purpose</h3>
        <p className="text-sm text-pulse-fg-muted">{data.explanation || approval.description}</p>
      </div>

      {/* Feedback */}
      <div className="px-6 py-4 border-b border-pulse-border">
        <label className="block text-sm font-medium text-pulse-fg mb-2">
          Feedback (optional)
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Add any notes or modifications..."
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
          className={`
            px-4 py-2 text-sm font-medium text-white rounded transition-colors
            ${data.risk_level === 'high'
              ? 'bg-pulse-error hover:bg-pulse-error/90'
              : 'bg-pulse-success hover:bg-pulse-success/90'
            }
          `}
        >
          {data.risk_level === 'high' ? 'Execute Anyway' : 'Approve Execution'}
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Icons
// ============================================================================

function TerminalIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5 text-pulse-primary" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5 flex-shrink-0" fill="currentColor">
      <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
    </svg>
  );
}
