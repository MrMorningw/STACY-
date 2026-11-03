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

    def test_request_does_not_guess_research_or_execution_from_message_text(self):
        start = self.html.index("function startStacyProcessingStages")
        end = self.html.index("window.stacyChatSetPending", start)
        lifecycle = self.html[start:end]

        self.assertIn('window.stacyNativeState&&window.stacyNativeState("pensando")', lifecycle)
        self.assertNotIn("likelyQuestion", lifecycle)
        self.assertIn("setTimeout", lifecycle)
        self.assertIn('window.stacyNativeState&&window.stacyNativeState("executando")', lifecycle)
        self.assertNotIn('"pesquisando"', lifecycle)

    def test_progress_reaching_one_hundred_does_not_finish_the_core_request(self):
        start = self.html.index("function animate(now)")
        end = self.html.index("window.stacySetAnimationsEnabled", start)
        animation_loop = self.html[start:end]

        self.assertIn("researchProgress=Math.min(100,(phaseClock/8)*100)", animation_loop)
        self.assertNotIn("setState('respondendo')", animation_loop)

    def test_all_live_orb_states_have_visible_particles(self):
        self.assertIn(
            "const desiredParticles={online:0,ouvindo:1,pensando:2,pesquisando:1,executando:1,respondendo:2,offline:0};",
            self.html,
        )
        self.assertIn('respondendo:{label:"RESPONDENDO",energy:1.12,rot:1.02,pulse:.82,glow:1.00', self.html)

    def test_final_core_result_transitions_to_response_unless_error(self):
        start = self.html.index("window.stacyNativeResponse=function")
        end = self.html.index("function nativeSend", start)
        response_handler = self.html[start:end]

        self.assertIn("const mapped=isError?'erro':'respondendo'", response_handler)

    def test_settings_markup_has_independent_ai_and_core_rows(self):
        start = self.html.index("config:{title:'Configurações'")
        end = self.html.index("nucleo:{title:'Núcleo STACY'", start)
        settings = self.html[start:end]
        self.assertIn('data-stacy-action="configurarIA"', settings)
        self.assertIn('data-stacy-action="nucleo"', settings)
        self.assertNotIn('<div class="stacy-setting-row"><div><div class="stacy-setting-row">', settings)

    def test_settings_controls_are_centered_and_consistently_sized(self):
        self.assertIn("flex-direction:column;align-items:center;justify-content:center", self.html)
        self.assertIn("width:min(100%,220px);min-width:0;min-height:42px", self.html)

    def test_fast_success_waits_for_minimum_processing_animation(self):
        start = self.html.index("window.stacyNativeResponse=function")
        end = self.html.index("function nativeSend", start)
        handler = self.html[start:end]
        self.assertIn("minimumProcessingMs=1350", handler)
        self.assertIn("stacyResponseDeferred=true", handler)
        self.assertIn("stacyPhaseTimers.push(setTimeout(finishResponse,delay))", handler)

    def test_real_research_state_prevents_execution_transition(self):
        start = self.html.index("function startStacyProcessingStages")
        end = self.html.index("window.stacyChatSetPending", start)
        lifecycle = self.html[start:end]
        self.assertIn('stacyCurrentPhase!=="pensando"', lifecycle)
        self.assertIn("stacyCurrentPhase=\"pensando\"", lifecycle)


if __name__ == "__main__":
    unittest.main()
