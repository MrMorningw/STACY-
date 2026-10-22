from pathlib import Path
import unittest


HTML_PATH = (
    Path(__file__).resolve().parents[1]
    / "android"
    / "app"
    / "src"
    / "main"
    / "assets"
    / "stacy_prototipo36.html"
)


class TestStacyAnimationLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML_PATH.read_text(encoding="utf-8")

    def test_local_nucleus_routes_unknown_text_to_android_core(self):
        self.assertIn("const KEY='stacy-core-v1'", self.html)
        self.assertIn("function command(raw)", self.html)
        self.assertIn("setPhase('PENSANDO');if(window.Android?.stacySend)", self.html)
        self.assertIn("Android.stacySend(t)", self.html)

    def test_native_phase_callback_is_authoritative(self):
        self.assertIn("window.stacyNativeState=x=>", self.html)
        for state in ("ONLINE", "OUVINDO", "PENSANDO", "PESQUISANDO", "EXECUTANDO", "RESPONDENDO", "ERRO", "OFFLINE"):
            self.assertIn(state, self.html)

    def test_all_live_orb_states_have_visible_particles_contract(self):
        self.assertIn("['PENSANDO','PESQUISANDO','EXECUTANDO']", self.html)
        self.assertIn("@keyframes pulse", self.html)
        self.assertIn("animation:spin", self.html)

    def test_final_core_result_transitions_to_response_unless_error(self):
        self.assertIn("window.stacyNativeResponse=text=>", self.html)
        self.assertIn("setPhase('RESPONDENDO')", self.html)
        self.assertIn("setPhase('ONLINE')", self.html)


if __name__ == "__main__":
    unittest.main()
