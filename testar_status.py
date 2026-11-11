import unittest

from regras_status import (
    STATUS_1,
    STATUS_2,
    STATUS_3,
    STATUS_4,
    STATUS_5,
    STATUS_6,
    STATUS_7,
    mudar_status,
)


class TestarTransicoes(unittest.TestCase):

    def test_tecnico_disponibiliza(self):
        resultado = mudar_status(
            STATUS_1, "disponibilizar", "tecnico"
        )
        self.assertEqual(resultado, STATUS_2)

    def test_adenilson_inicia_analise(self):
        resultado = mudar_status(
            STATUS_2, "iniciar_analise", "adenilson"
        )
        self.assertEqual(resultado, STATUS_3)

    def test_adenilson_solicita_correcao(self):
        resultado = mudar_status(
            STATUS_3, "solicitar_correcao", "adenilson"
        )
        self.assertEqual(resultado, STATUS_4)

    def test_tecnico_devolve_correcao(self):
        resultado = mudar_status(
            STATUS_4, "devolver_correcao", "tecnico"
        )
        self.assertEqual(resultado, STATUS_5)

    def test_adenilson_inicia_reanalise(self):
        resultado = mudar_status(
            STATUS_5, "iniciar_reanalise", "adenilson"
        )
        self.assertEqual(resultado, STATUS_6)

    def test_reanalise_pode_solicitar_nova_correcao(self):
        resultado = mudar_status(
            STATUS_6, "solicitar_correcao", "adenilson"
        )
        self.assertEqual(resultado, STATUS_4)

    def test_concluir_analise(self):
        resultado = mudar_status(
            STATUS_3, "concluir_avaliacao", "adenilson"
        )
        self.assertEqual(resultado, STATUS_7)

    def test_concluir_reanalise(self):
        resultado = mudar_status(
            STATUS_6, "concluir_avaliacao", "adenilson"
        )
        self.assertEqual(resultado, STATUS_7)

    def test_transicao_proibida(self):
        with self.assertRaises(ValueError):
            mudar_status(
                STATUS_7, "iniciar_analise", "adenilson"
            )


if __name__ == "__main__":
    unittest.main()