import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

const String kDefaultApiBase =
    String.fromEnvironment('IAA_API_BASE', defaultValue: 'http://localhost:5000/api');

void main() {
  runApp(const IaaFlutterApp());
}

class ApiClient {
  ApiClient({String? baseUrl})
      : baseUrl = (baseUrl ?? kDefaultApiBase).replaceAll(RegExp(r'/$'), '');

  final String baseUrl;

  Future<Map<String, dynamic>> _decode(http.Response res) async {
    if (res.statusCode >= 400) {
      throw Exception('请求失败 (${res.statusCode}): ${res.body}');
    }
    if (res.body.isEmpty) return <String, dynamic>{};
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> fetchStatus() async {
    final res = await http.get(Uri.parse('$baseUrl/status'));
    return _decode(res);
  }

  Future<Map<String, dynamic>> fetchConfig() async {
    final res = await http.get(Uri.parse('$baseUrl/config'));
    return _decode(res);
  }

  Future<Map<String, dynamic>> fetchOptions() async {
    final res = await http.get(Uri.parse('$baseUrl/options'));
    return _decode(res);
  }

  Future<Map<String, dynamic>> fetchAbout() async {
    final res = await http.get(Uri.parse('$baseUrl/about'));
    return _decode(res);
  }

  Future<void> startScheduler() async {
    final res = await http.post(Uri.parse('$baseUrl/scheduler/start'));
    await _decode(res);
  }

  Future<void> stopScheduler() async {
    final res = await http.post(Uri.parse('$baseUrl/scheduler/stop'));
    await _decode(res);
  }

  Future<void> runTask(String taskId) async {
    final res = await http.post(Uri.parse('$baseUrl/tasks/$taskId/run'));
    await _decode(res);
  }

  Future<Map<String, dynamic>> updateConfig(Map<String, dynamic> payload) async {
    final res = await http.put(
      Uri.parse('$baseUrl/config'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    return _decode(res);
  }
}

class IaaFlutterApp extends StatefulWidget {
  const IaaFlutterApp({super.key});

  @override
  State<IaaFlutterApp> createState() => _IaaFlutterAppState();
}

class _IaaFlutterAppState extends State<IaaFlutterApp> {
  static const double _railBreakpoint = 900;

  static const List<_NavDestination> _navDestinations = [
    _NavDestination(label: '控制', icon: Icons.tune_outlined, selectedIcon: Icons.tune),
    _NavDestination(label: '配置', icon: Icons.settings_outlined, selectedIcon: Icons.settings),
    _NavDestination(label: '关于', icon: Icons.info_outline, selectedIcon: Icons.info),
  ];

  final ApiClient api = ApiClient();

  Map<String, dynamic>? _status;
  Map<String, dynamic>? _config;
  Map<String, dynamic>? _options;
  Map<String, dynamic>? _about;
  bool _loading = true;
  String? _error;
  int _selectedIndex = 0;

  // draft state
  String? _emulator;
  String? _server;
  String? _linkAccount;
  String? _controlImpl;
  String _customIp = '127.0.0.1';
  String _customPort = '5555';
  int? _songId;
  bool _fullyDeplete = false;
  String? _challengeAward;
  String? _challengeCharacter;

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        api.fetchStatus(),
        api.fetchConfig(),
        api.fetchOptions(),
        api.fetchAbout(),
      ]);
      setState(() {
        _status = results[0];
        _config = results[1];
        _options = results[2];
        _about = results[3];
        _loading = false;
      });
      _syncDraftFromConfig(results[1]);
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  void _syncDraftFromConfig(Map<String, dynamic> cfg) {
    final game = cfg['game'] as Map<String, dynamic>;
    final live = cfg['live'] as Map<String, dynamic>;
    final cl = cfg['challenge_live'] as Map<String, dynamic>;

    setState(() {
      _emulator = game['emulator'] as String?;
      _server = game['server'] as String?;
      _linkAccount = game['link_account'] as String?;
      _controlImpl = game['control_impl'] as String?;
      final emuData = game['emulator_data'] as Map<String, dynamic>?;
      _customIp = emuData?['adb_ip']?.toString() ?? '127.0.0.1';
      _customPort = (emuData?['adb_port'] ?? '5555').toString();

      _songId = live['song_id'] as int?;
      _fullyDeplete = (live['fully_deplete'] ?? false) as bool;

      final chars = (cl['characters'] as List<dynamic>? ?? []).cast<String>();
      _challengeCharacter = chars.isNotEmpty ? chars.first : null;
      _challengeAward = cl['award'] as String?;
    });
  }

  Future<void> _refreshStatus() async {
    try {
      final st = await api.fetchStatus();
      setState(() => _status = st);
    } catch (e) {
      _showSnack('状态刷新失败：$e', isError: true);
    }
  }

  Future<void> _updateConfigPartial(Map<String, dynamic> payload) async {
    try {
      final cfg = await api.updateConfig(payload);
      setState(() => _config = cfg);
      _syncDraftFromConfig(cfg);
    } catch (e) {
      _showSnack('配置更新失败：$e', isError: true);
    }
  }

  Future<void> _startScheduler() async {
    try {
      await api.startScheduler();
      await _refreshStatus();
      _showSnack('已启动调度');
    } catch (e) {
      _showSnack('启动失败：$e', isError: true);
    }
  }

  Future<void> _stopScheduler() async {
    try {
      await api.stopScheduler();
      await _refreshStatus();
      _showSnack('已请求停止');
    } catch (e) {
      _showSnack('停止失败：$e', isError: true);
    }
  }

  Future<void> _runTask(String taskId) async {
    try {
      await api.runTask(taskId);
      await _refreshStatus();
      _showSnack('任务已启动');
    } catch (e) {
      _showSnack('任务启动失败：$e', isError: true);
    }
  }

  void _showSnack(String text, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(text),
        backgroundColor: isError ? Colors.red.shade600 : null,
      ),
    );
  }

  Future<void> _saveConfigDraft() async {
    final payload = {
      "game": {
        "emulator": _emulator,
        "server": _server,
        "link_account": _linkAccount,
        "control_impl": _controlImpl,
        "emulator_data": _emulator == 'custom'
            ? {
                "adb_ip": _customIp,
                "adb_port": int.tryParse(_customPort) ?? 5555,
              }
            : null,
      },
      "live": {
        "song_id": _songId,
        "fully_deplete": _fullyDeplete,
      },
      "challenge_live": {
        "characters": _challengeCharacter == null ? <String>[] : <String>[_challengeCharacter!],
        "award": _challengeAward,
      },
    };
    await _updateConfigPartial(payload);
    _showSnack('配置已保存');
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(seedColor: Colors.teal);
    return MaterialApp(
      title: '一歌小助手',
      theme: ThemeData(colorScheme: colorScheme, useMaterial3: true),
      home: LayoutBuilder(
        builder: (context, constraints) {
          final useRail = constraints.maxWidth >= _railBreakpoint;
          final body = Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1200),
              child: useRail ? _buildNavigationRailLayout() : _buildCurrentPage(),
            ),
          );
          return Scaffold(
            appBar: AppBar(title: const Text('一歌小助手')),
            body: body,
            bottomNavigationBar: useRail
                ? null
                : NavigationBar(
                    selectedIndex: _selectedIndex,
                    onDestinationSelected: (idx) => setState(() => _selectedIndex = idx),
                    destinations: _navDestinations
                        .map(
                          (dest) => NavigationDestination(
                            icon: Icon(dest.icon),
                            selectedIcon: Icon(dest.selectedIcon),
                            label: dest.label,
                          ),
                        )
                        .toList(),
                  ),
          );
        },
      ),
    );
  }

  Widget _buildCurrentPage() {
    return _buildPageForIndex(_selectedIndex);
  }

  Widget _buildNavigationRailLayout() {
    return Row(
      children: [
        NavigationRail(
          selectedIndex: _selectedIndex,
          onDestinationSelected: (idx) => setState(() => _selectedIndex = idx),
          labelType: NavigationRailLabelType.selected,
          destinations: _navDestinations
              .map(
                (dest) => NavigationRailDestination(
                  icon: Icon(dest.icon),
                  selectedIcon: Icon(dest.selectedIcon),
                  label: Text(dest.label),
                ),
              )
              .toList(),
        ),
        const VerticalDivider(width: 1),
        Expanded(child: _buildCurrentPage()),
      ],
    );
  }

  Widget _buildPageForIndex(int index) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('加载失败：$_error'),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: _loadAll,
              icon: const Icon(Icons.refresh),
              label: const Text('重试'),
            )
          ],
        ),
      );
    }
    switch (index) {
      case 0:
        return _buildControlTab();
      case 1:
        return _buildConfigTab();
      case 2:
        return _buildAboutTab();
      default:
        return _buildControlTab();
    }
  }

  Widget _buildControlTab() {
    final running = _status?['running'] == true;
    final isStarting = _status?['is_starting'] == true;
    final isStopping = _status?['is_stopping'] == true;
    final currentTask = _status?['current_task_name'] ?? '-';
    final scheduler = _status?['scheduler'] as Map<String, dynamic>? ?? {};

    return RefreshIndicator(
      onRefresh: () async {
        await _refreshStatus();
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
                        onPressed: isStarting ? null : (running ? _stopScheduler : _startScheduler),
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
                      onChanged: (v) => _updateConfigPartial({
                        "scheduler": {item.$1: v}
                      }),
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
                      FilledButton.tonal(
                        onPressed: running || isStarting || isStopping ? null : () => _runTask('start_game'),
                        child: const Text('启动游戏'),
                      ),
                      FilledButton.tonal(
                        onPressed: running || isStarting || isStopping ? null : () => _runTask('solo_live'),
                        child: const Text('单人演出'),
                      ),
                      FilledButton.tonal(
                        onPressed: running || isStarting || isStopping ? null : () => _runTask('challenge_live'),
                        child: const Text('挑战演出'),
                      ),
                      FilledButton.tonal(
                        onPressed: running || isStarting || isStopping ? null : () => _runTask('activity_story'),
                        child: const Text('活动剧情'),
                      ),
                      FilledButton.tonal(
                        onPressed: running || isStarting || isStopping ? null : () => _runTask('cm'),
                        child: const Text('自动 CM'),
                      ),
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
                                if (ok == true) {
                                  _runTask('ten_songs');
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

  Widget _buildConfigTab() {
    final options = _options ?? {};
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
                _LabeledDropdown<String>(
                  label: '模拟器',
                  value: _emulator,
                  items: emulators
                      .map((e) => DropdownMenuItem<String>(
                            value: e['value'] as String,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _emulator = v),
                ),
                if (_emulator == 'custom') ...[
                  const SizedBox(height: 8),
                  _LabeledTextField(
                    label: 'ADB IP',
                    initialValue: _customIp,
                    onChanged: (v) => _customIp = v,
                  ),
                  const SizedBox(height: 8),
                  _LabeledTextField(
                    label: 'ADB 端口',
                    initialValue: _customPort,
                    keyboardType: TextInputType.number,
                    onChanged: (v) => _customPort = v,
                  ),
                ],
                const SizedBox(height: 8),
                _LabeledDropdown<String>(
                  label: '服务器',
                  value: _server,
                  items: servers
                      .map((e) => DropdownMenuItem<String>(
                            value: e['value'] as String,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _server = v),
                ),
                const SizedBox(height: 8),
                _LabeledDropdown<String>(
                  label: '引继账号',
                  value: _linkAccount,
                  items: linkAccounts
                      .map((e) => DropdownMenuItem<String>(
                            value: e['value'] as String,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _linkAccount = v),
                ),
                const SizedBox(height: 8),
                _LabeledDropdown<String>(
                  label: '控制方式',
                  value: _controlImpl,
                  items: controls
                      .map((e) => DropdownMenuItem<String>(
                            value: e['value'] as String,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _controlImpl = v),
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
                _LabeledDropdown<int>(
                  label: '歌曲',
                  value: _songId,
                  items: songOptions
                      .map((e) => DropdownMenuItem<int>(
                            value: e['value'] as int,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _songId = v),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('完全清空体力'),
                  value: _fullyDeplete,
                  onChanged: (v) => setState(() => _fullyDeplete = v),
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
                _LabeledDropdown<String>(
                  label: '角色',
                  value: _challengeCharacter,
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
                    }).toList(),
                  ],
                  onChanged: (v) {
                    setState(() => _challengeCharacter = (v == null || v.isEmpty) ? null : v);
                  },
                ),
                const SizedBox(height: 8),
                _LabeledDropdown<String>(
                  label: '奖励优先',
                  value: _challengeAward,
                  items: awards
                      .map((e) => DropdownMenuItem<String>(
                            value: e['value'] as String,
                            child: Text(e['label'] as String),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _challengeAward = v),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton.icon(
            onPressed: _saveConfigDraft,
            icon: const Icon(Icons.save),
            label: const Text('保存'),
          ),
        ),
        const SizedBox(height: 24),
      ],
    );
  }

  Widget _buildAboutTab() {
    final version = _about?['version'] ?? 'Unknown';
    final links = (_about?['links'] as List<dynamic>? ?? []).cast<Map>();
    final logoUrl = _about?['logo'] as String?;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          if (logoUrl != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Image.network(
                logoUrl,
                width: 180,
                height: 180,
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => const Icon(Icons.image_not_supported, size: 72),
              ),
            ),
          Text('一歌小助手', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          Text('版本 $version'),
          const SizedBox(height: 16),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 12,
            runSpacing: 8,
            children: links
                .map(
                  (l) => OutlinedButton(
                    onPressed: () => _launch(l['url'] as String),
                    child: Text(l['text'] as String),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }

  Future<void> _launch(String url) async {
    final uri = Uri.parse(url);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      _showSnack('无法打开链接：$url', isError: true);
    }
  }
}

class _LabeledDropdown<T> extends StatelessWidget {
  const _LabeledDropdown({
    required this.label,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final String label;
  final T? value;
  final List<DropdownMenuItem<T>> items;
  final ValueChanged<T?> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 4),
        DropdownButtonFormField<T>(
          value: value,
          items: items,
          onChanged: onChanged,
          isExpanded: true,
        ),
      ],
    );
  }
}

class _LabeledTextField extends StatelessWidget {
  const _LabeledTextField({
    required this.label,
    required this.initialValue,
    required this.onChanged,
    this.keyboardType,
  });

  final String label;
  final String initialValue;
  final ValueChanged<String> onChanged;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 4),
        TextFormField(
          key: ValueKey('$label-$initialValue'),
          initialValue: initialValue,
          onChanged: onChanged,
          keyboardType: keyboardType,
        ),
      ],
    );
  }
}

class _NavDestination {
  const _NavDestination({
    required this.label,
    required this.icon,
    required this.selectedIcon,
  });

  final String label;
  final IconData icon;
  final IconData selectedIcon;
}
