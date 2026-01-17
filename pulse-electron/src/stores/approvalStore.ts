/**
 * Approval Store (Zustand)
 *
 * Manages pending approvals for patches and terminal commands.
 */

import { create } from 'zustand';
import type {
  PatchApprovalData,
  TerminalApprovalData,
} from '@/types/websocket';

// ============================================================================
// Approval Types
// ============================================================================

export type ApprovalType = 'patch' | 'terminal' | 'file_write';

export interface BaseApproval {
  id: string;
  runId: string;
  type: ApprovalType;
  description: string;
  timestamp: number;
}

export interface PatchApproval extends BaseApproval {
  type: 'patch';
  data: PatchApprovalData;
}

export interface TerminalApproval extends BaseApproval {
  type: 'terminal';
  data: TerminalApprovalData;
}

export interface FileWriteApproval extends BaseApproval {
  type: 'file_write';
  data: {
    operation: string;
    path: string;
    content: string;
    diff?: string;
  };
}

export type Approval = PatchApproval | TerminalApproval | FileWriteApproval;

// ============================================================================
// Store State
// ============================================================================

interface ApprovalState {
  // Queue of pending approvals
  pendingApprovals: Approval[];

  // Currently displayed approval (modal)
  currentApproval: Approval | null;

  // Whether approval modal is visible
  isModalOpen: boolean;
}

// ============================================================================
// Store Actions
// ============================================================================

interface ApprovalActions {
  // Add approval to queue
  addApproval: (approval: Omit<Approval, 'id' | 'timestamp'>) => void;

  // Show approval modal
  showApproval: (approvalId: string) => void;

  // Process approval decision
  approveAction: (approvalId: string) => void;
  denyAction: (approvalId: string, feedback?: string) => void;

  // Remove approval from queue
  removeApproval: (approvalId: string) => void;

  // Clear all approvals for a run
  clearApprovalsForRun: (runId: string) => void;

  // Modal control
  closeModal: () => void;

  // Utility
  getApproval: (approvalId: string) => Approval | undefined;
  hasPendingApprovals: () => boolean;
  reset: () => void;
}

// ============================================================================
// Initial State
// ============================================================================

const initialState: ApprovalState = {
  pendingApprovals: [],
  currentApproval: null,
  isModalOpen: false,
};

// ============================================================================
// Store Implementation
// ============================================================================

export const useApprovalStore = create<ApprovalState & ApprovalActions>()(
  (set, get) => ({
    ...initialState,

    // ========================================================================
    // Add Approval
    // ========================================================================

    addApproval: (approval) => {
      const newApproval: Approval = {
        ...approval,
        id: crypto.randomUUID(),
        timestamp: Date.now(),
      } as Approval;

      set((state) => ({
        pendingApprovals: [...state.pendingApprovals, newApproval],
        // Auto-show if no current approval
        currentApproval: state.currentApproval || newApproval,
        isModalOpen: state.isModalOpen || true,
      }));
    },

    // ========================================================================
    // Show Approval
    // ========================================================================

    showApproval: (approvalId) => {
      const approval = get().pendingApprovals.find((a) => a.id === approvalId);
      if (approval) {
        set({
          currentApproval: approval,
          isModalOpen: true,
        });
      }
    },

    // ========================================================================
    // Approve Action
    // ========================================================================

    approveAction: (approvalId) => {
      set((state) => {
        const approval = state.pendingApprovals.find((a) => a.id === approvalId);
        if (!approval) return state;

        // Remove from queue
        const pendingApprovals = state.pendingApprovals.filter(
          (a) => a.id !== approvalId
        );

        // Show next approval if any, otherwise close modal
        const nextApproval = pendingApprovals[0] || null;

        return {
          pendingApprovals,
          currentApproval: nextApproval,
          isModalOpen: nextApproval !== null,
        };
      });
    },

    // ========================================================================
    // Deny Action
    // ========================================================================

    denyAction: (approvalId, _feedback) => {
      set((state) => {
        const approval = state.pendingApprovals.find((a) => a.id === approvalId);
        if (!approval) return state;

        // Remove from queue
        const pendingApprovals = state.pendingApprovals.filter(
          (a) => a.id !== approvalId
        );

        // Show next approval if any, otherwise close modal
        const nextApproval = pendingApprovals[0] || null;

        return {
          pendingApprovals,
          currentApproval: nextApproval,
          isModalOpen: nextApproval !== null,
        };
      });
    },

    // ========================================================================
    // Remove Approval
    // ========================================================================

    removeApproval: (approvalId) => {
      set((state) => {
        const pendingApprovals = state.pendingApprovals.filter(
          (a) => a.id !== approvalId
        );

        // Clear current if it was removed
        const currentApproval =
          state.currentApproval?.id === approvalId
            ? pendingApprovals[0] || null
            : state.currentApproval;

        return {
          pendingApprovals,
          currentApproval,
          isModalOpen: currentApproval !== null,
        };
      });
    },

    // ========================================================================
    // Clear Approvals for Run
    // ========================================================================

    clearApprovalsForRun: (runId) => {
      set((state) => {
        const pendingApprovals = state.pendingApprovals.filter(
          (a) => a.runId !== runId
        );

        const currentApproval =
          state.currentApproval?.runId === runId
            ? pendingApprovals[0] || null
            : state.currentApproval;

        return {
          pendingApprovals,
          currentApproval,
          isModalOpen: currentApproval !== null,
        };
      });
    },

    // ========================================================================
    // Modal Control
    // ========================================================================

    closeModal: () => {
      set({ isModalOpen: false });
    },

    // ========================================================================
    // Utility
    // ========================================================================

    getApproval: (approvalId) => {
      return get().pendingApprovals.find((a) => a.id === approvalId);
    },

    hasPendingApprovals: () => {
      return get().pendingApprovals.length > 0;
    },

    reset: () => {
      set(initialState);
    },
  })
);

// ============================================================================
// Selectors
// ============================================================================

export const selectPendingCount = (state: ApprovalState) =>
  state.pendingApprovals.length;

export const selectCurrentApprovalType = (state: ApprovalState) =>
  state.currentApproval?.type;

export const selectIsPatchApproval = (state: ApprovalState) =>
  state.currentApproval?.type === 'patch';

export const selectIsTerminalApproval = (state: ApprovalState) =>
  state.currentApproval?.type === 'terminal';
