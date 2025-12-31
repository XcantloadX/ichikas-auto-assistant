import 'package:flutter/foundation.dart';
import '../api/api_client.dart';

class AppState extends ChangeNotifier {
  final ApiClient api;

  AppState({ApiClient? api}) : api = api ?? ApiClient();

  // Server Data
  Map<String, dynamic>? status;
  Map<String, dynamic>? config;
  Map<String, dynamic>? options;
  Map<String, dynamic>? about;

  bool loading = true;
  String? error;

  // Draft State (Mutable)
  String? emulator;
  String? server;
  String? linkAccount;
  String? controlImpl;
  String customIp = '127.0.0.1';
  String customPort = '5555';
  int? songId;
  bool fullyDeplete = false;
  String? challengeAward;
  String? challengeCharacter;

  Future<void> loadAll() async {
    loading = true;
    error = null;
    notifyListeners();

    try {
      final results = await Future.wait([
        api.fetchStatus(),
        api.fetchConfig(),
        api.fetchOptions(),
        api.fetchAbout(),
      ]);
      status = results[0];
      config = results[1];
      options = results[2];
      about = results[3];
      loading = false;
      syncDraftFromConfig();
    } catch (e) {
      error = e.toString();
      loading = false;
    }
    notifyListeners();
  }

  void syncDraftFromConfig() {
    if (config == null) return;
    final cfg = config!;
    final game = cfg['game'] as Map<String, dynamic>;
    final live = cfg['live'] as Map<String, dynamic>;
    final cl = cfg['challenge_live'] as Map<String, dynamic>;

    emulator = game['emulator'] as String?;
    server = game['server'] as String?;
    linkAccount = game['link_account'] as String?;
    controlImpl = game['control_impl'] as String?;
    final emuData = game['emulator_data'] as Map<String, dynamic>?;
    customIp = emuData?['adb_ip']?.toString() ?? '127.0.0.1';
    customPort = (emuData?['adb_port'] ?? '5555').toString();

    songId = live['song_id'] as int?;
    fullyDeplete = (live['fully_deplete'] ?? false) as bool;

    final chars = (cl['characters'] as List<dynamic>? ?? []).cast<String>();
    challengeCharacter = chars.isNotEmpty ? chars.first : null;
    challengeAward = cl['award'] as String?;
    notifyListeners();
  }

  Future<void> refreshStatus() async {
    try {
      status = await api.fetchStatus();
      notifyListeners();
    } catch (e) {
      // Handle error silently or expose via a stream/callback if needed
      // For now we just print or ignore, or set a transient error
      debugPrint('Status refresh failed: $e');
    }
  }

  Future<void> updateConfigPartial(Map<String, dynamic> payload) async {
    try {
      config = await api.updateConfig(payload);
      syncDraftFromConfig();
      notifyListeners();
    } catch (e) {
      rethrow;
    }
  }

  Future<void> startScheduler() async {
    await api.startScheduler();
    await refreshStatus();
  }

  Future<void> stopScheduler() async {
    await api.stopScheduler();
    await refreshStatus();
  }

  Future<void> runTask(String taskId) async {
    await api.runTask(taskId);
    await refreshStatus();
  }

  Future<void> saveConfigDraft() async {
    final payload = {
      "game": {
        "emulator": emulator,
        "server": server,
        "link_account": linkAccount,
        "control_impl": controlImpl,
        "emulator_data": emulator == 'custom'
            ? {
                "adb_ip": customIp,
                "adb_port": int.tryParse(customPort) ?? 5555,
              }
            : null,
      },
      "live": {
        "song_id": songId,
        "fully_deplete": fullyDeplete,
      },
      "challenge_live": {
        "characters": challengeCharacter == null ? <String>[] : <String>[challengeCharacter!],
        "award": challengeAward,
      },
    };
    await updateConfigPartial(payload);
  }
  
  // Setters for draft state to notify listeners
  void setEmulator(String? v) { emulator = v; notifyListeners(); }
  void setCustomIp(String v) { customIp = v; notifyListeners(); }
  void setCustomPort(String v) { customPort = v; notifyListeners(); }
  void setServer(String? v) { server = v; notifyListeners(); }
  void setLinkAccount(String? v) { linkAccount = v; notifyListeners(); }
  void setControlImpl(String? v) { controlImpl = v; notifyListeners(); }
  void setSongId(int? v) { songId = v; notifyListeners(); }
  void setFullyDeplete(bool v) { fullyDeplete = v; notifyListeners(); }
  void setChallengeCharacter(String? v) { challengeCharacter = v; notifyListeners(); }
  void setChallengeAward(String? v) { challengeAward = v; notifyListeners(); }
}
