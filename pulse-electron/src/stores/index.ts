/**
 * Store Exports
 */

export { useEditorStore, selectActiveFile, selectIsInDiffPreview, selectPendingPatchCount } from './editorStore';
export { useAgentStore, selectIsRunning, selectCanSendMessage, selectLatestMessage } from './agentStore';
export { useApprovalStore, selectPendingCount, selectCurrentApprovalType, selectIsPatchApproval, selectIsTerminalApproval } from './approvalStore';
export { useWorkspaceStore, selectHasWorkspace, selectIsExpanded, selectFileCount } from './workspaceStore';
export { useUIStore, selectHasNotifications, selectUnreadNotificationCount } from './uiStore';

export type { Message, MessageRole, RunStatus, AgentMode, VibeState, ToolCallInfo } from './agentStore';
export type { Approval, ApprovalType, PatchApproval, TerminalApproval } from './approvalStore';
export type { Notification, PanelId, ActivityBarItem } from './uiStore';
