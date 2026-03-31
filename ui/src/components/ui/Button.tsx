/** macOS-style Button */
import { css } from '@emotion/react';
import type { ButtonHTMLAttributes } from 'react';

export type ButtonVariant = 'default' | 'primary' | 'danger' | 'success' | 'ghost';
export type ButtonSize = 'sm' | 'md';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const base = css`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border-radius: 6px;
  border: none;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: filter 0.12s ease, opacity 0.12s ease;
  white-space: nowrap;

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
`;

const sizeMap = {
  sm: css`padding: 3px 10px; font-size: 12px;`,
  md: css`padding: 5px 14px;`,
};

const variantMap: Record<ButtonVariant, ReturnType<typeof css>> = {
  default: css`
    background: linear-gradient(180deg, #ffffff 0%, #f0f0f0 100%);
    color: rgba(0,0,0,0.85);
    border: 1px solid rgba(0,0,0,0.22);
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    &:hover:not(:disabled) { filter: brightness(0.97); }
    &:active:not(:disabled) { filter: brightness(0.92); }
  `,
  primary: css`
    background: linear-gradient(180deg, #1c8cff 0%, #0070f0 100%);
    color: #fff;
    box-shadow: 0 1px 3px rgba(0,122,255,0.35);
    &:hover:not(:disabled) { filter: brightness(1.08); }
    &:active:not(:disabled) { filter: brightness(0.92); }
  `,
  danger: css`
    background: linear-gradient(180deg, #ff5c55 0%, #ff3b30 100%);
    color: #fff;
    box-shadow: 0 1px 3px rgba(255,59,48,0.35);
    &:hover:not(:disabled) { filter: brightness(1.08); }
    &:active:not(:disabled) { filter: brightness(0.92); }
  `,
  success: css`
    background: linear-gradient(180deg, #45d567 0%, #34c759 100%);
    color: #fff;
    box-shadow: 0 1px 3px rgba(52,199,89,0.35);
    &:hover:not(:disabled) { filter: brightness(1.08); }
    &:active:not(:disabled) { filter: brightness(0.92); }
  `,
  ghost: css`
    background: transparent;
    color: #007AFF;
    &:hover:not(:disabled) { background: rgba(0,122,255,0.08); }
    &:active:not(:disabled) { background: rgba(0,122,255,0.15); }
  `,
};

export function Button({
  variant = 'default',
  size = 'md',
  children,
  ...props
}: ButtonProps) {
  return (
    <button css={[base, sizeMap[size], variantMap[variant]]} {...props}>
      {children}
    </button>
  );
}
