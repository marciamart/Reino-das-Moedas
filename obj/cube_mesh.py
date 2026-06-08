import numpy as np

from .indexed_mesh import MalhaIndexada


class MalhaCubo(MalhaIndexada):
    """Gera um cubo unitário centrado na origem, com normais para iluminação."""
    def __init__(self):
        """Monta os arrays de vértices/índices e envia para a MalhaIndexada."""
        vertices = [
            -1, -1, 1, 0, 0, 1, 1, -1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, -1, 1, 1, 0, 0, 1,
            -1, -1, -1, 0, 0, -1, 1, -1, -1, 0, 0, -1, 1, 1, -1, 0, 0, -1, -1, 1, -1, 0, 0, -1,
            -1, -1, -1, -1, 0, 0, -1, -1, 1, -1, 0, 0, -1, 1, 1, -1, 0, 0, -1, 1, -1, -1, 0, 0,
            1, -1, -1, 1, 0, 0, 1, -1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, -1, 1, 0, 0,
            -1, 1, -1, 0, 1, 0, -1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, -1, 0, 1, 0,
            -1, -1, -1, 0, -1, 0, -1, -1, 1, 0, -1, 0, 1, -1, 1, 0, -1, 0, 1, -1, -1, 0, -1, 0,
        ]
        indices = [
            0, 1, 2, 2, 3, 0,
            4, 5, 6, 6, 7, 4,
            8, 9, 10, 10, 11, 8,
            12, 13, 14, 14, 15, 12,
            16, 17, 18, 18, 19, 16,
            20, 21, 22, 22, 23, 20,
        ]

        super().__init__(
            vertices=np.array(vertices, dtype=np.float32),
            indices=np.array(indices, dtype=np.uint32),
            passo_floats=6,
        )
