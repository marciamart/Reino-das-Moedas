import math
import numpy as np

from .indexed_mesh import MalhaIndexada


class MalhaEsfera(MalhaIndexada):
    """Gera uma esfera por setores/pilhas, retornando vértices com normais."""
    def __init__(self, raio: float = 1.0, setores: int = 32, pilhas: int = 32):
        """
        Gera a malha de esfera.

        - raio: tamanho da esfera.
        - setores: subdivisões ao redor (longitude).
        - pilhas: subdivisões na vertical (latitude).
        """
        vertices = []
        indices = []

        for i in range(pilhas + 1):
            angulo_pilha = math.pi / 2 - i * math.pi / pilhas
            xy = raio * math.cos(angulo_pilha)
            z = raio * math.sin(angulo_pilha)

            for j in range(setores + 1):
                angulo_setor = j * 2 * math.pi / setores
                x = xy * math.cos(angulo_setor)
                y = xy * math.sin(angulo_setor)
                vertices.extend([x, z, y, x / raio, z / raio, y / raio])

        for i in range(pilhas):
            k1 = i * (setores + 1)
            k2 = k1 + setores + 1

            for _ in range(setores):
                if i != 0:
                    indices.extend([k1, k2, k1 + 1])

                if i != pilhas - 1:
                    indices.extend([k1 + 1, k2, k2 + 1])

                k1 += 1
                k2 += 1

        super().__init__(
            vertices=np.array(vertices, dtype=np.float32),
            indices=np.array(indices, dtype=np.uint32),
            passo_floats=6,
        )
