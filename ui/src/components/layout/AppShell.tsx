/** App shell layout */
import { css } from '@emotion/react';
import { Sidebar } from './Sidebar';
import { TitleBar } from './TitleBar';
import type { ReactNode } from 'react';

const shellStyle = css`
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
`;

const bodyStyle = css`
  display: flex;
  flex: 1;
  overflow: hidden;
`;

const contentStyle = css`
  flex: 1;
  overflow-y: auto;
  background: #f5f5f7;
`;

interface AppShellProps {
  children: ReactNode;
  title?: string;
}

export function AppShell({ children, title = '一歌小助手 iaa' }: AppShellProps) {
  return (
    <div css={shellStyle}>
      <TitleBar title={title} />
      <div css={bodyStyle}>
        <Sidebar />
        <main css={contentStyle}>
          {children}
        </main>
      </div>
    </div>
  );
}
