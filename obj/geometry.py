import math

import numpy as np
from OpenGL.GL import *


def create_cube():
    vertices = [
        -1,-1, 1, 0,0,1,  1,-1, 1, 0,0,1,  1, 1, 1, 0,0,1, -1, 1, 1, 0,0,1,
        -1,-1,-1, 0,0,-1, 1,-1,-1, 0,0,-1, 1, 1,-1, 0,0,-1, -1, 1,-1, 0,0,-1,
        -1,-1,-1,-1,0,0, -1,-1, 1,-1,0,0, -1, 1, 1,-1,0,0, -1, 1,-1,-1,0,0,
         1,-1,-1,1,0,0,  1,-1, 1,1,0,0,  1, 1, 1,1,0,0,  1, 1,-1,1,0,0,
        -1, 1,-1,0,1,0, -1, 1, 1,0,1,0,  1, 1, 1,0,1,0,  1, 1,-1,0,1,0,
        -1,-1,-1,0,-1,0, -1,-1, 1,0,-1,0, 1,-1, 1,0,-1,0, 1,-1,-1,0,-1,0,
    ]

    indices = [
         0,1,2, 2,3,0,
         4,5,6, 6,7,4,
         8,9,10, 10,11,8,
         12,13,14, 14,15,12,
         16,17,18, 18,19,16,
         20,21,22, 22,23,20
    ]

    vertices = np.array(vertices, dtype=np.float32)
    indices = np.array(indices, dtype=np.uint32)

    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    ebo = glGenBuffers(1)

    glBindVertexArray(vao)

    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    stride = 6 * 4

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)

    return vao, len(indices)


def create_sphere(radius=1.0, sectors=32, stacks=32):
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

        for j in range(sectors):
            if i != 0:
                indices.extend([k1, k2, k1 + 1])

            if i != stacks - 1:
                indices.extend([k1 + 1, k2, k2 + 1])

            k1 += 1
            k2 += 1

    vertices = np.array(vertices, dtype=np.float32)
    indices = np.array(indices, dtype=np.uint32)

    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    ebo = glGenBuffers(1)

    glBindVertexArray(vao)

    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    stride = 6 * 4

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)

    return vao, len(indices)


def create_curved_barrier(width=5.2, depth=1.0, thickness=0.35, height=0.8, segments=40):
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

        for side in [-1, 1]:
            px = x + nx * thickness * side
            pz = z + nz * thickness * side

            vertices.extend([px, 0, pz, 0, 1, 0])
            vertices.extend([px, height, pz, 0, 1, 0])

    for i in range(segments):
        base = i * 4
        nxt = (i + 1) * 4

        indices.extend([
            base, nxt, base + 1,
            base + 1, nxt, nxt + 1,
            base + 2, base + 3, nxt + 2,
            base + 3, nxt + 3, nxt + 2,
            base + 1, nxt + 1, base + 3,
            base + 3, nxt + 1, nxt + 3,
            base, base + 2, nxt,
            base + 2, nxt + 2, nxt,
        ])

    vertices = np.array(vertices, dtype=np.float32)
    indices = np.array(indices, dtype=np.uint32)

    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    ebo = glGenBuffers(1)

    glBindVertexArray(vao)

    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    stride = 6 * 4

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)

    return vao, len(indices)

