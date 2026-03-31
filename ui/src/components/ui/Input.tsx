/** macOS-style text Input */
import { css } from '@emotion/react';
import type { InputHTMLAttributes } from 'react';

const inputStyle = css`
  height: 22px;
  padding: 0 8px;
  background: #fff;
  border: 1px solid rgba(0,0,0,0.22);
  border-radius: 6px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
  font-size: 13px;
  color: rgba(0,0,0,0.85);
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);
  transition: border-color 0.12s ease;
  min-width: 140px;

  &:focus {
    outline: none;
    border-color: #007AFF;
    box-shadow: 0 0 0 2px rgba(0,122,255,0.25);
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
    background: rgba(0,0,0,0.04);
  }
`;

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input css={inputStyle} {...props} />;
}
