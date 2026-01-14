/**
 * FoxMascot - The "Face" of the AI Agent
 *
 * Pixel-art style fox mascot used in the agent panel.
 * Supports custom colors via CSS custom properties.
 */

import React from 'react';

interface FoxMascotProps {
  className?: string;
  bodyColor?: string;
  eyeColor?: string;
}

export function FoxMascot({
  className = '',
  bodyColor = '#FF521B',
  eyeColor = '#FFFFFF'
}: FoxMascotProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 250 250"
      className={`w-full h-full ${className}`}
      style={{
        ['--fox-body' as string]: bodyColor,
        ['--fox-eye' as string]: eyeColor,
      } as React.CSSProperties}
    >
      <g shapeRendering="crispEdges">
        {/* Ears */}
        <rect x="90" y="80" width="10" height="10" fill="var(--fox-body)" />
        <rect x="150" y="80" width="10" height="10" fill="var(--fox-body)" />
        <rect x="90" y="90" width="10" height="10" fill="var(--fox-body)" />
        <rect x="100" y="90" width="10" height="10" fill="var(--fox-body)" />
        <rect x="140" y="90" width="10" height="10" fill="var(--fox-body)" />
        <rect x="150" y="90" width="10" height="10" fill="var(--fox-body)" />

        {/* Top of head */}
        <rect x="90" y="100" width="10" height="10" fill="var(--fox-body)" />
        <rect x="100" y="100" width="10" height="10" fill="var(--fox-body)" />
        <rect x="110" y="100" width="10" height="10" fill="var(--fox-body)" />
        <rect x="120" y="100" width="10" height="10" fill="var(--fox-body)" />
        <rect x="130" y="100" width="10" height="10" fill="var(--fox-body)" />
        <rect x="140" y="100" width="10" height="10" fill="var(--fox-body)" />
        <rect x="150" y="100" width="10" height="10" fill="var(--fox-body)" />

        {/* Head rows */}
        <rect x="80" y="110" width="10" height="10" fill="var(--fox-body)" />
        <rect x="90" y="110" width="10" height="10" fill="var(--fox-body)" />
        <rect x="100" y="110" width="10" height="10" fill="var(--fox-body)" />
        <rect x="110" y="110" width="10" height="10" fill="var(--fox-body)" />
        <rect x="120" y="110" width="10" height="10" fill="var(--fox-body)" />
        <rect x="130" y="110" width="10" height="10" fill="var(--fox-body)" />
        <rect x="140" y="110" width="10" height="10" fill="var(--fox-body)" />
        <rect x="150" y="110" width="10" height="10" fill="var(--fox-body)" />
        <rect x="160" y="110" width="10" height="10" fill="var(--fox-body)" />

        <rect x="80" y="120" width="10" height="10" fill="var(--fox-body)" />
        <rect x="90" y="120" width="10" height="10" fill="var(--fox-body)" />
        <rect x="100" y="120" width="10" height="10" fill="var(--fox-body)" />
        <rect x="110" y="120" width="10" height="10" fill="var(--fox-body)" />
        <rect x="120" y="120" width="10" height="10" fill="var(--fox-body)" />
        <rect x="130" y="120" width="10" height="10" fill="var(--fox-body)" />
        <rect x="140" y="120" width="10" height="10" fill="var(--fox-body)" />
        <rect x="150" y="120" width="10" height="10" fill="var(--fox-body)" />
        <rect x="160" y="120" width="10" height="10" fill="var(--fox-body)" />

        {/* Eyes row */}
        <rect x="80" y="130" width="10" height="10" fill="var(--fox-body)" />
        <rect x="90" y="130" width="10" height="10" fill="var(--fox-body)" />
        <rect x="100" y="130" width="10" height="10" fill="var(--fox-eye)" />
        <rect x="110" y="130" width="10" height="10" fill="var(--fox-body)" />
        <rect x="120" y="130" width="10" height="10" fill="var(--fox-body)" />
        <rect x="130" y="130" width="10" height="10" fill="var(--fox-body)" />
        <rect x="140" y="130" width="10" height="10" fill="var(--fox-eye)" />
        <rect x="150" y="130" width="10" height="10" fill="var(--fox-body)" />
        <rect x="160" y="130" width="10" height="10" fill="var(--fox-body)" />

        {/* Lower face */}
        <rect x="90" y="140" width="10" height="10" fill="var(--fox-body)" />
        <rect x="100" y="140" width="10" height="10" fill="var(--fox-body)" />
        <rect x="110" y="140" width="10" height="10" fill="var(--fox-body)" />
        <rect x="120" y="140" width="10" height="10" fill="var(--fox-body)" />
        <rect x="130" y="140" width="10" height="10" fill="var(--fox-body)" />
        <rect x="140" y="140" width="10" height="10" fill="var(--fox-body)" />
        <rect x="150" y="140" width="10" height="10" fill="var(--fox-body)" />

        {/* Snout */}
        <rect x="110" y="150" width="10" height="10" fill="var(--fox-body)" />
        <rect x="120" y="150" width="10" height="10" fill="var(--fox-body)" />
        <rect x="130" y="150" width="10" height="10" fill="var(--fox-body)" />

        {/* Nose */}
        <rect x="120" y="160" width="10" height="10" fill="var(--fox-body)" />
      </g>
    </svg>
  );
}

export default FoxMascot;
