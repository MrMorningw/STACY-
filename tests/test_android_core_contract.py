from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestAndroidCoreResponseContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "android/app/src/main/assets/stacy_prototipo36.html").read_text(encoding="utf-8")
        cls.activity = (ROOT / "android/app/src/main/java/com/mrmorning/stacy/MainActivity.kt").read_text(encoding="utf-8")
        cls.bridge = (ROOT / "android/app/src/main/java/com/mrmorning/stacy/StacyCoreBridge.kt").read_text(encoding="utf-8")
        cls.native = (ROOT / "android/app/src/main/java/com/mrmorning/stacy/StacyNativeCore.kt").read_text(encoding="utf-8")
        cls.store = (ROOT / "android/app/src/main/java/com/mrmorning/stacy/StacyLocalStore.kt").read_text(encoding="utf-8")
        cls.server = (ROOT / "core_server.py").read_text(encoding="utf-8")
        cls.gradle = (ROOT / "android/app/build.gradle.kts").read_text(encoding="utf-8")
        cls.manifest = (ROOT / "android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
        cls.ai = (ROOT / "android/app/src/main/java/com/mrmorning/stacy/StacyAiClient.kt").read_text(encoding="utf-8")

    def test_message_has_a_complete_ui_to_core_and_back_path(self):
        self.assertIn('Android.stacySend(text)', self.html)
        self.assertIn('fun stacySend(message: String)', self.activity)
        self.assertIn('coreBridge.process(', self.activity)
        self.assertIn('aiClient.chat(', self.bridge)
        self.assertIn('StacyAiClient', self.bridge)
        self.assertIn('CoreResultStore.publish(context, result)', self.bridge)
        self.assertIn('webResponse(formatResponseWithSources(result), result.tipo)', self.activity)
        self.assertIn('window.stacyNativeResponse=function(response,tipo)', self.html)

    def test_android_chat_path_uses_native_kotlin_and_https_not_a_local_daemon(self):
        self.assertIn('StacyAiClient(context.applicationContext)', self.bridge)
        self.assertNotIn('StacyHttpCoreClient', self.bridge)
        self.assertNotIn('RUN_COMMAND', self.bridge)
        self.assertNotIn('localhost', self.bridge.lower())
        self.assertNotIn('com.termux.permission.RUN_COMMAND', self.manifest)
        self.assertNotIn('android:name="com.termux"', self.manifest)
        self.assertIn('https://generativelanguage.googleapis.com/v1/interactions', self.ai)
        self.assertIn('previous_interaction_id', self.ai)
        self.assertIn('StacyLocalStore', self.bridge)
        self.assertGreater(len(self.html), 170_000, "Approved STACY UI must be preserved")
        self.assertIn('data-stacy-action="configurarIA"', self.html)
        self.assertIn('fun stacyConfigureAi()', self.activity)

    def test_core_panel_runs_layered_diagnostics_and_displays_real_build_info(self):
        self.assertIn('data-stacy-action="diagnosticoCore"', self.html)
        self.assertIn('data-stacy-action="diagnosticoPonte"', self.html)
        self.assertIn('data-stacy-action="buildInfo"', self.html)
        self.assertIn('fun stacyRunDiagnostics(requestId: String)', self.activity)
        self.assertIn('fun stacyPingBridge(requestId: String)', self.activity)
        self.assertIn('fun stacyGetBuildInfo(): String', self.activity)
        self.assertIn('coreBridge.runNativeDiagnostic()', self.activity)
        self.assertIn('coreBridge.checkLocalStorage()', self.activity)
        self.assertIn('fun healthCheck(): Boolean', self.store)
        self.assertIn('window.stacyDiagnosticUpdate=function(raw)', self.html)
        self.assertIn('window.stacyBridgePingResult=function(raw)', self.html)
        self.assertIn('75000', self.html)
        self.assertIn('"not_used"', self.activity)

    def test_no_termux_runtime_entrypoints_or_command_adapters_remain(self):
        runtime_files = (
            "stacy.py",
            "interface.py",
            "ai.py",
            "android/app/src/main/AndroidManifest.xml",
            "android/app/src/main/java/com/mrmorning/stacy/MainActivity.kt",
            "android/app/src/main/java/com/mrmorning/stacy/StacyCoreBridge.kt",
        )
        forbidden = (
            "termux-speech-to-text",
            "termux-tts-speak",
            "termux-notification",
            "com.termux.permission.RUN_COMMAND",
            "AndroidInterface",
        )
        for relative_path in runtime_files:
            text = (ROOT / relative_path).read_text(encoding="utf-8").lower()
            for token in forbidden:
                self.assertNotIn(token.lower(), text, f"{token} remains in {relative_path}")
        self.assertFalse((ROOT / "termux_repair.sh").exists())
        self.assertFalse((ROOT / "android/termux_widget").exists())

    def test_native_core_has_local_greetings_actions_tasks_and_memory(self):
        self.assertIn("private val nativeCore = StacyNativeCore(localStore)", self.bridge)
        self.assertIn("private val localStore = StacyLocalStore", self.bridge)
        self.assertIn("routeLocalData(message, normalized)", self.native)
        self.assertNotIn("$" + "{task.", self.native)
        self.assertNotIn("$" + "{completed.", self.native)
        self.assertNotIn("$" + "{index + 1}", self.native)
        self.assertIn("store.addTask", self.native)
        self.assertIn("store.saveMemory", self.native)
        self.assertIn("conclu[ií]da", self.native)
        self.assertIn("mem[oó]ria", self.native)
        self.assertIn("abrir_aplicativo", self.native)
        self.assertIn('"whatsapp" to ("com.whatsapp" to "WhatsApp")', self.native)
        self.assertIn('androidAction("compartilhar_texto", shareText = text)', self.native)
        self.assertIn('operation = "abrir_aplicativo"', self.native)
        self.assertIn("CREATE TABLE tasks", self.store)
        self.assertIn("CREATE TABLE memories", self.store)
        self.assertNotIn("StacyHttpCoreClient", self.bridge)

    def test_phase_events_are_correlated_to_the_request_thread(self):
        self.assertIn("CorePhaseContext", self.server)
        self.assertIn("current_execution_id()", self.server)
        self.assertIn("set_current_execution_id(execution_id)", self.server)
        self.assertIn("clear_current_execution_id()", self.server)
        self.assertNotIn('getattr(self, "execution_id", None)', self.server)
        self.assertIn("CorePhaseContext", (ROOT / "core_phase_context.py").read_text(encoding="utf-8"))

    def test_released_build_advances_version_so_installed_app_can_update(self):
        self.assertIn("versionCode = 28", self.gradle)
        self.assertIn('versionName = "0.3.7"', self.gradle)


if __name__ == "__main__":
    unittest.main()
