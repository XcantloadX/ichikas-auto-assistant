import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../state/app_state.dart';

class AboutTab extends StatelessWidget {
  const AboutTab({super.key, required this.state});

  final AppState state;

  Future<void> _launch(BuildContext context, String url) async {
    final uri = Uri.parse(url);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('无法打开链接：$url'), backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final about = state.about;
    final version = about?['version'] ?? 'Unknown';
    final links = (about?['links'] as List<dynamic>? ?? []).cast<Map>();
    final logoUrl = about?['logo'] as String?;

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
                    onPressed: () => _launch(context, l['url'] as String),
                    child: Text(l['text'] as String),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}
