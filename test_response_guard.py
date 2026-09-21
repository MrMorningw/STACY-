import unittest

import response_guard


class ResponseGuardTests(unittest.TestCase):

    def test_valid_response_is_kept(self):
        self.assertEqual(
            response_guard.validar_resposta(" Tudo certo. ", "Como você está?"),
            "Tudo certo."
        )

    def test_empty_response_fails_closed(self):
        with self.assertRaises(response_guard.InvalidModelResponse):
            response_guard.validar_resposta("   ", "pergunta")

    def test_exact_query_echo_fails_closed(self):
        with self.assertRaises(response_guard.InvalidModelResponse):
            response_guard.validar_resposta("Qual é o nome da estátua?", "Qual é o nome da estátua?")

    def test_invalid_sources_are_removed(self):
        fontes = response_guard.validar_fontes([
            {"titulo": "A", "url": "https://example.com/a"},
            {"titulo": "duplicada", "url": "https://example.com/a"},
            {"titulo": "invalida", "url": "javascript:alert(1)"},
            {"titulo": "B", "url": "https://example.com/b"},
        ])
        self.assertEqual(len(fontes), 2)
        self.assertEqual(fontes[0]["url"], "https://example.com/a")
        self.assertEqual(fontes[1]["url"], "https://example.com/b")


if __name__ == "__main__":
    unittest.main()
