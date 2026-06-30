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


def create_textured_quad(width, depth):
    # Quad plano no plano XZ, centrado na origem, com UV para mapear uma
    # textura (usado no piso do tabuleiro).
    hw = width / 2.0
    hd = depth / 2.0
    vertices = np.array([
        -hw, 0, -hd, 0, 1, 0, 0, 0,
         hw, 0, -hd, 0, 1, 0, 1, 0,
         hw, 0,  hd, 0, 1, 0, 1, 1,
        -hw, 0,  hd, 0, 1, 0, 0, 1,
    ], dtype=np.float32)

    indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)

    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    ebo = glGenBuffers(1)

    glBindVertexArray(vao)

    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    stride = 8 * 4

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
    glEnableVertexAttribArray(1)

    glVertexAttribPointer(3, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
    glEnableVertexAttribArray(3)

    glBindVertexArray(0)

    return vao, len(indices)


def create_mesh_from_npz(path):
    # Carrega um modelo pre-processado: posicao + normal + cor por vertice +
    # UV (usado por objetos com textura real, como a barreira). Cor e UV
    # convivem no mesmo arquivo; cada objeto usa um ou outro no shader.
    data = np.load(path)
    vertices = data["vertices"].astype(np.float32)
    indices = data["indices"].astype(np.uint32)

    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    ebo = glGenBuffers(1)

    glBindVertexArray(vao)

    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    stride = 11 * 4

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
    glEnableVertexAttribArray(1)

    glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
    glEnableVertexAttribArray(2)

    glVertexAttribPointer(3, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(36))
    glEnableVertexAttribArray(3)

    glBindVertexArray(0)

    return vao, len(indices)

