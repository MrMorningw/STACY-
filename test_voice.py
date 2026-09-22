import unittest

from voice import EstadoVoz, VoiceController


class FakeRecognizer:
    def __init__(self, texto):
        self.texto = texto

    def ouvir(self):
        return self.texto


class FakeSynthesizer:
    def __init__(self):
        self.falas = []

    def falar(self, texto):
        self.falas.append(texto)


class VoiceControllerTests(unittest.TestCase):
    def test_voice_pipeline_uses_same_core_processor(self):
        chamadas = []

        def processar(texto):
            chamadas.append(texto)
            return {"tipo": "local", "resposta": "Olá, senhor."}

        sintetizador = FakeSynthesizer()
        controlador = VoiceController(
            processar_mensagem=processar,
            reconhecedor=FakeRecognizer("oi stacy"),
            sintetizador=sintetizador,
        )

        resultado = controlador.executar_uma_interacao()

        self.assertEqual(chamadas, ["oi stacy"])
        self.assertEqual(sintetizador.falas, ["Olá, senhor."])
        self.assertEqual(resultado.estado, EstadoVoz.OCIOSO)
        self.assertEqual(resultado.texto_entrada, "oi stacy")
        self.assertEqual(resultado.resposta, "Olá, senhor.")

    def test_empty_transcription_does_not_call_core_or_tts(self):
        chamadas = []

        def processar(texto):
            chamadas.append(texto)
            return {"resposta": "não deveria ocorrer"}

        sintetizador = FakeSynthesizer()
        controlador = VoiceController(
            processar_mensagem=processar,
            reconhecedor=FakeRecognizer("   "),
            sintetizador=sintetizador,
        )

        resultado = controlador.executar_uma_interacao()

        self.assertEqual(chamadas, [])
        self.assertEqual(sintetizador.falas, [])
        self.assertEqual(resultado.estado, EstadoVoz.OCIOSO)

    def test_core_without_text_response_does_not_speak(self):
        sintetizador = FakeSynthesizer()
        controlador = VoiceController(
            processar_mensagem=lambda texto: {"tipo": "acao"},
            reconhecedor=FakeRecognizer("crie uma tarefa"),
            sintetizador=sintetizador,
        )

        resultado = controlador.executar_uma_interacao()

        self.assertEqual(sintetizador.falas, [])
        self.assertEqual(resultado.estado, EstadoVoz.OCIOSO)

    def test_core_failure_is_reported_as_voice_error(self):
        sintetizador = FakeSynthesizer()

        def processar(_texto):
            raise RuntimeError("falha no core")

        controlador = VoiceController(
            processar_mensagem=processar,
            reconhecedor=FakeRecognizer("oi"),
            sintetizador=sintetizador,
        )

        resultado = controlador.executar_uma_interacao()

        self.assertEqual(resultado.estado, EstadoVoz.ERRO)
        self.assertEqual(resultado.erro, "falha no core")
        self.assertEqual(sintetizador.falas, [])


if __name__ == "__main__":
    unittest.main()
