from OpenGL.GL import *
import numpy as np
import ctypes


class MalhaIndexada:
    """Cria buffers e descreve atributos (posição e normal) para uma malha indexada."""
    def __init__(self, vertices: np.ndarray, indices: np.ndarray, passo_floats: int):
        """
        Monta a malha no OpenGL.

        - vertices: array float32 contendo (x,y,z,nx,ny,nz) repetido.
        - indices: array uint32 com os índices dos triângulos.
        - passo_floats: quantidade de floats por vértice (stride), normalmente 6.
        """
        self.quantidade_indices = int(indices.size)
        self.id_vao = glGenVertexArrays(1)
        self.id_vbo = glGenBuffers(1)
        self.id_ebo = glGenBuffers(1)

        glBindVertexArray(self.id_vao)

        glBindBuffer(GL_ARRAY_BUFFER, self.id_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.id_ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        # Descrição dos atributos:
        # location 0 -> posição (vec3)
        # location 1 -> normal (vec3)
        passo_bytes = int(passo_floats * 4)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, passo_bytes, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, passo_bytes, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)

        glBindVertexArray(0)

    def desenhar(self):
        """Envia a chamada de desenho para a GPU usando os índices da malha."""
        glBindVertexArray(self.id_vao)
        glDrawElements(GL_TRIANGLES, self.quantidade_indices, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
