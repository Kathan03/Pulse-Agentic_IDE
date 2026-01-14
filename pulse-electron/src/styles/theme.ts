/**
 * Pulse IDE Theme Configuration
 *
 * VS Code Dark-inspired theme with custom Pulse accent colors.
 */

export const theme = {
  // Core backgrounds
  background: '#1E1E1E',
  backgroundSecondary: '#252526',
  backgroundTertiary: '#2D2D2D',

  // Foregrounds
  foreground: '#CCCCCC',
  foregroundMuted: '#808080',

  // Borders
  border: '#2B2B2B',
  borderActive: '#007ACC',

  // Inputs
  input: '#313131',
  inputFocus: '#3C3C3C',

  // Primary accent (blue)
  primary: '#0078D4',
  primaryHover: '#1C8AE6',

  // Status colors
  success: '#89D185',
  warning: '#CCA700',
  error: '#F48771',
  info: '#3794FF',

  // Vibe loader colors (by category)
  vibe: {
    thinking: '#3794FF', // Blue - pondering, analyzing
    context: '#CCA700', // Gold - gathering, mustering
    action: '#89D185', // Green - executing, building
  },

  // Editor specific
  editor: {
    lineNumber: '#858585',
    selection: '#264F78',
    currentLine: '#282828',
    findMatch: '#515C6A',
    findMatchHighlight: '#EA5C0055',
  },
} as const;

/**
 * Vibe words organized by category.
 * The loader picks random words from the active category.
 */
export const vibeWords = {
  thinking: [
    'Wondering',
    'Pondering',
    'Contemplating',
    'Analyzing',
    'Considering',
    'Reflecting',
    'Deliberating',
    'Examining',
    'Reasoning',
    'Evaluating',
  ],
  context: [
    'Mustering',
    'Coalescing',
    'Ideating',
    'Gathering',
    'Assembling',
    'Synthesizing',
    'Composing',
    'Organizing',
    'Structuring',
    'Consolidating',
  ],
  action: [
    'Completing',
    'Executing',
    'Building',
    'Creating',
    'Implementing',
    'Crafting',
    'Generating',
    'Producing',
    'Constructing',
    'Finalizing',
  ],
} as const;

export type VibeCategory = keyof typeof vibeWords;
