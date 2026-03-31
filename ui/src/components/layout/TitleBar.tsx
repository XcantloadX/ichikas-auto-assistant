/** macOS-style title bar */
import { css } from '@emotion/react';
import { useAppStore } from '@/stores/useAppStore';

const barStyle = css`
  height: 38px;
  background: #d8d8d8;
  border-bottom: 1px solid rgba(0,0,0,0.14);
  display: flex;
  align-items: center;
  padding: 0 14px;
  flex-shrink: 0;
  -webkit-app-region: drag;
  user-select: none;
`;

const trafficLightsStyle = css`
  display: flex;
  gap: 6px;
  margin-right: 14px;
  -webkit-app-region: no-drag;
`;

const dotStyle = css`
  width: 12px;
  height: 12px;
  border-radius: 50%;
`;

const titleStyle = css`
  font-size: 13px;
  font-weight: 600;
  color: rgba(0,0,0,0.65);
  flex: 1;
  text-align: center;
  pointer-events: none;
`;

const wsIndicatorStyle = css`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
`;

const wsColors = {
  connected: '#34C759',
  connecting: '#FF9500',
  disconnected: '#8E8E93',
  error: '#FF3B30',
};

export function TitleBar({ title }: { title: string }) {
  const wsStatus = useAppStore(s => s.wsStatus);

  return (
    <div css={barStyle}>
      <div css={trafficLightsStyle}>
        <div css={dotStyle} style={{ background: '#FF5F57' }} />
        <div css={dotStyle} style={{ background: '#FEBC2E' }} />
        <div css={dotStyle} style={{ background: '#28C840' }} />
      </div>
      <span css={titleStyle}>{title}</span>
      <div
        css={wsIndicatorStyle}
        style={{ background: wsColors[wsStatus] }}
        title={`WebSocket: ${wsStatus}`}
      />
    </div>
  );
}
