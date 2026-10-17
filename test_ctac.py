import inspect
import unittest

import orchestrator


class LegacyCtacDependencyTest(unittest.TestCase):
    def test_orchestrator_does_not_import_ctac(self):
        source = inspect.getsource(orchestrator)
        self.assertNotIn("import ctac", source.lower())
        self.assertNotIn("from ctac", source.lower())

    def test_orchestrator_retains_full_core_contract(self):
        required = {
            "processar",
            "_processar_interno",
            "_registrar_resultado_conversa",
            "_usar_ai",
        }
        self.assertTrue(required.issubset(set(dir(orchestrator.StacyOrchestrator))))


if __name__ == "__main__":
    unittest.main()
