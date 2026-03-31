/** macOS-style progress bar */
import { css, keyframes } from '@emotion/react';

interface ProgressBarProps {
  value: number | null; // 0-100; null = indeterminate
  variant?: 'default' | 'success' | 'danger';
}

const stripeAnim = keyframes`
  from { background-position: 0 0; }
  to   { background-position: 28px 0; }
`;

const trackStyle = css`
  width: 100%;
  height: 6px;
  background: rgba(0,0,0,0.10);
  border-radius: 3px;
  overflow: hidden;
`;

const fillBase = css`
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
`;

const indeterminate = css`
  width: 40% !important;
  background: linear-gradient(90deg, #007AFF 0%, #5ac8fa 100%);
  animation: ${stripeAnim} 1s linear infinite;
  transform-origin: left;
`;

export function ProgressBar({ value, variant = 'default' }: ProgressBarProps) {
  const color =
    variant === 'success' ? '#34C759' : variant === 'danger' ? '#FF3B30' : '#007AFF';

  return (
    <div css={trackStyle}>
      <div
        css={[fillBase, value === null && indeterminate]}
        style={{
          width: value !== null ? `${Math.max(0, Math.min(100, value))}%` : undefined,
          background: value !== null ? color : undefined,
        }}
      />
    </div>
  );
}
