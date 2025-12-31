import 'package:flutter/material.dart';
import '../../state/app_state.dart';

class ControlTab extends StatelessWidget {
  const ControlTab({super.key, required this.state});

  final AppState state;

  void _showSnack(BuildContext context, String text, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(text),
        backgroundColor: isError ? Colors.red.shade600 : null,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final status = state.status;
    final running = status?['running'] == true;
    final isStarting = status?['is_starting'] == true;
    final isStopping = status?['is_stopping'] == true;
    final currentTask = status?['current_task_name'] ?? '-';
    final scheduler = status?['scheduler'] as Map<String, dynamic>? ?? {};

    return RefreshIndicator(
      onRefresh: () async {
        await state.refreshStatus();
      },
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    running ? '运行中' : '已停止',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      ElevatedButton.icon(
                        onPressed: isStarting
                            ? null
                            : (running
                                ? () async {
                                    try {
                                      await state.stopScheduler();
                                      if (context.mounted) _showSnack(context, '已请求停止');
                                    } catch (e) {
                                      if (context.mounted) _showSnack(context, '停止失败：$e', isError: true);
                                    }
                                  }
                                : () async {
                                    try {
                                      await state.startScheduler();
                                      if (context.mounted) _showSnack(context, '已启动调度');
                                    } catch (e) {
                                      if (context.mounted) _showSnack(context, '启动失败：$e', isError: true);
                                    }
                                  }),
                        icon: Icon(running ? Icons.stop : Icons.play_arrow),
                        label: Text(running ? '停止' : '启动'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: running ? Colors.red.shade500 : null,
                        ),
                      ),
                      Chip(
                        avatar: const Icon(Icons.timelapse, size: 16),
                        label: Text('当前任务：$currentTask'),
                      ),
                      if (isStarting) const Chip(label: Text('正在启动…')),
                      if (isStopping) const Chip(label: Text('正在停止…')),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('任务开关', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  ...[
                    ('start_game_enabled', '启动游戏'),
                    ('solo_live_enabled', '单人演出'),
                    ('challenge_live_enabled', '挑战演出'),
                    ('activity_story_enabled', '活动剧情'),
                    ('cm_enabled', '自动 CM'),
                  ].map(
                    (item) => SwitchListTile(
                      title: Text(item.$2),
                      value: scheduler[item.$1] == true,
                      onChanged: (v) async {
                        try {
                          await state.updateConfigPartial({
                            "scheduler": {item.$1: v}
                          });
                        } catch (e) {
                          if (context.mounted) _showSnack(context, '更新失败：$e', isError: true);
                        }
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('立即运行', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      _buildRunButton(context, 'start_game', '启动游戏', running, isStarting, isStopping),
                      _buildRunButton(context, 'solo_live', '单人演出', running, isStarting, isStopping),
                      _buildRunButton(context, 'challenge_live', '挑战演出', running, isStarting, isStopping),
                      _buildRunButton(context, 'activity_story', '活动剧情', running, isStarting, isStopping),
                      _buildRunButton(context, 'cm', '自动 CM', running, isStarting, isStopping),
                      FilledButton(
                        onPressed: running || isStarting || isStopping
                            ? null
                            : () async {
                                final ok = await showDialog<bool>(
                                  context: context,
                                  builder: (ctx) => AlertDialog(
                                    title: const Text('确认开始'),
                                    content: const Text('将循环 AUTO 歌单最多 10 次，是否继续？'),
                                    actions: [
                                      TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
                                      FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('开始')),
                                    ],
                                  ),
                                );
                                if (ok == true && context.mounted) {
                                  _runTask(context, 'ten_songs');
                                }
                              },
                        child: const Text('刷完成歌曲首数'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRunButton(BuildContext context, String taskId, String label, bool running, bool starting, bool stopping) {
    return FilledButton.tonal(
      onPressed: running || starting || stopping ? null : () => _runTask(context, taskId),
      child: Text(label),
    );
  }

  Future<void> _runTask(BuildContext context, String taskId) async {
    try {
      await state.runTask(taskId);
      if (context.mounted) _showSnack(context, '任务已启动');
    } catch (e) {
      if (context.mounted) _showSnack(context, '任务启动失败：$e', isError: true);
    }
  }
}
