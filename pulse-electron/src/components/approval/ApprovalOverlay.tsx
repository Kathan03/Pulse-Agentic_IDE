/**
 * ApprovalOverlay - Modal Container for Approvals
 *
 * Renders the appropriate approval modal based on approval type.
 */

import { useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApprovalStore, type Approval } from '@/stores/approvalStore';
import { usePulseAgent } from '@/hooks/usePulseAgent';
import { PatchApproval } from './PatchApproval';
import { TerminalApproval } from './TerminalApproval';

export function ApprovalOverlay() {
  const { isModalOpen, currentApproval, closeModal } = useApprovalStore();
  const { approveAction, denyAction } = usePulseAgent({ autoConnect: false });

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isModalOpen) {
        // Don't close on escape - user must explicitly approve or deny
        // Could show a hint instead
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isModalOpen]);

  const handleApprove = useCallback(
    (feedback?: string) => {
      if (!currentApproval) return;

      // Process the approval through WebSocket
      approveAction(feedback);

      // Update store
      useApprovalStore.getState().approveAction(currentApproval.id);
    },
    [currentApproval, approveAction]
  );

  const handleDeny = useCallback(
    (feedback?: string) => {
      if (!currentApproval) return;

      // Process the denial through WebSocket
      denyAction(feedback);

      // Update store
      useApprovalStore.getState().denyAction(currentApproval.id, feedback);
    },
    [currentApproval, denyAction]
  );

  return (
    <AnimatePresence>
      {isModalOpen && currentApproval && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center"
        >
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />

          {/* Modal Content */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="relative z-10 w-full max-w-2xl mx-4"
          >
            {currentApproval.type === 'patch' || currentApproval.type === 'file_write' ? (
              <PatchApproval
                approval={currentApproval}
                onApprove={handleApprove}
                onDeny={handleDeny}
              />
            ) : (
              <TerminalApproval
                approval={currentApproval}
                onApprove={handleApprove}
                onDeny={handleDeny}
              />
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
