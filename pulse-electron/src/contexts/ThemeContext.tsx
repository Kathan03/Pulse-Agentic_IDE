/**
 * Theme Context - Centralized Theme Management
 *
 * Provides 5 distinct professional themes for Pulse IDE:
 * 1. Midnight Pulse (Default) - Deep charcoal with Pulse Orange accents
 * 2. Solar Flare - Clean paper-white/gray with orange primary
 * 3. Nebula - Deep violet/black with neon cyan/magenta
 * 4. Emerald Flow - Dark slate green with seafoam accents
 * 5. Crimson Horizon - Warm dark browns with sunset gradients
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

// ============================================================================
// Theme Definitions
// ============================================================================

export type ThemeName = 'midnight-pulse' | 'solar-flare' | 'nebula' | 'emerald-flow' | 'crimson-horizon';

export interface ThemeColors {
  // Core backgrounds
  bg: string;
  bgSecondary: string;
  bgTertiary: string;

  // Foregrounds
  fg: string;
  fgMuted: string;

  // Borders
  border: string;
  borderActive: string;

  // Inputs
  input: string;
  inputFocus: string;

  // Primary accent
  primary: string;
  primaryHover: string;

  // Status colors
  success: string;
  warning: string;
  error: string;
  info: string;

  // Selection
  selection: string;

  // Vibe colors
  vibeThinking: string;
  vibeContext: string;
  vibeAction: string;
}

export interface Theme {
  name: ThemeName;
  label: string;
  icon: 'moon' | 'sun' | 'stars' | 'leaf' | 'sunset';
  isDark: boolean;
  colors: ThemeColors;
}

// Theme definitions
export const themes: Record<ThemeName, Theme> = {
  'midnight-pulse': {
    name: 'midnight-pulse',
    label: 'Midnight Pulse',
    icon: 'moon',
    isDark: true,
    colors: {
      bg: '#1F1F1F',
      bgSecondary: '#252526',
      bgTertiary: '#2D2D2D',
      fg: '#CCCCCC',
      fgMuted: '#808080',
      border: '#2B2B2B',
      borderActive: '#FF521B',
      input: '#313131',
      inputFocus: '#3C3C3C',
      primary: '#FF521B',
      primaryHover: '#FF7043',
      success: '#89D185',
      warning: '#CCA700',
      error: '#F48771',
      info: '#3794FF',
      selection: '#3A2618',
      vibeThinking: '#3794FF',
      vibeContext: '#CCA700',
      vibeAction: '#89D185',
    },
  },
  'solar-flare': {
    name: 'solar-flare',
    label: 'Solar Flare',
    icon: 'sun',
    isDark: false,
    colors: {
      bg: '#FFFFFF',
      bgSecondary: '#F5F5F5',
      bgTertiary: '#EBEBEB',
      fg: '#1A1A1A',
      fgMuted: '#6B6B6B',
      border: '#E0E0E0',
      borderActive: '#FF521B',
      input: '#FFFFFF',
      inputFocus: '#F0F0F0',
      primary: '#FF521B',
      primaryHover: '#E64A19',
      success: '#2E7D32',
      warning: '#F57C00',
      error: '#C62828',
      info: '#1565C0',
      selection: '#FFE0B2',
      vibeThinking: '#1565C0',
      vibeContext: '#F57C00',
      vibeAction: '#2E7D32',
    },
  },
  'nebula': {
    name: 'nebula',
    label: 'Nebula',
    icon: 'stars',
    isDark: true,
    colors: {
      bg: '#1A103C',
      bgSecondary: '#221548',
      bgTertiary: '#2B1D55',
      fg: '#E0E0FF',
      fgMuted: '#9090C0',
      border: '#3D2D6B',
      borderActive: '#00FFFF',
      input: '#2B1D55',
      inputFocus: '#352665',
      primary: '#00FFFF',
      primaryHover: '#40FFFF',
      success: '#00FF88',
      warning: '#FFAA00',
      error: '#FF5577',
      info: '#8080FF',
      selection: '#4A3D7A',
      vibeThinking: '#8080FF',
      vibeContext: '#FF00FF',
      vibeAction: '#00FF88',
    },
  },
  'emerald-flow': {
    name: 'emerald-flow',
    label: 'Emerald Flow',
    icon: 'leaf',
    isDark: true,
    colors: {
      bg: '#1A2421',
      bgSecondary: '#202D29',
      bgTertiary: '#273632',
      fg: '#D0E8E0',
      fgMuted: '#7A9990',
      border: '#2E3D38',
      borderActive: '#4ECDC4',
      input: '#273632',
      inputFocus: '#2E403A',
      primary: '#4ECDC4',
      primaryHover: '#6EDDD5',
      success: '#95E1A3',
      warning: '#F4D03F',
      error: '#E74C3C',
      info: '#5DADE2',
      selection: '#2A4540',
      vibeThinking: '#5DADE2',
      vibeContext: '#F4D03F',
      vibeAction: '#4ECDC4',
    },
  },
  'crimson-horizon': {
    name: 'crimson-horizon',
    label: 'Crimson Horizon',
    icon: 'sunset',
    isDark: true,
    colors: {
      bg: '#1F1612',
      bgSecondary: '#2A1F19',
      bgTertiary: '#352820',
      fg: '#F0E6DC',
      fgMuted: '#A08878',
      border: '#3D2E24',
      borderActive: '#FF6B35',
      input: '#352820',
      inputFocus: '#403028',
      primary: '#FF6B35',
      primaryHover: '#FF8855',
      success: '#A8D08D',
      warning: '#F5B041',
      error: '#E74C3C',
      info: '#85C1E9',
      selection: '#4A3528',
      vibeThinking: '#85C1E9',
      vibeContext: '#F5B041',
      vibeAction: '#A8D08D',
    },
  },
};

// ============================================================================
// Context
// ============================================================================

interface ThemeContextValue {
  theme: Theme;
  themeName: ThemeName;
  setTheme: (name: ThemeName) => void;
  cycleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

// ============================================================================
// Provider
// ============================================================================

const THEME_STORAGE_KEY = 'pulse-theme';

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [themeName, setThemeName] = useState<ThemeName>(() => {
    // Load from localStorage
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      if (saved && saved in themes) {
        return saved as ThemeName;
      }
    }
    return 'midnight-pulse';
  });

  const theme = themes[themeName];

  // Apply theme CSS variables
  useEffect(() => {
    const root = document.documentElement;
    const { colors } = theme;

    // Set CSS custom properties
    root.style.setProperty('--pulse-bg', colors.bg);
    root.style.setProperty('--pulse-bg-secondary', colors.bgSecondary);
    root.style.setProperty('--pulse-bg-tertiary', colors.bgTertiary);
    root.style.setProperty('--pulse-fg', colors.fg);
    root.style.setProperty('--pulse-fg-muted', colors.fgMuted);
    root.style.setProperty('--pulse-border', colors.border);
    root.style.setProperty('--pulse-border-active', colors.borderActive);
    root.style.setProperty('--pulse-input', colors.input);
    root.style.setProperty('--pulse-input-focus', colors.inputFocus);
    root.style.setProperty('--pulse-primary', colors.primary);
    root.style.setProperty('--pulse-primary-hover', colors.primaryHover);
    root.style.setProperty('--pulse-success', colors.success);
    root.style.setProperty('--pulse-warning', colors.warning);
    root.style.setProperty('--pulse-error', colors.error);
    root.style.setProperty('--pulse-info', colors.info);
    root.style.setProperty('--pulse-selection', colors.selection);
    root.style.setProperty('--pulse-vibe-thinking', colors.vibeThinking);
    root.style.setProperty('--pulse-vibe-context', colors.vibeContext);
    root.style.setProperty('--pulse-vibe-action', colors.vibeAction);

    // Set data attribute for conditional styling
    root.setAttribute('data-theme', themeName);
    root.setAttribute('data-theme-mode', theme.isDark ? 'dark' : 'light');

    // Save to localStorage
    localStorage.setItem(THEME_STORAGE_KEY, themeName);
  }, [theme, themeName]);

  const setTheme = useCallback((name: ThemeName) => {
    setThemeName(name);
  }, []);

  const cycleTheme = useCallback(() => {
    const themeNames = Object.keys(themes) as ThemeName[];
    const currentIndex = themeNames.indexOf(themeName);
    const nextIndex = (currentIndex + 1) % themeNames.length;
    setThemeName(themeNames[nextIndex]);
  }, [themeName]);

  return (
    <ThemeContext.Provider value={{ theme, themeName, setTheme, cycleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

// ============================================================================
// Theme Icons
// ============================================================================

export function ThemeIcon({ icon, className = '', style }: { icon: Theme['icon']; className?: string; style?: React.CSSProperties }) {
  switch (icon) {
    case 'moon':
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
      );
    case 'sun':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
          <circle fill="currentColor" cx="12" cy="12" r="4"></circle>
          <path d="M12 2v2m0 16v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M2 12h2m16 0h2M4.22 19.78l1.42-1.42m12.72-12.72l1.42-1.42"></path>
        </svg>
      );
    case 'stars':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
          <path d="M12 2l2 6h6l-5 4 2 6-5-4-5 4 2-6-5-4h6z"></path>
          <circle cx="19" cy="5" r="2"></circle>
          <circle cx="5" cy="19" r="2"></circle>
        </svg>
      );
    case 'leaf':
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" className={className} style={style}>
          <path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75C7 8 17 8 17 8z" />
        </svg>
      );
    case 'sunset':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
          <circle cx="12" cy="10" r="3"></circle>
          <path d="M18 16c1.66 0 3-1.34 3-3s-1.34-3-3-3c-.17 0-.33.02-.5.05C16.95 8.19 15.11 7 13 7c-2.76 0-5 2.24-5 5 0 .34.04.67.09 1H6c-1.66 0-3 1.34-3 3s1.34 3 3 3h12z"></path>
        </svg>
      );
  }
}
