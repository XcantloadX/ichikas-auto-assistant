/** macOS-style sidebar navigation */
import { css } from '@emotion/react';
import { useAppStore, type Page } from '@/stores/useAppStore';
import { useStatusStore } from '@/stores/useStatusStore';

const sidebarStyle = css`
  width: 160px;
  min-width: 160px;
  background: #e8e8e8;
  border-right: 1px solid rgba(0,0,0,0.12);
  display: flex;
  flex-direction: column;
  padding: 8px 0;
  overflow: hidden;
`;

const itemStyle = css`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 6px;
  margin: 0 6px 2px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(0,0,0,0.7);
  cursor: pointer;
  user-select: none;
  transition: background 0.12s ease;

  &:hover {
    background: rgba(0,0,0,0.06);
  }
`;

const activeItemStyle = css`
  background: rgba(0,122,255,0.14);
  color: #007AFF;

  &:hover {
    background: rgba(0,122,255,0.18);
  }
`;

const statusDotStyle = css`
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-left: auto;
`;

interface NavItem {
  id: Page;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'main',     label: '控制',    icon: '▶' },
  { id: 'settings', label: '设置',    icon: '⚙' },
  { id: 'about',    label: '关于',    icon: 'ℹ' },
];

export function Sidebar() {
  const { page, setPage } = useAppStore();
  const status = useStatusStore(s => s.status);

  const isRunning = status?.running || status?.is_starting;

  return (
    <nav css={sidebarStyle}>
      {NAV_ITEMS.map(item => (
        <div
          key={item.id}
          css={[itemStyle, page === item.id && activeItemStyle]}
          onClick={() => setPage(item.id)}
        >
          <span>{item.icon}</span>
          <span>{item.label}</span>
          {item.id === 'main' && (
            <span
              css={statusDotStyle}
              style={{
                background: status?.is_starting
                  ? '#FF9500'
                  : isRunning
                  ? '#34C759'
                  : 'transparent',
              }}
            />
          )}
        </div>
      ))}
    </nav>
  );
}
