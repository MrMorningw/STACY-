import unittest

from android_tools import detectar_acao_android


class AndroidActionParserTests(unittest.TestCase):
    def test_open_settings_is_explicit(self):
        self.assertEqual(
            detectar_acao_android("Abra as configurações do Android!"),
            {"acao": "abrir_configuracoes"},
        )

    def test_allowlisted_app_is_mapped_to_known_package(self):
        self.assertEqual(
            detectar_acao_android("Por favor, abra o WhatsApp"),
            {
                "acao": "abrir_aplicativo",
                "nome": "WhatsApp",
                "pacote": "com.whatsapp",
            },
        )

    def test_calendar_command_is_typed(self):
        self.assertEqual(
            detectar_acao_android("abrir minha agenda"),
            {"acao": "abrir_calendario"},
        )

    def test_share_requires_explicit_colon_and_keeps_text(self):
        self.assertEqual(
            detectar_acao_android("Compartilhe: Olá, tudo bem?"),
            {"acao": "compartilhar_texto", "texto": "olá, tudo bem"},
        )
        self.assertIsNone(detectar_acao_android("Quais aplicativos posso compartilhar?"))

    def test_unknown_apps_and_ambiguous_phrases_are_not_executed(self):
        self.assertIsNone(detectar_acao_android("abra o aplicativo que você achar melhor"))
        self.assertIsNone(detectar_acao_android("como eu abro o WhatsApp?"))
        self.assertIsNone(detectar_acao_android("execute um comando no terminal"))


if __name__ == "__main__":
    unittest.main()
