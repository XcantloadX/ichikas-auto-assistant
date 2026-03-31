/** Settings page */
import { css } from '@emotion/react';
import { useState, useEffect } from 'react';
import { useConfig, useSaveConfig } from '@/hooks/useRpc';
import { useAppStore } from '@/stores/useAppStore';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { Checkbox } from '@/components/ui/Checkbox';
import { GroupBox } from '@/components/ui/GroupBox';
import { FormRow } from '@/components/ui/FormRow';
import type {
  IaaConfig,
  GameCharacter,
  ChallengeLiveAward,
} from '@/types';

const pageStyle = css`
  padding: 16px 20px;
  overflow-y: auto;
  height: 100%;
`;

const actionsStyle = css`
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
`;

const emptyStyle = css`
  font-size: 13px;
  color: rgba(0,0,0,0.40);
  padding: 40px 0;
  text-align: center;
`;

// ─── display maps ────────────────────────────────────────────────────────────

const EMULATOR_LABELS: Record<string, string> = {
  mumu: 'MuMu',
  mumu_v5: 'MuMu v5.x',
  custom: '自定义',
};
const SERVER_LABELS: Record<string, string> = { jp: '日服', tw: '台服' };
const LINK_LABELS: Record<string, string> = {
  no: '不引继账号',
  google: 'Google 账号',
  google_play: 'Google Play',
};
const CONTROL_LABELS: Record<string, string> = {
  nemu_ipc: 'Nemu IPC',
  adb: 'ADB',
  uiautomator: 'UIAutomator2',
};
const AWARD_LABELS: Record<string, string> = {
  crystal: '水晶',
  music_card: '音乐卡',
  miracle_gem: '奇迹晶石',
  magic_cloth: '魔法之布',
  coin: '硬币',
  intermediate_practice_score: '中级练习乐谱',
};

// Characters data
const CHARACTER_GROUPS: Array<{ group: string; chars: Array<{ id: GameCharacter; label: string }> }> = [
  {
    group: 'VIRTUAL SINGER',
    chars: [
      { id: 'miku', label: '初音未来' },
      { id: 'rin', label: '镜音铃' },
      { id: 'len', label: '镜音连' },
      { id: 'luka', label: '巡音流歌' },
      { id: 'meiko', label: 'MEIKO' },
      { id: 'kaito', label: 'KAITO' },
    ],
  },
  {
    group: 'Leo/need',
    chars: [
      { id: 'ichika', label: '星乃一歌' },
      { id: 'saki', label: '天马咲希' },
      { id: 'honami', label: '望月穗波' },
      { id: 'shiho', label: '日野森志步' },
    ],
  },
  {
    group: 'MORE MORE JUMP!',
    chars: [
      { id: 'minori', label: '花里实乃里' },
      { id: 'haruka', label: '桐谷遥' },
      { id: 'airi', label: '桃井爱莉' },
      { id: 'shizuku', label: '日野森雫' },
    ],
  },
  {
    group: 'Vivid BAD SQUAD',
    chars: [
      { id: 'kohane', label: '小豆泽心羽音' },
      { id: 'an', label: '白石杏' },
      { id: 'akito', label: '东云彰人' },
      { id: 'toya', label: '青柳冬弥' },
    ],
  },
  {
    group: 'ワンダーランズ×ショウタイム',
    chars: [
      { id: 'tsukasa', label: '天马司' },
      { id: 'emu', label: '凤笑梦' },
      { id: 'nene', label: '草薙宁宁' },
      { id: 'rui', label: '神代类' },
    ],
  },
  {
    group: '25時、ナイトコードで。',
    chars: [
      { id: 'kanade', label: '宵崎奏' },
      { id: 'mafuyu', label: '朝比奈真冬' },
      { id: 'ena', label: '东云绘名' },
      { id: 'mizuki', label: '晓山瑞希' },
    ],
  },
];

// ─── character multi-select ──────────────────────────────────────────────────

const charGroupsStyle = css`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;
const charGroupStyle = css`
  display: flex;
  flex-direction: column;
  gap: 2px;
`;
const charGroupLabelStyle = css`
  font-size: 11px;
  font-weight: 600;
  color: rgba(0,0,0,0.45);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
`;
const charRowStyle = css`
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
`;

interface CharSelectProps {
  value: GameCharacter[];
  onChange: (v: GameCharacter[]) => void;
}

function CharSelect({ value, onChange }: CharSelectProps) {
  function toggle(id: GameCharacter) {
    if (value.includes(id)) {
      onChange(value.filter(c => c !== id));
    } else {
      onChange([id]); // single-select per original UI
    }
  }
  return (
    <div css={charGroupsStyle}>
      {CHARACTER_GROUPS.map(g => (
        <div key={g.group} css={charGroupStyle}>
          <span css={charGroupLabelStyle}>{g.group}</span>
          <div css={charRowStyle}>
            {g.chars.map(c => (
              <Checkbox
                key={c.id}
                label={c.label}
                checked={value.includes(c.id)}
                onChange={() => toggle(c.id)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── main component ──────────────────────────────────────────────────────────

export function SettingsPage() {
  const showToast = useAppStore(s => s.showToast);
  const { data: config, isLoading } = useConfig();
  const saveConfig = useSaveConfig();

  // Local state (draft)
  const [draft, setDraft] = useState<IaaConfig | null>(null);

  useEffect(() => {
    if (config && !draft) {
      setDraft(JSON.parse(JSON.stringify(config)) as IaaConfig);
    }
  }, [config, draft]);

  if (isLoading || !draft) {
    return <div css={emptyStyle}>加载配置中…</div>;
  }

  function g<K extends keyof IaaConfig>(key: K) {
    return draft![key];
  }

  function setGame(field: string, value: unknown) {
    setDraft(prev => prev ? { ...prev, game: { ...prev.game, [field]: value } } : prev);
  }
  function setLive(field: string, value: unknown) {
    setDraft(prev => prev ? { ...prev, live: { ...prev.live, [field]: value } } : prev);
  }
  function setChallenge(field: string, value: unknown) {
    setDraft(prev => prev ? { ...prev, challenge_live: { ...prev.challenge_live, [field]: value } } : prev);
  }
  function setCm(field: string, value: unknown) {
    setDraft(prev => prev ? { ...prev, cm: { ...prev.cm, [field]: value } } : prev);
  }
  function setScheduler(field: string, value: unknown) {
    setDraft(prev => prev ? { ...prev, scheduler: { ...prev.scheduler, [field]: value } } : prev);
  }

  function handleSave() {
    if (!draft) return;
    saveConfig.mutate(draft, {
      onSuccess: () => showToast('保存成功', 'success'),
      onError: (e) => showToast(`保存失败：${e}`, 'error'),
    });
  }

  function handleReset() {
    if (config) setDraft(JSON.parse(JSON.stringify(config)) as IaaConfig);
  }

  const gameData = g('game');
  const liveData = g('live');
  const challengeData = g('challenge_live');
  const cmData = g('cm');
  const schedulerData = g('scheduler');

  return (
    <div css={pageStyle}>
      <div css={actionsStyle}>
        <Button variant="primary" onClick={handleSave} disabled={saveConfig.isPending}>
          {saveConfig.isPending ? '保存中…' : '保存'}
        </Button>
        <Button variant="default" onClick={handleReset}>
          重置
        </Button>
      </div>

      {/* Game settings */}
      <GroupBox title="游戏设置">
        <FormRow label="模拟器类型">
          <Select
            value={gameData.emulator}
            onChange={e => setGame('emulator', e.target.value)}
          >
            {Object.entries(EMULATOR_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </Select>
        </FormRow>

        {gameData.emulator === 'custom' && (
          <>
            <FormRow label="ADB IP">
              <Input
                value={gameData.emulator_data?.adb_ip ?? '127.0.0.1'}
                onChange={e => setGame('emulator_data', {
                  ...gameData.emulator_data,
                  adb_ip: e.target.value,
                })}
              />
            </FormRow>
            <FormRow label="ADB 端口">
              <Input
                type="number"
                value={gameData.emulator_data?.adb_port ?? 5555}
                onChange={e => setGame('emulator_data', {
                  ...gameData.emulator_data,
                  adb_port: Number(e.target.value),
                })}
              />
            </FormRow>
            <FormRow label="模拟器路径">
              <Input
                value={gameData.emulator_data?.emulator_path ?? ''}
                onChange={e => setGame('emulator_data', {
                  ...gameData.emulator_data,
                  emulator_path: e.target.value,
                })}
              />
            </FormRow>
            <FormRow label="启动参数">
              <Input
                value={gameData.emulator_data?.emulator_args ?? ''}
                onChange={e => setGame('emulator_data', {
                  ...gameData.emulator_data,
                  emulator_args: e.target.value,
                })}
              />
            </FormRow>
          </>
        )}

        <FormRow label="服务器">
          <Select
            value={gameData.server}
            onChange={e => {
              const val = e.target.value as 'jp' | 'tw';
              setGame('server', val);
              if (val === 'tw') setGame('link_account', 'no');
            }}
          >
            {Object.entries(SERVER_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </Select>
        </FormRow>

        <FormRow label="引继账号">
          <Select
            value={gameData.link_account}
            disabled={gameData.server === 'tw'}
            onChange={e => setGame('link_account', e.target.value)}
          >
            {Object.entries(LINK_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </Select>
        </FormRow>

        <FormRow label="控制方式">
          <Select
            value={gameData.control_impl}
            onChange={e => setGame('control_impl', e.target.value)}
          >
            {Object.entries(CONTROL_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </Select>
        </FormRow>

        <FormRow label="">
          <Checkbox
            label="检查并启动模拟器"
            checked={gameData.check_emulator}
            onChange={e => setGame('check_emulator', e.target.checked)}
          />
        </FormRow>
      </GroupBox>

      {/* Scheduler (task enables) */}
      <GroupBox title="任务启用">
        {(
          [
            ['start_game_enabled', '启动游戏'],
            ['solo_live_enabled', '单人演出'],
            ['challenge_live_enabled', '挑战演出'],
            ['activity_story_enabled', '活动剧情'],
            ['cm_enabled', '自动 CM'],
            ['gift_enabled', '领取礼物'],
            ['area_convos_enabled', '区域对话'],
          ] as [keyof typeof schedulerData, string][]
        ).map(([field, label]) => (
          <FormRow key={field} label="">
            <Checkbox
              label={label}
              checked={!!schedulerData[field]}
              onChange={e => setScheduler(field, e.target.checked)}
            />
          </FormRow>
        ))}
      </GroupBox>

      {/* Live settings */}
      <GroupBox title="演出设置">
        <FormRow label="歌曲">
          <Select
            value={liveData.song_id}
            disabled
            onChange={e => setLive('song_id', Number(e.target.value))}
          >
            <option value={-1}>保持不变</option>
            <option value={1}>Tell Your World</option>
            <option value={47}>メルト｜Melt</option>
            <option value={74}>独りんぼエンヴィー</option>
          </Select>
        </FormRow>
        <FormRow label="">
          <Checkbox
            label="完全清空体力"
            checked={liveData.fully_deplete}
            onChange={e => setLive('fully_deplete', e.target.checked)}
          />
        </FormRow>
      </GroupBox>

      {/* Challenge live settings */}
      <GroupBox title="挑战演出设置">
        <FormRow label="角色">
          <CharSelect
            value={challengeData.characters}
            onChange={v => setChallenge('characters', v)}
          />
        </FormRow>
        <FormRow label="奖励">
          <Select
            value={challengeData.award}
            onChange={e => setChallenge('award', e.target.value as ChallengeLiveAward)}
          >
            {Object.entries(AWARD_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </Select>
        </FormRow>
      </GroupBox>

      {/* CM settings */}
      <GroupBox title="CM 设置">
        <FormRow label="广告等待秒数">
          <Input
            type="number"
            min={1}
            value={cmData.watch_ad_wait_sec}
            onChange={e => setCm('watch_ad_wait_sec', Number(e.target.value))}
          />
        </FormRow>
      </GroupBox>
    </div>
  );
}
