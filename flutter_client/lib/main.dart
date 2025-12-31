import 'package:flutter/material.dart';
import 'state/app_state.dart';
import 'ui/home_page.dart';

void main() {
  runApp(const IaaFlutterApp());
}

class IaaFlutterApp extends StatefulWidget {
  const IaaFlutterApp({super.key});

  @override
  State<IaaFlutterApp> createState() => _IaaFlutterAppState();
}

class _IaaFlutterAppState extends State<IaaFlutterApp> {
  final AppState _appState = AppState();

  @override
  void dispose() {
    _appState.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(seedColor: Colors.teal);
    return MaterialApp(
      title: '一歌小助手',
      theme: ThemeData(colorScheme: colorScheme, useMaterial3: true),
      home: HomePage(state: _appState),
    );
  }
}
