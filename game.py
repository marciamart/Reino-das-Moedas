import math
import os

import glfw
from OpenGL.GL import *
import glm

from obj import CubeMesh, SphereMesh, CurvedBarrierMesh
from config import create_program_from_files


class TabuleiroGame:
    def __init__(self):
        self.resolution = [1280, 720]

        self.shader_id = 0
        self.locations = {}

        self.cube = None
        self.sphere = None
        self.barrier = None

        self.camera_distance = 45.0
        self.camera_angle = 0.0
        self.camera_forward_offset = 0.0

        self.board_half_width = 7.0
        self.board_bottom_length = 16.0
        self.board_top_length = 16.0

        self.blue_barrier_pos = glm.vec3(0, 0.05, 4.0)
        self.red_barrier_pos = glm.vec3(0, 0.05, -4.0)

        self.players = [
            {"pos": glm.vec3(-4, 0.5, 8), "color": (0.2, 0.5, 1.0)},
            {"pos": glm.vec3(4, 0.5, 8), "color": (0.2, 0.5, 1.0)},
            {"pos": glm.vec3(-4, 0.5, -8), "color": (1.0, 0.2, 0.2)},
            {"pos": glm.vec3(4, 0.5, -8), "color": (1.0, 0.2, 0.2)},
        ]

        self.blue_goal = glm.vec3(0, 0.05, 5.5)
        self.red_goal = glm.vec3(0, 0.05, -5.5)

        self.blue_bag_pos = glm.vec3(0, 0.4, 5.5)
        self.red_bag_pos = glm.vec3(0, 0.4, -5.5)

    def init_gl(self):
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.82, 0.86, 0.91, 1.0)

        here = os.path.dirname(os.path.abspath(__file__))
        shaders_dir = os.path.join(here, "shaders")

        self.shader_id = create_program_from_files(
            os.path.join(shaders_dir, "vertexShader.glsl"),
            os.path.join(shaders_dir, "fragmentShader.glsl"),
        )

        self.locations["projection"] = glGetUniformLocation(self.shader_id, "projection")
        self.locations["view"] = glGetUniformLocation(self.shader_id, "view")
        self.locations["model"] = glGetUniformLocation(self.shader_id, "model")
        self.locations["objectColor"] = glGetUniformLocation(self.shader_id, "objectColor")
        self.locations["lightColor"] = glGetUniformLocation(self.shader_id, "lightColor")
        self.locations["lightPos"] = glGetUniformLocation(self.shader_id, "lightPos")
        self.locations["viewPos"] = glGetUniformLocation(self.shader_id, "viewPos")

        self.cube = CubeMesh()
        self.sphere = SphereMesh()
        self.barrier = CurvedBarrierMesh()

    def update_framebuffer(self, window, width: int, height: int):
        self.resolution = [width, height]
        glViewport(0, 0, width, height)

    def update(self, window, delta_time: float):
        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            glfw.set_window_should_close(window, True)

    def _set_object_uniforms(self, model_matrix: glm.mat4, color):
        glUniformMatrix4fv(self.locations["model"], 1, GL_FALSE, glm.value_ptr(model_matrix))
        glUniform3f(self.locations["objectColor"], *color)

    def draw_cube(self, position: glm.vec3, scale: glm.vec3, color, rotation_y: float = 0.0):
        model = glm.mat4(1.0)
        model = glm.translate(model, position)
        model = glm.rotate(model, glm.radians(rotation_y), glm.vec3(0, 1, 0))
        model = glm.scale(model, scale)
        self._set_object_uniforms(model, color)
        self.cube.render()

    def draw_sphere(self, position: glm.vec3, scale: float, color):
        model = glm.mat4(1.0)
        model = glm.translate(model, position)
        model = glm.scale(model, glm.vec3(scale))
        self._set_object_uniforms(model, color)
        self.sphere.render()

    def draw_barrier(self, position: glm.vec3, color, rotation_y: float = 0.0):
        model = glm.mat4(1.0)
        model = glm.translate(model, position)
        model = glm.rotate(model, glm.radians(rotation_y), glm.vec3(0, 1, 0))
        self._set_object_uniforms(model, color)
        self.barrier.render()

    def render(self, window):
        width, height = glfw.get_framebuffer_size(window)
        if height == 0:
            return

        aspect = width / height

        forward_x = -math.sin(self.camera_angle)
        forward_z = -math.cos(self.camera_angle)
        camera_focus = glm.vec3(forward_x * self.camera_forward_offset, 0, forward_z * self.camera_forward_offset)
        camera_pos = camera_focus + glm.vec3(
            math.sin(self.camera_angle) * self.camera_distance,
            25,
            math.cos(self.camera_angle) * self.camera_distance,
        )

        view = glm.lookAt(camera_pos, camera_focus, glm.vec3(0, 1, 0))
        projection = glm.perspective(glm.radians(25), aspect, 0.1, 100.0)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.shader_id)

        glUniformMatrix4fv(self.locations["projection"], 1, GL_FALSE, glm.value_ptr(projection))
        glUniformMatrix4fv(self.locations["view"], 1, GL_FALSE, glm.value_ptr(view))
        glUniform3f(self.locations["lightColor"], 1, 1, 1)
        glUniform3f(self.locations["lightPos"], 0, 14, 0)
        glUniform3fv(self.locations["viewPos"], 1, glm.value_ptr(camera_pos))

        board_center_z = (self.board_bottom_length - self.board_top_length) / 2.0
        board_total_half = (self.board_bottom_length + self.board_top_length) / 2.0

        self.draw_cube(glm.vec3(0, -0.15, board_center_z), glm.vec3(self.board_half_width, 0.1, board_total_half), (0.88, 0.88, 0.90))

        border_color = (0.55, 0.55, 0.55)
        self.draw_cube(glm.vec3(0, 0.35, -self.board_top_length), glm.vec3(self.board_half_width + 0.2, 0.4, 0.2), border_color)
        self.draw_cube(glm.vec3(0, 0.35, self.board_bottom_length), glm.vec3(self.board_half_width + 0.2, 0.4, 0.2), border_color)
        self.draw_cube(glm.vec3(-self.board_half_width, 0.35, board_center_z), glm.vec3(0.2, 0.4, board_total_half), border_color)
        self.draw_cube(glm.vec3(self.board_half_width, 0.35, board_center_z), glm.vec3(0.2, 0.4, board_total_half), border_color)

        self.draw_barrier(self.blue_barrier_pos, (0.55, 0.55, 0.55), 180)
        self.draw_barrier(self.red_barrier_pos, (0.55, 0.55, 0.55), 0)

        self.draw_cube(self.blue_goal, glm.vec3(0.9, 0.05, 0.9), (0.2, 0.75, 1.0), 45)
        self.draw_cube(self.red_goal, glm.vec3(0.9, 0.05, 0.9), (1.0, 0.25, 0.25), 45)

        for player in self.players:
            self.draw_sphere(player["pos"], 0.6, player["color"])

        self.draw_cube(self.blue_bag_pos, glm.vec3(0.45, 0.45, 0.45), (1.0, 0.9, 0.15))
        self.draw_cube(self.red_bag_pos, glm.vec3(0.45, 0.45, 0.45), (1.0, 0.65, 0.05))

        glUseProgram(0)
