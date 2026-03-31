/** Form row: label + control side by side */
import { css } from '@emotion/react';
import type { ReactNode } from 'react';

interface FormRowProps {
  label: string;
  children: ReactNode;
}

const rowStyle = css`
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;

  &:last-child {
    margin-bottom: 0;
  }
`;

const labelStyle = css`
  min-width: 110px;
  font-size: 13px;
  color: rgba(0,0,0,0.7);
  text-align: right;
  flex-shrink: 0;
`;

export function FormRow({ label, children }: FormRowProps) {
  return (
    <div css={rowStyle}>
      <span css={labelStyle}>{label}</span>
      <div style={{ flex: 1 }}>{children}</div>
    </div>
  );
}
