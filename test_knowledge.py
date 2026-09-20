import unittest

import knowledge


class KnowledgeTests(unittest.TestCase):

    def test_venus_has_no_natural_satellites(self):
        self.assertEqual(
            knowledge.consultar("quantas luas tem venus?"),
            "Vênus não possui luas naturais conhecidas."
        )

    def test_common_typo_is_normalized(self):
        self.assertEqual(
            knowledge.consultar("wuantos dentes tem um ser humani adulto"),
            "Um adulto normalmente tem 32 dentes permanentes, incluindo os quatro sisos."
        )

    def test_sun_answer_is_qualified(self):
        resposta = knowledge.consultar("qual a cor do nosso sol?")
        self.assertIn("parece branco", resposta)
        self.assertIn("atmosfera", resposta)

    def test_ducks_answer_does_not_invent_one_lifespan(self):
        resposta = knowledge.consultar("quanto tempo os patos vivem?")
        self.assertIn("varia bastante", resposta)
        self.assertIn("não existe um único tempo de vida", resposta)


    def test_capital_and_accents_are_normalized(self):
        self.assertEqual(
            knowledge.consultar("qual é a capital do Brasil?"),
            "A capital do Brasil é Brasília."
        )

    def test_contextual_followup_requires_prior_clue(self):
        historico = [
            {"tipo": "usuario", "conteudo": "qual fruta é verde e começa com a?"}
        ]
        resposta = knowledge.consultar_contextual(
            "tem um caroço no meio",
            historico
        )
        self.assertIn("abacate", resposta.lower())

    def test_unknown_fact_is_not_guessed(self):
        self.assertIsNone(
            knowledge.consultar("qual é a temperatura média de Netuno?")
        )

    def test_avocado_clues(self):
        self.assertEqual(
            knowledge.consultar("qual fruta é verde e começa com a e tem um caroço no meio?"),
            "A fruta que corresponde a essas pistas é o abacate."
        )


if __name__ == "__main__":
    unittest.main()
