from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestAndroidCoreResponseContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "android" / "app" / "src" / "main" / "assets" / "stacy_prototipo36.html").read_text(encoding="utf-8")
        cls.gradle = (ROOT / "android" / "app" / "build.gradle.kts").read_text(encoding="utf-8")
        cls.server = (ROOT / "core_server.py").read_text(encoding="utf-8")
        cls.daemon = (ROOT / "android" / "termux_widget" / "stacy-core-daemon.sh").read_text(encoding="utf-8")

    def test_message_has_a_complete_ui_to_core_and_back_path(self):
        self.assertIn("function command(raw)", self.html)
        self.assertIn("Android.stacySend(t)", self.html)
        self.assertIn("window.stacyNativeResponse=text=>", self.html)
        self.assertIn("CoreResultStore", (ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "mrmorning" / "stacy" / "MainActivity.kt").read_text(encoding="utf-8"))

    def test_released_build_advances_version_so_installed_app_can_update(self):
        self.assertIn("versionCode = 25", self.gradle)
        self.assertIn('versionName = "0.3.4"', self.gradle)

    def test_phase_events_are_correlated_to_the_request_thread(self):
        self.assertIn("CorePhaseContext", self.server)
        self.assertIn("current_execution_id()", self.server)
        self.assertIn("set_current_execution_id(execution_id)", self.server)
        self.assertIn("clear_current_execution_id()", self.server)
        self.assertNotIn('getattr(self, "execution_id", None)', self.server)
        self.assertIn("CorePhaseContext", (ROOT / "core_phase_context.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
