/** macOS-style Checkbox */
import { css } from '@emotion/react';
import type { InputHTMLAttributes } from 'react';

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
}

const wrapperStyle = css`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  color: rgba(0,0,0,0.85);

  input {
    width: 14px;
    height: 14px;
    accent-color: #007AFF;
    cursor: pointer;
  }
`;

export function Checkbox({ label, id, ...props }: CheckboxProps) {
  return (
    <label css={wrapperStyle} htmlFor={id}>
      <input type="checkbox" id={id} {...props} />
      {label && <span>{label}</span>}
    </label>
  );
}
