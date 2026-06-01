import 'package:flutter_test/flutter_test.dart';
import 'package:va_bus_mobile/app.dart';

void main() {
  testWidgets('App boots without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const VaBusApp());
    await tester.pump();
  });
}
