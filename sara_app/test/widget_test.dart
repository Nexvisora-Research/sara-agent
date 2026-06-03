import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sara_voice/features/chat/chat_screen.dart';
import 'package:sara_voice/main.dart';
import 'package:sara_voice/services/settings_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('App renders smoke test', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          settingsServiceProvider.overrideWith((ref) => SettingsService(prefs)),
        ],
        child: const SaraVoiceApp(),
      ),
    );

    expect(find.text('Sara Voice'), findsOneWidget);
  });
}
