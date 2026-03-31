/** About page */
import { css } from '@emotion/react';
import { useVersion } from '@/hooks/useRpc';

const pageStyle = css`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px 20px;
`;

const logoStyle = css`
  width: 80px;
  height: 80px;
  border-radius: 20px;
  object-fit: cover;
  margin-bottom: 16px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.18);
`;

const titleStyle = css`
  font-size: 20px;
  font-weight: 700;
  color: rgba(0,0,0,0.85);
  margin-bottom: 4px;
`;

const subtitleStyle = css`
  font-size: 13px;
  color: rgba(0,0,0,0.45);
  margin-bottom: 24px;
`;

const linksStyle = css`
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  justify-content: center;
`;

const linkStyle = css`
  font-size: 13px;
  color: #007AFF;
  text-decoration: none;
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
`;

const LINKS = [
  { label: 'GitHub', url: 'https://github.com/XcantloadX/ichikas-auto-assistant' },
  { label: 'Bilibili', url: 'https://space.bilibili.com/3546853903698457' },
  { label: '教程文档', url: 'https://p.kdocs.cn/s/AGBH56RBAAAFS' },
  { label: 'QQ 群', url: 'https://qm.qq.com/q/Mu1SSfK1Gg' },
];

export function AboutPage() {
  const versionQ = useVersion();
  const version = versionQ.data?.version ?? '…';

  return (
    <div css={pageStyle}>
      <img
        css={logoStyle}
        src="/logo.png"
        alt="一歌小助手"
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = 'none';
        }}
      />
      <div css={titleStyle}>一歌小助手 iaa</div>
      <div css={subtitleStyle}>版本 v{version}</div>
      <div css={linksStyle}>
        {LINKS.map(l => (
          <a
            key={l.label}
            css={linkStyle}
            href={l.url}
            target="_blank"
            rel="noreferrer"
          >
            {l.label}
          </a>
        ))}
      </div>
    </div>
  );
}
