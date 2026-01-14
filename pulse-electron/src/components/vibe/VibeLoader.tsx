/**
 * VibeLoader - Animated Status Indicator
 *
 * Shows a pulsating dot with cycling words based on the agent's activity category.
 */

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAgentStore } from '@/stores/agentStore';
import { vibeWords, type VibeCategory } from '@/styles/theme';

// Colors for each category
const categoryColors: Record<VibeCategory, string> = {
  thinking: '#3794FF',
  context: '#CCA700',
  action: '#89D185',
};

export function VibeLoader() {
  const { vibe } = useAgentStore();
  const { isActive, category, currentWord } = vibe;

  const [displayWord, setDisplayWord] = useState(currentWord || getRandomWord(category));

  // Cycle words when active
  useEffect(() => {
    if (!isActive) return;

    const interval = setInterval(() => {
      setDisplayWord(getRandomWord(category));
    }, 2000);

    return () => clearInterval(interval);
  }, [isActive, category]);

  // Update display word when currentWord changes from backend
  useEffect(() => {
    if (currentWord) {
      setDisplayWord(currentWord);
    }
  }, [currentWord]);

  if (!isActive) return null;

  const color = categoryColors[category];

  return (
    <div className="flex items-center space-x-3">
      {/* Pulsating Dot */}
      <VibePulse color={color} />

      {/* Animated Word */}
      <VibeWord word={displayWord} color={color} />
    </div>
  );
}

// ============================================================================
// VibePulse - Pulsating Dot with Glow
// ============================================================================

function VibePulse({ color }: { color: string }) {
  return (
    <motion.div
      className="relative w-3 h-3"
      animate={{
        scale: [1, 1.2, 1],
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
    >
      {/* Glow effect */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{ backgroundColor: color }}
        animate={{
          boxShadow: [
            `0 0 4px 2px ${color}40`,
            `0 0 12px 4px ${color}60`,
            `0 0 4px 2px ${color}40`,
          ],
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Core dot */}
      <div
        className="absolute inset-0 rounded-full"
        style={{ backgroundColor: color }}
      />
    </motion.div>
  );
}

// ============================================================================
// VibeWord - Animated Word Transition
// ============================================================================

function VibeWord({ word, color }: { word: string; color: string }) {
  return (
    <div className="relative h-5 overflow-hidden">
      <AnimatePresence mode="wait">
        <motion.span
          key={word}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className="text-sm font-medium"
          style={{ color }}
        >
          {word}...
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

// ============================================================================
// Helper
// ============================================================================

function getRandomWord(category: VibeCategory): string {
  const words = vibeWords[category];
  return words[Math.floor(Math.random() * words.length)];
}
