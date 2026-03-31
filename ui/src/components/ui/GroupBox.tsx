/** macOS-style GroupBox (Labelframe equivalent) */
import { css } from '@emotion/react';
import type { ReactNode } from 'react';

interface GroupBoxProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

const boxStyle = css`
  border: 1px solid rgba(0,0,0,0.14);
  border-radius: 10px;
  background: rgba(255,255,255,0.65);
  backdrop-filter: blur(4px);
  padding: 12px 16px 14px;
  margin-bottom: 12px;
`;

const titleStyle = css`
  font-size: 12px;
  font-weight: 600;
  color: rgba(0,0,0,0.55);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 10px;
`;

export function GroupBox({ title, children, className }: GroupBoxProps) {
  return (
    <div css={boxStyle} className={className}>
      {title && <div css={titleStyle}>{title}</div>}
      {children}
    </div>
  );
}
