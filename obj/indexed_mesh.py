from OpenGL.GL import *
import numpy as np
import ctypes


class IndexedMesh:
    def __init__(self, vertices: np.ndarray, indices: np.ndarray, stride_floats: int):
        self.index_count = int(indices.size)
        self.vao_id = glGenVertexArrays(1)
        self.vbo_id = glGenBuffers(1)
        self.ebo_id = glGenBuffers(1)

        glBindVertexArray(self.vao_id)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_id)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo_id)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        stride_bytes = int(stride_floats * 4)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride_bytes, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride_bytes, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)

        glBindVertexArray(0)

    def render(self):
        glBindVertexArray(self.vao_id)
        glDrawElements(GL_TRIANGLES, self.index_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
