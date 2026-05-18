import math
import numpy as np

from .indexed_mesh import IndexedMesh


class CurvedBarrierMesh(IndexedMesh):
    def __init__(
        self,
        width: float = 5.2,
        depth: float = 1.0,
        thickness: float = 0.35,
        height: float = 0.8,
        segments: int = 40,
    ):
        vertices = []
        indices = []

        for i in range(segments + 1):
            t = i / segments
            x = -width / 2 + t * width
            z = math.sin(t * math.pi) * depth

            dz_dt = math.cos(t * math.pi) * math.pi * depth
            dx_dt = width
            length = math.sqrt(dx_dt * dx_dt + dz_dt * dz_dt)
            nx = -dz_dt / length
            nz = dx_dt / length

            for side in (-1, 1):
                px = x + nx * thickness * side
                pz = z + nz * thickness * side
                vertices.extend([px, 0, pz, 0, 1, 0])
                vertices.extend([px, height, pz, 0, 1, 0])

        for i in range(segments):
            base = i * 4
            nxt = (i + 1) * 4
            indices.extend(
                [
                    base, nxt, base + 1,
                    base + 1, nxt, nxt + 1,
                    base + 2, base + 3, nxt + 2,
                    base + 3, nxt + 3, nxt + 2,
                    base + 1, nxt + 1, base + 3,
                    base + 3, nxt + 1, nxt + 3,
                    base, base + 2, nxt,
                    base + 2, nxt + 2, nxt,
                ]
            )

        super().__init__(
            vertices=np.array(vertices, dtype=np.float32),
            indices=np.array(indices, dtype=np.uint32),
            stride_floats=6,
        )
