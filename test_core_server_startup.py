import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

import core_server
import orchestrator


class CoreServerStartupSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), core_server.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_orchestrator_keeps_full_core_contract_without_ctac(self):
        required = {
            "processar",
            "_processar_interno",
            "_registrar_resultado_conversa",
            "_usar_ai",
        }
        self.assertTrue(required.issubset(set(dir(orchestrator.StacyOrchestrator))))
        self.assertIn("phase_callback", orchestrator.StacyOrchestrator.__init__.__code__.co_varnames)
        import inspect
        source = inspect.getsource(orchestrator)
        self.assertNotIn("import ctac", source.lower())
        self.assertNotIn("from ctac", source.lower())

    def test_health_endpoint_confirms_runtime_is_ready(self):
        with urlopen(f"{self.base_url}/health", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertTrue(payload.get("ok"), payload)
        self.assertEqual(payload.get("service"), "stacy-core")

    def test_chat_endpoint_returns_typed_nonempty_response(self):
        body = json.dumps({"message": "oi", "executionId": 12345}).encode("utf-8")
        request = Request(
            f"{self.base_url}/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertIsInstance(payload.get("tipo"), str)
        self.assertTrue(payload["tipo"])
        self.assertIsInstance(payload.get("resposta"), str)
        self.assertTrue(payload["resposta"].strip())


    def test_registry_reports_real_provider_configuration_without_secrets(self):
        from component_registry import snapshot, render_status

        data = snapshot()
        providers = data.get("aiProviders")
        self.assertIsInstance(providers, dict)
        self.assertIn(providers.get("selected_provider"), {"local", "gemini", "unavailable"})
        self.assertIsInstance(providers.get("generation_configured"), bool)
        self.assertIsInstance(providers.get("local_model_server"), str)
        self.assertIsInstance(providers.get("gemini_key_configured"), bool)
        self.assertEqual(providers.get("provider_validation"), "not_tested")
        self.assertIn("IA generativa:", render_status())
        self.assertNotIn("AIza", render_status())



if __name__ == "__main__":
    unittest.main()
