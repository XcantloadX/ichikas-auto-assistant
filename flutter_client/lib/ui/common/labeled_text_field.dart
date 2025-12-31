import 'package:flutter/material.dart';

class LabeledTextField extends StatelessWidget {
  const LabeledTextField({
    super.key,
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
