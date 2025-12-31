import 'package:flutter/material.dart';
import '../state/app_state.dart';
import 'tabs/control_tab.dart';
import 'tabs/config_tab.dart';
import 'tabs/about_tab.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.state});

  final AppState state;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  static const double _railBreakpoint = 900;
  int _selectedIndex = 0;

  static const List<_NavDestination> _navDestinations = [
    _NavDestination(label: '控制', icon: Icons.tune_outlined, selectedIcon: Icons.tune),
    _NavDestination(label: '配置', icon: Icons.settings_outlined, selectedIcon: Icons.settings),
    _NavDestination(label: '关于', icon: Icons.info_outline, selectedIcon: Icons.info),
  ];

  @override
  void initState() {
    super.initState();
    // Initial load
    widget.state.loadAll();
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final useRail = constraints.maxWidth >= _railBreakpoint;
        
        Widget body;
        if (useRail) {
          body = Row(
            children: [
              _buildNavigationRail(),
              const VerticalDivider(width: 1),
              Expanded(
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1200),
                    child: _buildCurrentPage(),
                  ),
                ),
              ),
            ],
          );
        } else {
          body = Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1200),
              child: _buildCurrentPage(),
            ),
          );
        }

        return Scaffold(
          body: SafeArea(child: body),
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
    );
  }

  Widget _buildCurrentPage() {
    // We wrap the page content in ListenableBuilder so it rebuilds when AppState changes
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, child) {
        if (widget.state.loading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (widget.state.error != null) {
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('加载失败：${widget.state.error}'),
                const SizedBox(height: 12),
                ElevatedButton.icon(
                  onPressed: widget.state.loadAll,
                  icon: const Icon(Icons.refresh),
                  label: const Text('重试'),
                )
              ],
            ),
          );
        }
        switch (_selectedIndex) {
          case 0:
            return ControlTab(state: widget.state);
          case 1:
            return ConfigTab(state: widget.state);
          case 2:
            return AboutTab(state: widget.state);
          default:
            return ControlTab(state: widget.state);
        }
      },
    );
  }

  Widget _buildNavigationRail() {
    return NavigationRail(
      selectedIndex: _selectedIndex,
      onDestinationSelected: (idx) => setState(() => _selectedIndex = idx),
      labelType: NavigationRailLabelType.all,
      minWidth: 96,
      destinations: _navDestinations
          .map(
            (dest) => NavigationRailDestination(
              icon: Icon(dest.icon, size: 32),
              selectedIcon: Icon(dest.selectedIcon, size: 32),
              label: Text(dest.label, style: const TextStyle(fontSize: 14)),
            ),
          )
          .toList(),
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
