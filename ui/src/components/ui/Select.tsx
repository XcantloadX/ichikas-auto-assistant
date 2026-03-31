/** macOS-style Select / Combobox */
import { css } from '@emotion/react';
import type { SelectHTMLAttributes } from 'react';

const selectStyle = css`
  appearance: none;
  -webkit-appearance: none;
  height: 22px;
  padding: 0 24px 0 8px;
  background: linear-gradient(180deg, #fff 0%, #f5f5f5 100%)
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23555'/%3E%3C/svg%3E")
    no-repeat right 8px center / 8px 5px;
  border: 1px solid rgba(0,0,0,0.22);
  border-radius: 6px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif;
  font-size: 13px;
  color: rgba(0,0,0,0.85);
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
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
  }
`;

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select css={selectStyle} {...props} />;
}
