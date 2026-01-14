/**
 * ModeSelector - Agent Mode Dropdown
 *
 * Allows switching between Agent, Ask, and Plan modes.
 */

import { useState, useRef, useEffect } from 'react';
import { useAgentStore, type AgentMode, selectIsRunning } from '@/stores/agentStore';

export function ModeSelector() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { mode, setMode } = useAgentStore();
  const isRunning = useAgentStore(selectIsRunning);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (newMode: AgentMode) => {
    setMode(newMode);
    setIsOpen(false);
  };

  const modeConfig: Record<AgentMode, { label: string; icon: React.ReactNode; description: string; color: string }> = {
    agent: {
      label: 'Agent',
      icon: <AgentIcon />,
      description: 'Full access to modify files',
      color: 'text-pulse-success',
    },
    ask: {
      label: 'Ask',
      icon: <AskIcon />,
      description: 'Read-only, answers questions',
      color: 'text-pulse-info',
    },
    plan: {
      label: 'Plan',
      icon: <PlanIcon />,
      description: 'Creates plans without executing',
      color: 'text-pulse-warning',
    },
  };

  const current = modeConfig[mode];

  return (
    <div ref={dropdownRef} className="relative">
      {/* Trigger */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isRunning}
        className={`
          flex items-center space-x-1.5 px-2 py-1 rounded
          text-xs font-medium
          hover:bg-pulse-bg-tertiary
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-colors
          ${current.color}
        `}
      >
        <div className="w-3.5 h-3.5">{current.icon}</div>
        <span>{current.label}</span>
        <ChevronIcon isOpen={isOpen} />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-56 bg-pulse-bg-secondary border border-pulse-border rounded-lg shadow-dropdown z-50 overflow-hidden">
          {(Object.keys(modeConfig) as AgentMode[]).map((m) => {
            const config = modeConfig[m];
            const isActive = m === mode;

            return (
              <button
                key={m}
                onClick={() => handleSelect(m)}
                className={`
                  w-full flex items-start px-3 py-2 text-left
                  hover:bg-pulse-bg-tertiary
                  ${isActive ? 'bg-pulse-bg-tertiary' : ''}
                `}
              >
                <div className={`w-4 h-4 mt-0.5 mr-2 ${config.color}`}>
                  {config.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className={`text-sm font-medium ${config.color}`}>
                    {config.label}
                  </div>
                  <div className="text-xs text-pulse-fg-muted">
                    {config.description}
                  </div>
                </div>
                {isActive && (
                  <div className="ml-2 text-pulse-primary">
                    <CheckIcon />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Mode Icons - Font Awesome Icons
// ============================================================================


function AgentIcon() {
  return (
    <svg viewBox="0 0 640 640" fill="currentColor" stroke="currentColor" className="w-4 h-4">
    <path
        d="M280 170.6C298.9 161.6 312 142.3 312 120C312 89.1 286.9 64 256 64C225.1 64 200 89.1 200 120C200 142.3 213.1 161.6 232 170.6L232 269.4C229.2 270.7 226.5 272.3 224 274.1L143.9 228.3C145.5 207.5 135.3 186.7 116 175.5C89.2 160 55 169.2 39.5 196C24 222.8 33.2 257 60 272.5C61.3 273.3 62.6 274 64 274.6L64 365.4C62.7 366 61.3 366.7 60 367.5C33.2 383 24 417.2 39.5 444C55 470.8 89.2 480 116 464.5C135.3 453.4 145.4 432.5 143.8 411.7L194.3 382.8C182.8 371.6 174.4 357.2 170.5 341.1L120 370.1C117.4 368.3 114.8 366.8 112 365.4L112 274.6C114.8 273.3 117.5 271.7 120 269.9L200.1 315.7C200 317.1 199.9 318.5 199.9 320C199.9 342.3 213 361.6 231.9 370.6L231.9 469.4C213 478.4 199.9 497.7 199.9 520C199.9 550.9 225 576 255.9 576C286.6 576 311.5 551.3 311.9 520.8C304.4 507.9 298.4 494 294.3 479.3C290.1 475.3 285.2 472 279.9 469.4L279.9 370.6C282.7 369.3 285.4 367.7 287.9 365.9L298.4 371.9C303.9 356.6 311.5 342.4 320.8 329.4L311.7 324.2C311.8 322.8 311.9 321.4 311.9 319.9C311.9 297.6 298.8 278.3 279.9 269.3L279.9 170.5zM472.5 196C457 169.2 422.8 160 396 175.5C376.7 186.6 366.6 207.5 368.2 228.3L317.6 257.2C329.1 268.4 337.5 282.8 341.4 298.9L392 269.9C392.4 270.2 392.8 270.5 393.3 270.8C415 261.3 438.9 256 464.1 256C466.1 256 468.1 256 470 256.1C482.1 238.8 483.8 215.5 472.6 196zM464 576C543.5 576 608 511.5 608 432C608 352.5 543.5 288 464 288C384.5 288 320 352.5 320 432C320 511.5 384.5 576 464 576zM511.9 351C516.2 354.7 517.3 360.9 514.5 365.9L484.4 420L520 420C525.2 420 529.8 423.3 531.4 428.2C533 433.1 531.3 438.5 527.2 441.6L431.2 513.6C426.7 517 420.4 516.8 416.1 513C411.8 509.2 410.7 503.1 413.5 498.1L443.6 444L408 444C402.8 444 398.2 440.7 396.6 435.8C395 430.9 396.7 425.5 400.8 422.4L496.8 350.4C501.3 347 507.6 347.2 511.9 351z" />
    </svg>
  );
}

function AskIcon() {
  return (
    <i className="fa-solid fa-flask w-full h-full flex items-center justify-center text-xs" />
  );
}


function PlanIcon() {
  return (
    <svg viewBox="0 0 640 640" fill="currentColor" stroke="currentColor" className="w-4 h-4">
      <path
        d="M344 170.6C362.9 161.6 376 142.3 376 120C376 89.1 350.9 64 320 64C289.1 64 264 89.1 264 120C264 142.3 277.1 161.6 296 170.6L296 269.4C293.2 270.7 290.5 272.3 288 274.1L207.9 228.3C209.5 207.5 199.3 186.7 180 175.5C153.2 160 119 169.2 103.5 196C88 222.8 97.2 257 124 272.5C125.3 273.3 126.6 274 128 274.6L128 365.4C126.7 366 125.3 366.7 124 367.5C97.2 383 88 417.2 103.5 444C119 470.8 153.2 480 180 464.5C199.3 453.4 209.4 432.5 207.8 411.7L258.3 382.8C246.8 371.6 238.4 357.2 234.5 341.1L184 370.1C181.4 368.3 178.8 366.8 176 365.4L176 274.6C178.8 273.3 181.5 271.7 184 269.9L264.1 315.7C264 317.1 263.9 318.5 263.9 320C263.9 342.3 277 361.6 295.9 370.6L295.9 469.4C277 478.4 263.9 497.7 263.9 520C263.9 550.9 289 576 319.9 576C350.8 576 375.9 550.9 375.9 520C375.9 497.7 362.8 478.4 343.9 469.4L343.9 370.6C346.7 369.3 349.4 367.7 351.9 365.9L432 411.7C430.4 432.5 440.6 453.3 459.8 464.5C486.6 480 520.8 470.8 536.3 444C551.8 417.2 542.6 383 515.8 367.5C514.5 366.7 513.1 366 511.8 365.4L511.8 274.6C513.2 274 514.5 273.3 515.8 272.5C542.6 257 551.8 222.8 536.3 196C520.8 169.2 486.8 160 460 175.5C440.7 186.6 430.6 207.5 432.2 228.3L381.6 257.2C393.1 268.4 401.5 282.8 405.4 298.9L456 269.9C458.6 271.7 461.2 273.2 464 274.6L464 365.4C461.2 366.7 458.5 368.3 456 370L375.9 324.2C376 322.8 376.1 321.4 376.1 319.9C376.1 297.6 363 278.3 344.1 269.3L344.1 170.5z" />
    </svg>
  );
}

function ChevronIcon({ isOpen }: { isOpen: boolean }) {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="currentColor"
      className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`}
    >
      <path d="M4 6l4 4 4-4" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
      <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
    </svg>
  );
}
