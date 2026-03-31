/** macOS-style toast notification */
import { css, keyframes } from '@emotion/react';
import { useEffect } from 'react';
import { useAppStore } from '@/stores/useAppStore';

const slideIn = keyframes`
  from { transform: translateY(20px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
`;

const toastStyle = css`
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 18px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  box-shadow: 0 4px 16px rgba(0,0,0,0.25);
  animation: ${slideIn} 0.2s ease;
  z-index: 9999;
  white-space: nowrap;
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const kindColors = {
  success: '#34C759',
  error: '#FF3B30',
  info: 'rgba(0,0,0,0.75)',
};

export function Toast() {
  const { toast, clearToast } = useAppStore();

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(clearToast, 3000);
    return () => clearTimeout(t);
  }, [toast, clearToast]);

  if (!toast) return null;

  return (
    <div
      css={toastStyle}
      style={{ background: kindColors[toast.kind] }}
      onClick={clearToast}
    >
      {toast.message}
    </div>
  );
}
