import math
import numpy as np

from .indexed_mesh import IndexedMesh


class SphereMesh(IndexedMesh):
    def __init__(self, radius: float = 1.0, sectors: int = 32, stacks: int = 32):
        vertices = []
        indices = []

        for i in range(stacks + 1):
            stack_angle = math.pi / 2 - i * math.pi / stacks
            xy = radius * math.cos(stack_angle)
            z = radius * math.sin(stack_angle)

            for j in range(sectors + 1):
                sector_angle = j * 2 * math.pi / sectors
                x = xy * math.cos(sector_angle)
                y = xy * math.sin(sector_angle)
                vertices.extend([x, z, y, x / radius, z / radius, y / radius])

        for i in range(stacks):
            k1 = i * (sectors + 1)
            k2 = k1 + sectors + 1

            for _ in range(sectors):
                if i != 0:
                    indices.extend([k1, k2, k1 + 1])

                if i != stacks - 1:
                    indices.extend([k1 + 1, k2, k2 + 1])

                k1 += 1
                k2 += 1

        super().__init__(
            vertices=np.array(vertices, dtype=np.float32),
            indices=np.array(indices, dtype=np.uint32),
            stride_floats=6,
        )
