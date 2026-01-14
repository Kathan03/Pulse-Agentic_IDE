import { AppShell } from '@components/layout/AppShell';
import { ApprovalOverlay } from '@components/approval/ApprovalOverlay';
import { CommandPalette } from '@components/common/CommandPalette';
import { useKeyboardShortcuts } from '@hooks/useKeyboardShortcuts';
import { useFileSystem } from '@hooks/useFileSystem';
import { usePulseAgent } from '@hooks/usePulseAgent';
import { useMenuActions } from '@hooks/useMenuActions';
import { ThemeProvider } from '@/contexts/ThemeContext';

function AppContent() {
  // Initialize global hooks
  useKeyboardShortcuts();
  useFileSystem();
  usePulseAgent(); // Auto-connects to backend
  useMenuActions(); // Handle menu actions from Electron

  return (
    <>
      <AppShell />
      <ApprovalOverlay />
      <CommandPalette />
    </>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
