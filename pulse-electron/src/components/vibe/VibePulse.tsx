/**
 * VibePulse - Standalone Pulsating Indicator
 *
 * A minimal pulsating dot for use in various UI locations.
 */

import { motion } from 'framer-motion';
import type { VibeCategory } from '@/styles/theme';

const categoryColors: Record<VibeCategory, string> = {
  thinking: '#3794FF',
  context: '#CCA700',
  action: '#89D185',
};

interface VibePulseProps {
  category?: VibeCategory;
  size?: 'sm' | 'md' | 'lg';
  isActive?: boolean;
}

export function VibePulse({
  category = 'thinking',
  size = 'md',
  isActive = true,
}: VibePulseProps) {
  const color = categoryColors[category];

  const sizes = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4',
  };

  if (!isActive) {
    return (
      <div
        className={`${sizes[size]} rounded-full bg-pulse-fg-muted`}
      />
    );
  }

  return (
    <motion.div
      className={`relative ${sizes[size]}`}
      animate={{
        scale: [1, 1.2, 1],
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
    >
      {/* Glow ring */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{ backgroundColor: color }}
        animate={{
          opacity: [0.5, 0.8, 0.5],
          scale: [1, 1.5, 1],
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
