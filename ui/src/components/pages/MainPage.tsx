/** Control / main page */
import { css } from '@emotion/react';
import { useStatusStore } from '@/stores/useStatusStore';
import {
  useStartTasks,
  useStopTasks,
  useRunSingleTask,
  useTaskRegistry,
  useExportReport,
} from '@/hooks/useRpc';
import { useAppStore } from '@/stores/useAppStore';
import { Button } from '@/components/ui/Button';
import { GroupBox } from '@/components/ui/GroupBox';
import { ProgressBar } from '@/components/ui/ProgressBar';

const pageStyle = css`
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const powerRowStyle = css`
  display: flex;
  align-items: center;
  gap: 10px;
`;

const statusTextStyle = css`
  font-size: 13px;
  color: rgba(0,0,0,0.55);
`;

const taskGridStyle = css`
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
`;

const taskItemStyle = css`
  display: flex;
  align-items: center;
  gap: 6px;
`;

const taskNameStyle = css`
  font-size: 13px;
  color: rgba(0,0,0,0.75);
  min-width: 80px;
`;

const progressListStyle = css`
  display: flex;
  flex-direction: column;
  gap: 10px;
`;

const progressItemStyle = css`
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const progressHeaderStyle = css`
  display: flex;
  justify-content: space-between;
  align-items: baseline;
`;

const progressTaskNameStyle = css`
  font-size: 12px;
  font-weight: 600;
  color: rgba(0,0,0,0.75);
`;

const progressMessageStyle = css`
  font-size: 12px;
  color: rgba(0,0,0,0.50);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 260px;
`;

const progressPercentStyle = css`
  font-size: 12px;
  color: rgba(0,0,0,0.45);
  flex-shrink: 0;
`;

const errorStyle = css`
  font-size: 12px;
  color: #FF3B30;
  background: rgba(255,59,48,0.08);
  border-radius: 6px;
  padding: 6px 10px;
`;

const emptyStyle = css`
  font-size: 13px;
  color: rgba(0,0,0,0.35);
  padding: 12px 0;
  text-align: center;
`;

export function MainPage() {
  const status = useStatusStore(s => s.status);
  const showToast = useAppStore(s => s.showToast);
  const taskRegistryQ = useTaskRegistry();
  const startTasks = useStartTasks();
  const stopTasks = useStopTasks();
  const runSingle = useRunSingleTask();
  const exportReport = useExportReport();

  const isRunning = status?.running ?? false;
  const isStarting = status?.is_starting ?? false;
  const isStopping = status?.is_stopping ?? false;
  const isTransition = isStarting || isStopping;

  const snapshots = Object.values(status?.progress_snapshot ?? {});
  const activeSnapshots = snapshots.filter(s => s.status === 'running');
  const recentSnapshots = snapshots.filter(s => s.status !== 'running').slice(-3);

  function handleToggle() {
    if (isRunning || isStarting) {
      stopTasks.mutate(undefined, {
        onError: (e) => showToast(String(e), 'error'),
      });
    } else {
      startTasks.mutate(undefined, {
        onError: (e) => showToast(String(e), 'error'),
      });
    }
  }

  function handleRunSingle(taskId: string) {
    runSingle.mutate(taskId, {
      onSuccess: () => showToast('已启动任务', 'success'),
      onError: (e) => showToast(String(e), 'error'),
    });
  }

  function handleExport() {
    exportReport.mutate(undefined, {
      onSuccess: (data) => showToast(`报告已生成：${(data as { path: string }).path}`, 'success'),
      onError: (e) => showToast(String(e), 'error'),
    });
  }

  const btnVariant = isStopping
    ? 'default'
    : isStarting
    ? 'default'
    : isRunning
    ? 'danger'
    : 'success';

  const btnLabel = isStopping
    ? '停止中…'
    : isStarting
    ? '启动中…'
    : isRunning
    ? '停止'
    : '启动';

  const statusText = isStopping
    ? '正在尝试停止…'
    : isStarting
    ? '初始化脚本中…'
    : isRunning
    ? `正在执行：${status?.current_task_name ?? ''}`
    : '就绪';

  return (
    <div css={pageStyle}>
      {/* Power group */}
      <GroupBox title="启停">
        <div css={powerRowStyle}>
          <Button
            variant={btnVariant}
            onClick={handleToggle}
            disabled={isTransition}
          >
            {btnLabel}
          </Button>
          <Button
            variant="default"
            onClick={handleExport}
            disabled={exportReport.isPending}
          >
            导出报告
          </Button>
          <span css={statusTextStyle}>{statusText}</span>
        </div>
        {isTransition && (
          <div style={{ marginTop: 10 }}>
            <ProgressBar value={null} />
          </div>
        )}
      </GroupBox>

      {/* Tasks group */}
      <GroupBox title="任务">
        {taskRegistryQ.data ? (
          <div css={taskGridStyle}>
            {/* Regular tasks */}
            {Object.entries(taskRegistryQ.data.regular_tasks).map(([id, name]) => (
              <div key={id} css={taskItemStyle}>
                <span css={taskNameStyle}>{name}</span>
                <Button
                  size="sm"
                  onClick={() => handleRunSingle(id)}
                  disabled={isRunning || isTransition || runSingle.isPending}
                  title={`单独运行：${name}`}
                >
                  ▶
                </Button>
              </div>
            ))}
            {/* Manual tasks */}
            {Object.entries(taskRegistryQ.data.manual_tasks).map(([id, name]) => (
              <div key={id} css={taskItemStyle}>
                <span css={taskNameStyle}>{name}</span>
                <Button
                  size="sm"
                  onClick={() => handleRunSingle(id)}
                  disabled={isRunning || isTransition || runSingle.isPending}
                  title={`运行手动任务：${name}`}
                >
                  ▶
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <span css={emptyStyle}>加载中…</span>
        )}
      </GroupBox>

      {/* Progress group */}
      <GroupBox title="进度">
        {activeSnapshots.length === 0 && recentSnapshots.length === 0 ? (
          <span css={emptyStyle}>暂无进度信息</span>
        ) : (
          <div css={progressListStyle}>
            {[...activeSnapshots, ...recentSnapshots].map(snap => (
              <div key={snap.task_id} css={progressItemStyle}>
                <div css={progressHeaderStyle}>
                  <span css={progressTaskNameStyle}>{snap.task_name}</span>
                  <span css={progressPercentStyle}>
                    {snap.percent !== null ? `${snap.percent}%` : ''}
                  </span>
                </div>
                <ProgressBar
                  value={snap.status === 'running' && snap.percent === null ? null : (snap.percent ?? 0)}
                  variant={
                    snap.status === 'failed' ? 'danger' : snap.status === 'finished' ? 'success' : 'default'
                  }
                />
                {snap.message && (
                  <span css={progressMessageStyle}>{snap.message}</span>
                )}
                {snap.error && (
                  <div css={errorStyle}>错误：{snap.error}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </GroupBox>
    </div>
  );
}
