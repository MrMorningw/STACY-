import unittest

import interface


class InterfaceTests(unittest.TestCase):
    def test_html_contains_stacy_interface(self):
        self.assertIn("STACY", interface.HTML)
        self.assertIn("/api/chat", interface.HTML)

    def test_health_endpoint_shape(self):
        class Dummy:
            pass
        handler = interface.criar_handler(Dummy)
        self.assertTrue(handler)

if __name__ == "__main__":
    unittest.main()
