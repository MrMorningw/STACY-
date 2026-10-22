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
        cls.daemon = (ROOT / "android/termux_widget/stacy-core-daemon.sh").read_text(encoding="utf-8")
        cls.server = (ROOT / "core_server.py").read_text(encoding="utf-8")
        cls.gradle = (ROOT / "android/app/build.gradle.kts").read_text(encoding="utf-8")

    def test_message_has_a_complete_ui_to_core_and_back_path(self):
        self.assertIn('Android.stacySend(text)', self.html)
        self.assertIn('fun stacySend(message: String)', self.activity)
        self.assertIn('coreBridge.process(', self.activity)
        self.assertIn('aiClient.chat(', self.bridge)
        self.assertIn('StacyAiClient', self.bridge)
        self.assertIn('CoreResultStore.publish(context, result)', self.bridge)
        self.assertIn('webResponse(formatResponseWithSources(result), result.tipo)', self.activity)
        self.assertIn('window.stacyNativeResponse=function(response,tipo)', self.html)

    def test_android_chat_path_is_independent_of_termux_and_localhost(self):
        manifest = (ROOT / "android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
        ai = (ROOT / "android/app/src/main/java/com/mrmorning/stacy/StacyAiClient.kt").read_text(encoding="utf-8")
        self.assertIn('StacyAiClient(context.applicationContext)', self.bridge)
        self.assertNotIn('StacyHttpCoreClient', self.bridge)
        self.assertNotIn('RUN_COMMAND', self.bridge)
        self.assertNotIn('localhost', self.bridge.lower())
        self.assertNotIn('com.termux.permission.RUN_COMMAND', manifest)
        self.assertNotIn('android:name="com.termux"', manifest)
        self.assertIn('https://generativelanguage.googleapis.com/v1beta/interactions', ai)
        self.assertIn('previous_interaction_id', ai)
        self.assertIn('StacyLocalStore', self.bridge)
        self.assertGreater(len(self.html), 170_000, "Approved STACY UI must be preserved")
        self.assertIn('data-stacy-action="configurarIA"', self.html)
        self.assertIn('fun stacyConfigureAi()', self.activity)

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

    def test_native_core_has_local_greetings_actions_tasks_and_memory(self):
        self.assertIn("private val nativeCore = StacyNativeCore(localStore)", self.bridge)
        self.assertIn("private val localStore = StacyLocalStore", self.bridge)
        self.assertIn("routeLocalData(message, normalized)", self.native)
        self.assertNotIn(r"\${task.", self.native)
        self.assertNotIn(r"\${completed.", self.native)
        self.assertNotIn(r"\${index + 1}", self.native)
        self.assertIn("store.addTask", self.native)
        self.assertIn("store.saveMemory", self.native)
        self.assertIn("conclu[ií]da", self.native)
        self.assertIn("mem[oó]ria", self.native)
        self.assertIn("abrir_aplicativo", self.native)
        self.assertIn('"whatsapp" to ("com.whatsapp" to "WhatsApp")', self.native)
        self.assertIn('androidAction("compartilhar_texto", shareText = text)', self.native)
        self.assertIn('operation = "abrir_aplicativo"', self.native)
        local_store = (ROOT / "android/app/src/main/java/com/mrmorning/stacy/StacyLocalStore.kt").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE tasks", local_store)
        self.assertIn("CREATE TABLE memories", local_store)
        self.assertNotIn("StacyHttpCoreClient", self.bridge)

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
        self.assertIn("versionCode = 26", self.gradle)
        self.assertIn('versionName = "0.3.5"', self.gradle)


if __name__ == "__main__":
    unittest.main()
