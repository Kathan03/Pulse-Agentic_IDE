/**
 * ActivityBar - Left Icon Strip
 *
 * VS Code-style activity bar with icons for different views.
 */

import { useState } from 'react';
import { useUIStore, type ActivityBarItem } from '@/stores/uiStore';
import { useTheme, themes, ThemeIcon, type ThemeName } from '@/contexts/ThemeContext';

export function ActivityBar() {
  const { activeActivityItem, setActiveActivityItem, sidebarVisible } = useUIStore();

  const items: Array<{ id: ActivityBarItem; icon: React.ReactNode; title: string }> = [
    { id: 'explorer', icon: <ExplorerIcon />, title: 'Explorer' },
    { id: 'search', icon: <SearchIcon />, title: 'Search' },
    { id: 'sourceControl', icon: <GitIcon />, title: 'Source Control' },
    { id: 'extensions', icon: <ExtensionsIcon />, title: 'Extensions' },
  ];

  return (
    <div className="w-activitybar bg-pulse-bg-secondary flex flex-col items-center py-1 border-r border-pulse-border">
      {/* Main Items */}
      <div className="flex flex-col items-center space-y-1">
        {items.map((item) => (
          <ActivityBarButton
            key={item.id}
            isActive={activeActivityItem === item.id && sidebarVisible}
            onClick={() => setActiveActivityItem(item.id)}
            title={item.title}
          >
            {item.icon}
          </ActivityBarButton>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Bottom Items */}
      <div className="flex flex-col items-center space-y-1 mb-1">
        {/* Theme Switcher - Settings removed per Issue 9, access via Menu Bar only */}
        <ThemeSwitcher />
      </div>
    </div>
  );
}

// ============================================================================
// Theme Switcher
// ============================================================================

/**
 * ThemeSwitcher - Portfolio-style animated theme toggle (Issue 10)
 *
 * Features:
 * - All 5 theme icons rendered in a stack
 * - Active icon visible with scale(1) rotate(0deg)
 * - Inactive icons hidden with scale(0.5) rotate(-90deg)
 * - Smooth CSS transitions between states
 * - Hover rotation effect (15deg)
 */
function ThemeSwitcher() {
  const { theme, setTheme, cycleTheme, themeName } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const themeList = Object.values(themes);
  const themeOrder: ThemeName[] = [
    'midnight-pulse',
    'solar-flare',
    'nebula',
    'emerald-flow',
    'crimson-horizon',
  ];

  return (
    <div className="relative">
      {/* Theme Toggle Button - Portfolio Style */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        onContextMenu={(e) => {
          e.preventDefault();
          cycleTheme();
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        title={`Theme: ${theme.label} (Click to change, Right-click to cycle)`}
        className="w-12 h-12 flex items-center justify-center text-pulse-primary transition-transform duration-300 hover:scale-110"
      >
        {/* Stacked Icons Container - All icons rendered but only active one visible */}
        <div
          className="relative w-6 h-6"
          style={{
            transform: isHovered ? 'rotate(15deg)' : 'rotate(0deg)',
            transition: 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
          }}
        >
          {themeOrder.map((name) => {
            const isActive = themeName === name;
            const iconType = themes[name].icon;

            return (
              <div
                key={name}
                className="absolute inset-0"
                style={{
                  opacity: isActive ? 1 : 0,
                  transform: isActive ? 'scale(1) rotate(0deg)' : 'scale(0.5) rotate(-90deg)',
                  transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                  transformOrigin: 'center',
                }}
              >
                <ThemeIcon icon={iconType} className="w-full h-full" />
              </div>
            );
          })}
        </div>
      </button>

      {/* Theme Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Menu */}
          <div className="absolute left-full bottom-0 ml-2 z-50 bg-pulse-bg-secondary border border-pulse-border rounded-lg shadow-dropdown overflow-hidden min-w-[180px]">
            <div className="p-2 border-b border-pulse-border">
              <span className="text-xs font-semibold text-pulse-fg-muted uppercase tracking-wide">
                Select Theme
              </span>
            </div>
            {themeList.map((t) => (
              <button
                key={t.name}
                onClick={() => {
                  setTheme(t.name);
                  setIsOpen(false);
                }}
                className={`
                  w-full px-3 py-2 flex items-center gap-3 text-sm
                  hover:bg-pulse-bg-tertiary transition-colors
                  ${theme.name === t.name ? 'bg-pulse-selection text-pulse-primary' : 'text-pulse-fg'}
                `}
              >
                <ThemeIcon icon={t.icon} className="w-4 h-4" />
                <span>{t.label}</span>
                {theme.name === t.name && (
                  <span className="ml-auto text-pulse-success">✓</span>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

interface ActivityBarButtonProps {
  isActive: boolean;
  onClick: () => void;
  title: string;
  children: React.ReactNode;
}

function ActivityBarButton({ isActive, onClick, title, children }: ActivityBarButtonProps) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`
        w-12 h-12 flex items-center justify-center
        text-pulse-fg-muted hover:text-pulse-fg
        transition-colors relative
        ${isActive ? 'text-pulse-fg' : ''}
      `}
    >
      {/* Active indicator */}
      {isActive && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-pulse-primary rounded-r" />
      )}
      <div className="w-6 h-6">{children}</div>
    </button>
  );
}

// ============================================================================
// Icons
// ============================================================================

function ExplorerIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-full h-full">
      <path d="M3 7v13a1 1 0 001 1h16a1 1 0 001-1V7" />
      <path d="M3 7l3-4h5l2 2h8a1 1 0 011 1v1H3z" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-full h-full">
      <circle cx="10" cy="10" r="7" />
      <path d="M15 15l6 6" />
    </svg>
  );
}

function GitIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-full h-full">
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <path d="M6 9v6M15 6H9M6 15V9c0 6 12 6 12 0" />
    </svg>
  );
}

function ExtensionsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-full h-full">
      <rect x="3" y="3" width="8" height="8" rx="1" />
      <rect x="13" y="3" width="8" height="8" rx="1" />
      <rect x="3" y="13" width="8" height="8" rx="1" />
      <rect x="13" y="13" width="8" height="8" rx="1" />
    </svg>
  );
}
