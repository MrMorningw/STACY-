from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android" / "app" / "src" / "main"
JAVA = ANDROID / "java" / "com" / "mrmorning" / "stacy"


class TestAndroidCoreResponseContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ANDROID / "assets" / "stacy_prototipo36.html").read_text(encoding="utf-8")
        cls.gradle = (ROOT / "android" / "app" / "build.gradle.kts").read_text(encoding="utf-8")
        cls.bridge = (JAVA / "StacyCoreBridge.kt").read_text(encoding="utf-8")
        cls.activity = (JAVA / "MainActivity.kt").read_text(encoding="utf-8")
        cls.ai = (JAVA / "StacyAiClient.kt").read_text(encoding="utf-8")
        cls.secrets = (JAVA / "StacySecretStore.kt").read_text(encoding="utf-8")
        cls.manifest = (ANDROID / "AndroidManifest.xml").read_text(encoding="utf-8")
        cls.server = (ROOT / "core_server.py").read_text(encoding="utf-8")
        cls.phase_context = (ROOT / "core_phase_context.py").read_text(encoding="utf-8")

    def test_message_has_a_complete_ui_to_native_core_and_back_path(self):
        self.assertIn("function command(raw)", self.html)
        self.assertIn("Android.stacySend(t)", self.html)
        self.assertIn("window.stacyNativeResponse=text=>", self.html)
        self.assertIn("CoreResultStore", self.activity)
        self.assertIn("StacyAiClient", self.bridge)

    def test_android_chat_path_does_not_depend_on_termux_or_localhost_daemon(self):
        self.assertNotIn("StacyHttpCoreClient", self.bridge)
        self.assertNotIn("RUN_COMMAND", self.bridge)
        self.assertNotIn("localhost", self.bridge.lower())
        self.assertNotIn("com.termux.permission.RUN_COMMAND", self.manifest)
        self.assertNotIn('android:name="com.termux"', self.manifest)
        self.assertIn("StacyAiClient(context.applicationContext)", self.bridge)

    def test_api_key_is_keystore_encrypted_and_sent_over_https_header(self):
        self.assertIn('"AndroidKeyStore"', self.secrets)
        self.assertIn('"AES/GCM/NoPadding"', self.secrets)
        self.assertIn("GCMParameterSpec", self.secrets)
        self.assertIn('setRequestProperty("x-goog-api-key", apiKey)', self.ai)
        self.assertIn("https://generativelanguage.googleapis.com/", self.ai)
        self.assertNotIn("?key=", self.ai)
        self.assertIn("stacyConfigureAi", self.activity)

    def test_released_build_advances_version_so_installed_app_can_update(self):
        self.assertIn("versionCode = 26", self.gradle)
        self.assertIn('versionName = "0.3.5"', self.gradle)

    def test_python_legacy_diagnostics_remain_available_for_development(self):
        self.assertIn("CorePhaseContext", self.server)
        self.assertIn("current_execution_id()", self.server)
        self.assertIn("set_current_execution_id(execution_id)", self.server)
        self.assertIn("clear_current_execution_id()", self.server)
        self.assertIn("CorePhaseContext", self.phase_context)
        self.assertTrue((ROOT / "android" / "termux_widget" / "stacy-core-daemon.sh").exists())


if __name__ == "__main__":
    unittest.main()
