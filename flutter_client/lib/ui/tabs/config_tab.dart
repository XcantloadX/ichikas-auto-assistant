import 'package:flutter/material.dart';
import '../../state/app_state.dart';
import '../common/labeled_dropdown.dart';
import '../common/labeled_text_field.dart';

class ConfigTab extends StatelessWidget {
  const ConfigTab({super.key, required this.state});

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
    final options = state.options ?? {};
    final songOptions = (options['songs'] as List<dynamic>? ?? []).cast<Map>();
    final characters = (options['characters'] as List<dynamic>? ?? []).cast<Map>();
    final awards = (options['challenge_awards'] as List<dynamic>? ?? []).cast<Map>();
    final emulators = (options['emulators'] as List<dynamic>? ?? []).cast<Map>();
    final servers = (options['servers'] as List<dynamic>? ?? []).cast<Map>();
    final linkAccounts = (options['link_accounts'] as List<dynamic>? ?? []).cast<Map>();
    final controls = (options['control_impls'] as List<dynamic>? ?? []).cast<Map>();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('游戏设置', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                LabeledDropdown<String>(
                  label: '模拟器',
                  value: state.emulator,
                  items: emulators
                      .map((e) => DropdownMenuItem<String>(
                            value: e['value'] as String,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: state.setEmulator,
                ),
                if (state.emulator == 'custom') ...[
                  const SizedBox(height: 8),
                  LabeledTextField(
                    label: 'ADB IP',
                    initialValue: state.customIp,
                    onChanged: state.setCustomIp,
                  ),
                  const SizedBox(height: 8),
                  LabeledTextField(
                    label: 'ADB 端口',
                    initialValue: state.customPort,
                    keyboardType: TextInputType.number,
                    onChanged: state.setCustomPort,
                  ),
                ],
                const SizedBox(height: 8),
                LabeledDropdown<String>(
                  label: '服务器',
                  value: state.server,
                  items: servers
                      .map((e) => DropdownMenuItem<String>(
                            value: e['value'] as String,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: state.setServer,
                ),
                const SizedBox(height: 8),
                LabeledDropdown<String>(
                  label: '引继账号',
                  value: state.linkAccount,
                  items: linkAccounts
                      .map((e) => DropdownMenuItem<String>(
                            value: e['value'] as String,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: state.setLinkAccount,
                ),
                const SizedBox(height: 8),
                LabeledDropdown<String>(
                  label: '控制方式',
                  value: state.controlImpl,
                  items: controls
                      .map((e) => DropdownMenuItem<String>(
                            value: e['value'] as String,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: state.setControlImpl,
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
                Text('演出设置', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                LabeledDropdown<int>(
                  label: '歌曲',
                  value: state.songId,
                  items: songOptions
                      .map((e) => DropdownMenuItem<int>(
                            value: e['value'] as int,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: state.setSongId,
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('完全清空体力'),
                  value: state.fullyDeplete,
                  onChanged: state.setFullyDeplete,
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
                Text('挑战演出', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                LabeledDropdown<String>(
                  label: '角色',
                  value: state.challengeCharacter,
                  items: [
                    const DropdownMenuItem<String>(
                      value: '',
                      child: Text('未选择'),
                    ),
                    ...characters.expand((group) sync* {
                      final name = group['group'] as String? ?? '';
                      final items = (group['items'] as List<dynamic>? ?? []).cast<Map>();
                      for (final item in items) {
                        yield DropdownMenuItem<String>(
                          value: item['value'] as String,
                          child: Text('$name · ${item['label']}'),
                        );
                      }
                    }),
                  ],
                  onChanged: (v) {
                    state.setChallengeCharacter((v == null || v.isEmpty) ? null : v);
                  },
                ),
                const SizedBox(height: 8),
                LabeledDropdown<String>(
                  label: '奖励优先',
                  value: state.challengeAward,
                  items: awards
                      .map((e) => DropdownMenuItem<String>(
                            value: e['value'] as String,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: state.setChallengeAward,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton.icon(
            onPressed: () async {
              try {
                await state.saveConfigDraft();
                if (context.mounted) _showSnack(context, '配置已保存');
              } catch (e) {
                if (context.mounted) _showSnack(context, '保存失败：$e', isError: true);
              }
            },
            icon: const Icon(Icons.save),
            label: const Text('保存'),
          ),
        ),
        const SizedBox(height: 24),
      ],
    );
  }
}
