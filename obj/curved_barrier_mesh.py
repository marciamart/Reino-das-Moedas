import math
import numpy as np

from .indexed_mesh import MalhaIndexada


class MalhaBarreiraCurva(MalhaIndexada):
    """Gera uma barreira curva com espessura e altura, apropriada para o tabuleiro."""
    def __init__(
        self,
        largura: float = 5.2,
        profundidade: float = 1.0,
        espessura: float = 0.35,
        altura: float = 0.8,
        segmentos: int = 40,
    ):
        """
        Gera a barreira curva.

        A curva é um arco (seno) ao longo da largura, com espessura para formar um volume.
        """
        vertices = []
        indices = []

        for i in range(segmentos + 1):
            t = i / segmentos
            x = -largura / 2 + t * largura
            z = math.sin(t * math.pi) * profundidade

            dz_dt = math.cos(t * math.pi) * math.pi * profundidade
            dx_dt = largura
            comprimento = math.sqrt(dx_dt * dx_dt + dz_dt * dz_dt)
            nx = -dz_dt / comprimento
            nz = dx_dt / comprimento

            for lado in (-1, 1):
                px = x + nx * espessura * lado
                pz = z + nz * espessura * lado
                vertices.extend([px, 0, pz, 0, 1, 0])
                vertices.extend([px, altura, pz, 0, 1, 0])

        for i in range(segmentos):
            base = i * 4
            prox = (i + 1) * 4
            indices.extend(
                [
                    base, prox, base + 1,
                    base + 1, prox, prox + 1,
                    base + 2, base + 3, prox + 2,
                    base + 3, prox + 3, prox + 2,
                    base + 1, prox + 1, base + 3,
                    base + 3, prox + 1, prox + 3,
                    base, base + 2, prox,
                    base + 2, prox + 2, prox,
                ]
            )

        super().__init__(
            vertices=np.array(vertices, dtype=np.float32),
            indices=np.array(indices, dtype=np.uint32),
            passo_floats=6,
        )
