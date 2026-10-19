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
        cls.http = (ROOT / "android/app/src/main/java/com/mrmorning/stacy/StacyHttpCoreClient.kt").read_text(encoding="utf-8")
        cls.daemon = (ROOT / "android/termux_widget/stacy-core-daemon.sh").read_text(encoding="utf-8")
        cls.server = (ROOT / "core_server.py").read_text(encoding="utf-8")
        cls.gradle = (ROOT / "android/app/build.gradle.kts").read_text(encoding="utf-8")

    def test_message_has_a_complete_ui_to_core_and_back_path(self):
        self.assertIn('Android.stacySend(text)', self.html)
        self.assertIn('fun stacySend(message: String)', self.activity)
        self.assertIn('coreBridge.process(', self.activity)
        self.assertIn('httpCore.chat(', self.bridge)
        self.assertIn('CoreResultStore.publish(context, result)', self.bridge)
        self.assertIn('webResponse(formatResponseWithSources(result), result.tipo)', self.activity)
        self.assertIn('window.stacyNativeResponse=function(response,tipo)', self.html)

    def test_http_transport_waits_for_a_healthy_core_before_chat(self):
        self.assertIn('http://127.0.0.1:8765', self.http)
        self.assertIn('awaitCoreReady(CORE_READY_TIMEOUT_MS)', self.http)
        self.assertIn('request("GET", "/health"', self.http)
        self.assertIn('health.optString("service") == "stacy-core"', self.http)
        self.assertIn('JSONObject(text)', self.http)
        self.assertIn('val startupError = readiness.error', self.http)
        self.assertIn('health.optString("error", "").trim()', self.http)
        self.assertIn('O CORE da STACY iniciou, mas não ficou saudável:', self.http)

    def test_daemon_does_not_restart_a_healthy_core_for_the_same_app_version(self):
        self.assertIn('--app-version-code=', self.daemon)
        self.assertIn('.stacy-core-app-version', self.daemon)
        self.assertIn('HEALTH" = "ok"', self.daemon)
        self.assertIn('CORE já está saudável para o aplicativo código', self.daemon)
        self.assertIn('LOCK_VERSION="$(cat "$START_LOCK/version"', self.daemon)
        self.assertIn('core_health_error()', self.daemon)
        self.assertIn('READY=0', self.daemon)
        self.assertIn('if [ "$READY" != "1" ]', self.daemon)
        self.assertIn('rm -f "$VERSION_MARKER"', self.daemon)
        self.assertIn('for ((attempt=0; attempt<80; attempt++))', self.daemon)
        self.assertLess(self.daemon.index('if [ "$HEALTH" = "ok"'), self.daemon.index("pkill -f"))
        self.assertGreater(self.daemon.index('rm -rf "$START_LOCK"', self.daemon.index("core_server.py iniciado")), self.daemon.index("core_server.py iniciado"))

    def test_native_core_fast_path_does_not_require_termux(self):
        self.assertNotIn("init { httpCore.startDaemon() }", self.bridge)
        self.assertIn("private val nativeCore = StacyNativeCore()", self.bridge)
        self.assertIn("val nativeResult = nativeCore.process(normalized)", self.bridge)
        self.assertIn("CURRENT_APP_VERSION", self.http)
        self.assertIn("Fast no-op when the same app version already has a healthy CORE", self.http)
        self.assertLess(self.bridge.index("val nativeResult = nativeCore.process(normalized)"), self.bridge.index("startNext()"))
        self.assertIn("Termux para este teste: não utilizado", self.native)
        self.assertIn("IA generativa / Orchestrator Python: não testados", self.native)
        self.assertIn("if (normalized in GREETINGS)", self.native)

    def test_runtime_sync_includes_the_new_evolution_components_and_skills(self):
        for path in (
            "agent_modes.py", "skills_registry.py", "verification_gate.py", "core_phase_context.py", "requirements.txt",
            "skills/README.md", "skills/research/SKILL.md",
            "skills/verification/SKILL.md", "skills/memory/SKILL.md",
            "skills/android/SKILL.md", "skills/automation/SKILL.md",
            "skills/engineering/SKILL.md",
        ):
            self.assertIn(path, self.daemon)
        self.assertIn("import requests", self.daemon)
        self.assertIn("pkg install -y python-requests", self.daemon)
        self.assertIn("requirements.txt", self.daemon)

    def test_phase_events_are_correlated_to_the_request_thread(self):
        self.assertIn("CorePhaseContext", self.server)
        self.assertIn("current_execution_id()", self.server)
        self.assertIn("set_current_execution_id(execution_id)", self.server)
        self.assertIn("clear_current_execution_id()", self.server)
        self.assertNotIn('getattr(self, "execution_id", None)', self.server)
        self.assertIn("CorePhaseContext", (ROOT / "core_phase_context.py").read_text(encoding="utf-8"))

    def test_released_build_advances_version_so_installed_app_can_update(self):
        self.assertIn("versionCode = 24", self.gradle)
        self.assertIn('versionName = "0.3.3"', self.gradle)


if __name__ == "__main__":
    unittest.main()
