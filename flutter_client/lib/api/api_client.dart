import 'dart:convert';
import 'package:http/http.dart' as http;

const String kDefaultApiBase =
    String.fromEnvironment('IAA_API_BASE', defaultValue: 'http://localhost:5000/api');

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
