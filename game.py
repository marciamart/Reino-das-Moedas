from pathlib import Path
import ctypes
import math
import random

import glfw
import glm
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from OpenGL.GL import *

from config import *
from obj.geometry import create_cube, create_mesh_from_npz, create_textured_quad


SHADER_DIR = Path(__file__).with_name("shaders")
ASSET_DIR = Path(__file__).with_name("assets")
MODEL_DIR = Path(__file__).with_name("obj") / "models"
CHARACTER_IMAGE_FILES = [
    "tigre.png",
    "dragao.png",
    "panda.png",
    "macaco.png",
]
CHARACTER_MODEL_FILES = [
    "tigre.npz",
    "dragao.npz",
    "panda.npz",
    "macaco.npz",
]


class Player:
    """Representa um personagem no tabuleiro: nome, posicao 3D, time,
    qual personagem foi escolhido e seus atributos (stats) de jogo."""

    def __init__(self, name, pos, team, personagem=None, stats=None):
        self.name = name
        self.pos = pos
        self.team = team
        self.personagem = personagem
        self.stats = stats

    def is_aliado(self, other):
        return self.team == other.team

    def __repr__(self):
        return f"Player(name={self.name!r}, team={self.team}, personagem={self.personagem})"


def load_shader_source(filename):
    return (SHADER_DIR / filename).read_text(encoding="utf-8")


VERTEX_SHADER = load_shader_source("vertex.glsl")
FRAGMENT_SHADER = load_shader_source("fragment.glsl")
BUTTON_VERTEX_SHADER = load_shader_source("button_vertex.glsl")
BUTTON_FRAGMENT_SHADER = load_shader_source("button_fragment.glsl")
TEXT_VERTEX_SHADER = load_shader_source("text_vertex.glsl")
TEXT_FRAGMENT_SHADER = load_shader_source("text_fragment.glsl")


def compile_shader(source, shader_type):
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)

    if not glGetShaderiv(shader, GL_COMPILE_STATUS):
        raise Exception(glGetShaderInfoLog(shader).decode())

    return shader


def create_shader_program(vertex_source, fragment_source):
    vertex = compile_shader(vertex_source, GL_VERTEX_SHADER)
    fragment = compile_shader(fragment_source, GL_FRAGMENT_SHADER)

    program = glCreateProgram()
    glAttachShader(program, vertex)
    glAttachShader(program, fragment)
    glLinkProgram(program)

    if not glGetProgramiv(program, GL_LINK_STATUS):
        raise Exception(glGetProgramInfoLog(program).decode())

    glDeleteShader(vertex)
    glDeleteShader(fragment)

    return program


def framebuffer_size_callback(window, width, height):
    glViewport(0, 0, width, height)


def to_ndc(x, y, window_width, window_height):
    return (x / window_width) * 2.0 - 1.0, 1.0 - (y / window_height) * 2.0


def create_button_renderer():
    program = create_shader_program(BUTTON_VERTEX_SHADER, BUTTON_FRAGMENT_SHADER)

    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)

    glBindVertexArray(vao)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, 6 * 5 * 4, None, GL_DYNAMIC_DRAW)

    stride = 5 * 4

    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(8))
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)

    return program, vao, vbo


class TextRenderer:
    # Renderiza texto como textura OpenGL, substituindo o antigo mapa manual de letras.
    def __init__(self):
        self.program = create_shader_program(TEXT_VERTEX_SHADER, TEXT_FRAGMENT_SHADER)
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.cache = {}

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, 6 * 4 * 4, None, GL_DYNAMIC_DRAW)
        stride = 4 * 4
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(8))
        glEnableVertexAttribArray(1)
        glBindVertexArray(0)

    def _font(self, pixel_size):
        for font_name in ("arial.ttf", "segoeui.ttf", "calibri.ttf"):
            try:
                return ImageFont.truetype(font_name, pixel_size)
            except OSError:
                pass
        return ImageFont.load_default()

    def _texture(self, text, scale, color):
        key = (text.upper(), scale, tuple(color))
        if key in self.cache:
            return self.cache[key]

        font_size = max(10, int(scale * 8))
        font = self._font(font_size)
        text = text.upper()
        bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=font)
        width = max(1, bbox[2] - bbox[0] + 4)
        height = max(1, bbox[3] - bbox[1] + 4)
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        rgba = tuple(int(max(0, min(1, value)) * 255) for value in color) + (255,)
        draw.text((2 - bbox[0], 2 - bbox[1]), text, font=font, fill=rgba)

        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image.tobytes())
        self.cache[key] = (texture, width, height)
        return self.cache[key]

    def measure(self, text, scale):
        _, width, _ = self._texture(text, scale, (1, 1, 1))
        return width

    def draw(self, text, x, y, scale, color, window_width, window_height):
        texture, width, height = self._texture(text, scale, color)
        left, top = to_ndc(x, y, window_width, window_height)
        right, bottom = to_ndc(x + width, y + height, window_width, window_height)
        vertices = np.array([
            left, bottom, 0.0, 1.0,
            right, bottom, 1.0, 1.0,
            right, top, 1.0, 0.0,
            left, bottom, 0.0, 1.0,
            right, top, 1.0, 0.0,
            left, top, 0.0, 0.0,
        ], dtype=np.float32)

        glUseProgram(self.program)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, texture)
        glUniform1i(glGetUniformLocation(self.program, "textTexture"), 0)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, 6)


def load_texture(path):
    image = Image.open(path).convert("RGBA").transpose(Image.FLIP_TOP_BOTTOM)
    width, height = image.size

    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image.tobytes())
    return texture


def load_floor_texture(path):
    image = Image.open(path).convert("RGB").transpose(Image.FLIP_TOP_BOTTOM)
    width, height = image.size

    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, image.tobytes())
    glGenerateMipmap(GL_TEXTURE_2D)

    # Filtro anisotropico: sem ele, o piso visto em angulo raso (como no
    # tabuleiro, visto de cima meio inclinado) gera linhas de serrilhado/moire.
    # Isso evita o problema sem precisar borrar a textura toda.
    try:
        GL_TEXTURE_MAX_ANISOTROPY_EXT = 0x84FE
        GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT = 0x84FF
        max_aniso = glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT)
        if max_aniso and max_aniso > 0:
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, max_aniso)
    except Exception:
        pass

    return texture


def load_character_textures():
    textures = []
    character_dir = ASSET_DIR / "personagens"
    for filename in CHARACTER_IMAGE_FILES:
        textures.append(load_texture(character_dir / filename))
    return textures


def load_character_models():
    models = []
    for filename in CHARACTER_MODEL_FILES:
        models.append(create_mesh_from_npz(MODEL_DIR / filename))
    return models


def draw_texture(texture, x, y, w, h, window_width, window_height):
    left, top = to_ndc(x, y, window_width, window_height)
    right, bottom = to_ndc(x + w, y + h, window_width, window_height)
    vertices = np.array([
        left, bottom, 0.0, 0.0,
        right, bottom, 1.0, 0.0,
        right, top, 1.0, 1.0,
        left, bottom, 0.0, 0.0,
        right, top, 1.0, 1.0,
        left, top, 0.0, 1.0,
    ], dtype=np.float32)

    glUseProgram(text_renderer.program)
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, texture)
    glUniform1i(glGetUniformLocation(text_renderer.program, "textTexture"), 0)
    glBindBuffer(GL_ARRAY_BUFFER, text_renderer.vbo)
    glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)
    glBindVertexArray(text_renderer.vao)
    glDrawArrays(GL_TRIANGLES, 0, 6)


def draw_character_portrait(character_index, x, y, w, h, window_width, window_height):
    if character_index is None or character_index < 0 or character_index >= len(character_textures):
        return
    draw_texture(character_textures[character_index], x, y, w, h, window_width, window_height)


def draw_cube(position, scale, color, rotation_y=0):
    model = glm.mat4(1.0)
    model = glm.translate(model, position)
    model = glm.rotate(model, glm.radians(rotation_y), glm.vec3(0, 1, 0))
    model = glm.scale(model, scale)

    glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
    glUniform1i(use_vertex_color_loc, 0)
    glUniform1i(use_texture_loc, 0)
    glUniform3f(object_color_loc, *color)

    glBindVertexArray(cube_vao)
    glDrawElements(GL_TRIANGLES, cube_count, GL_UNSIGNED_INT, None)


def draw_floor(position, width, depth):
    model = glm.mat4(1.0)
    model = glm.translate(model, position)
    model = glm.scale(model, glm.vec3(width, 1.0, depth))

    glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
    glUniform1i(use_vertex_color_loc, 0)
    glUniform1i(use_texture_loc, 1)

    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, floor_texture)

    glBindVertexArray(floor_vao)
    glDrawElements(GL_TRIANGLES, floor_count, GL_UNSIGNED_INT, None)


def get_oponente_pos(player_index):
    # Cada personagem enfrenta quem esta posicionado no espelho dele do
    # outro lado do tabuleiro (mesmo x, z oposto).
    own = players[player_index].pos
    nearest_index = None
    nearest_dx = None
    for index, other in enumerate(players):
        if index == player_index or players[index].team == players[player_index].team:
            continue
        dx = abs(other.pos.x - own.x)
        if nearest_dx is None or dx < nearest_dx:
            nearest_dx = dx
            nearest_index = index
    if nearest_index is None:
        return glm.vec3(own.x, own.y, -own.z)
    return players[nearest_index].pos


def draw_character_model(player_index, scale, current_frame):
    personagem_idx = players[player_index].personagem
    vao, count = character_models[personagem_idx]
    pos = players[player_index].pos
    alvo = get_oponente_pos(player_index)

    dx = alvo.x - pos.x
    dz = alvo.z - pos.z
    rotation_y = math.degrees(math.atan2(dx, dz)) if (dx or dz) else 0.0

    # pos.y e o "ancora" dos pes do personagem (ja embutido no modelo);
    # escalamos esse ancora junto para o personagem nao flutuar nem
    # afundar no tabuleiro quando aumentado (ex: destaque de selecao).
    model = glm.mat4(1.0)
    model = glm.translate(model, glm.vec3(pos.x, pos.y * scale, pos.z))
    model = glm.rotate(model, glm.radians(rotation_y), glm.vec3(0, 1, 0))
    model = glm.scale(model, glm.vec3(scale))

    glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
    glUniform1i(use_vertex_color_loc, 1)
    glUniform1i(use_texture_loc, 0)

    glBindVertexArray(vao)
    glDrawElements(GL_TRIANGLES, count, GL_UNSIGNED_INT, None)


def get_shake_offset(tipo, team, current_frame):
    # Tremida que decai com o tempo, aplicada apenas no objeto realmente
    # atingido (a barreira ou o saco de moedas do time que recebeu o golpe).
    if hit_reaction is None or hit_reaction["tipo"] != tipo or hit_reaction["team"] != team:
        return glm.vec3(0, 0, 0)

    elapsed = current_frame - hit_reaction["start_time"]
    if elapsed < 0 or elapsed >= HIT_SHAKE_DURATION:
        return glm.vec3(0, 0, 0)

    decay = 1.0 - (elapsed / HIT_SHAKE_DURATION)
    wave = math.sin(elapsed * HIT_SHAKE_FREQUENCY) * HIT_SHAKE_MAGNITUDE * decay
    return glm.vec3(wave, 0, wave * 0.6)


def draw_barrier(position, rotation_y, team, current_frame):
    position = position + get_shake_offset("muro", team, current_frame)

    model = glm.mat4(1.0)
    model = glm.translate(model, position)
    model = glm.rotate(model, glm.radians(rotation_y), glm.vec3(0, 1, 0))

    glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
    glUniform1i(use_vertex_color_loc, 0)
    glUniform1i(use_texture_loc, 1)

    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, barreira_texture)

    glBindVertexArray(barrier_vao)
    glDrawElements(GL_TRIANGLES, barrier_count, GL_UNSIGNED_INT, None)


def draw_bag_model(position, color, team, current_frame, scale=1.0):
    position = position + get_shake_offset("saco", team, current_frame)

    model = glm.mat4(1.0)
    model = glm.translate(model, position)
    model = glm.scale(model, glm.vec3(scale))

    glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
    glUniform1i(use_vertex_color_loc, 0)
    glUniform1i(use_texture_loc, 0)
    glUniform3f(object_color_loc, *color)

    glBindVertexArray(moedas_vao)
    glDrawElements(GL_TRIANGLES, moedas_count, GL_UNSIGNED_INT, None)


def get_roleta_x(window_width):
    return (window_width - roleta_largura) / 2


def draw_roleta_tela(window_width, window_height):
    roleta_tela_x = get_roleta_x(window_width)
    draw_button(roleta_tela_x + 5, roleta_y + 5, roleta_largura, roleta_altura, (0.03, 0.03, 0.04), window_width, window_height)
    draw_button(roleta_tela_x, roleta_y, roleta_largura, roleta_altura, (0.05, 0.06, 0.08), window_width, window_height)

    margem = 14
    tela_x = roleta_tela_x + margem
    tela_y = roleta_y + margem
    tela_largura = roleta_largura - margem * 2
    tela_altura = roleta_altura - margem * 2
    draw_button(tela_x, tela_y, tela_largura, tela_altura, (0.12, 0.14, 0.17), window_width, window_height)

    gap = 8
    barra_largura = (tela_largura - gap * 6) / 5
    barra_altura = tela_altura - gap * 2

    for i, resultado in enumerate(roleta_resultados):
        barra_x = tela_x + gap + i * (barra_largura + gap)
        barra_y = tela_y + gap
        draw_button(barra_x, barra_y, barra_largura, barra_altura, roleta_opcoes[resultado]["color"], window_width, window_height)


def draw_segmented_stat_bar(x, y, w, h, value, max_value, color, window_width, window_height, active=True):
    max_value = max(1, int(max_value))
    value = max(0, min(max_value, int(value)))
    gap = 3
    segment_w = (w - gap * (max_value - 1)) / max_value
    fill_color = color if active else tuple(c * 0.35 + 0.10 for c in color)

    for i in range(max_value):
        segment_x = x + i * (segment_w + gap)
        segment_color = fill_color if i < value else (0.16, 0.17, 0.20)
        draw_button(segment_x, y, segment_w, h, segment_color, window_width, window_height)


def label_color(active):
    return (0.92, 0.92, 0.90) if active else (0.36, 0.37, 0.40)


def mouse_inside_rect(mouse_x, mouse_y, x, y, w, h):
    return x <= mouse_x <= x + w and y <= mouse_y <= y + h


def draw_action_label(label, acao, player_index, x, y, scale, active, window_width, window_height):
    global action_hovered

    mouse_x, mouse_y = glfw.get_cursor_pos(window)
    text_w = get_text_width(label, scale)
    text_h = 7 * scale
    hovered = mouse_inside_rect(mouse_x, mouse_y, x, y, text_w, text_h)

    draw_text(label, x, y, scale, label_color(active), window_width, window_height)
    if hovered and active:
        action_hovered = True
        dash_w = 8
        gap = 4
        line_y = y + text_h / 2
        dash_x = x
        while dash_x < x + text_w:
            draw_button(dash_x, line_y, min(dash_w, x + text_w - dash_x), 2, label_color(active), window_width, window_height)
            dash_x += dash_w + gap

    action_buttons.append({
        "acao": acao,
        "player_index": player_index,
        "x": x,
        "y": y,
        "w": text_w,
        "h": text_h + 4,
        "active": active,
    })


def get_personagem_image_index(personagem):
    player_index = personagem["player_index"]
    if 0 <= player_index < len(players) and players[player_index].personagem is not None:
        return players[player_index].personagem
    if personagem["name"] in player_names:
        return player_names.index(personagem["name"])
    return None


def draw_personagem_info(x, y, w, personagem, window_width, window_height):
    stats = personagem["stats"]
    player_index = personagem["player_index"]
    roubo_disponivel = pode_roubar_contra_alvo(stats, personagem["team"])
    defesa_disponivel = stats["defesa_pontos"] >= stats["defesa_max"] and pode_defender(personagem["team"])
    card_h = 154 if stats["pode_roubar"] else 134

    draw_button(x, y, w, card_h, (0.09, 0.10, 0.13), window_width, window_height)

    nome_scale = 2
    portrait_size = 40
    nome_x = x + 8 + portrait_size / 2 - get_text_width(personagem["name"], nome_scale) / 2
    draw_text(personagem["name"], nome_x, y + 8, nome_scale, (0.88, 0.90, 0.95), window_width, window_height)
    draw_button(x + 8, y + 28, portrait_size, portrait_size, (0.03, 0.03, 0.04), window_width, window_height)
    draw_character_portrait(get_personagem_image_index(personagem), x + 10, y + 30, portrait_size - 4, portrait_size - 4, window_width, window_height)
    draw_text(f"DANO {stats['dano']}", x + 5, y + 70, 1, (0.80, 0.82, 0.86), window_width, window_height)
    if stats["pode_roubar"]:
        draw_text(f"ROUBO {stats['roubo_moedas']}", x + 5, y + 80, 1, (0.80, 0.82, 0.86), window_width, window_height)

    label_scale = 2
    bar_x = x + 66
    bar_w = w - 80
    bars_y = y + 30

    draw_action_label("1 ATACAR", "ataque", player_index, bar_x, bars_y, label_scale, pode_atacar(stats), window_width, window_height)
    draw_segmented_stat_bar(bar_x, bars_y + 15, bar_w, 10, stats["ataque_pontos"], stats["ataque_max"], (1.00, 0.35, 0.25), window_width, window_height, pode_atacar(stats))

    if stats["pode_roubar"]:
        draw_action_label("2 ROUBAR", "roubo", player_index, bar_x, bars_y + 31, label_scale, roubo_disponivel, window_width, window_height)
        draw_segmented_stat_bar(bar_x, bars_y + 46, bar_w, 10, stats["roubo_pontos"], stats["roubo_max"], (0.25, 0.75, 1.00), window_width, window_height, roubo_disponivel)
        evolucao_y = bars_y + 62
        evolucao_label = "3 EVOLUIR"
        defesa_label = "4 DEFENDER"
    else:
        evolucao_y = bars_y + 31
        evolucao_label = "2 EVOLUIR"
        defesa_label = "3 DEFENDER"

    draw_action_label(evolucao_label, "evolucao", player_index, bar_x, evolucao_y, label_scale, pode_evoluir(stats), window_width, window_height)
    draw_segmented_stat_bar(bar_x, evolucao_y + 15, bar_w, 10, stats["evolucao_pontos"], stats["evolucao_max"], (0.85, 0.35, 1.00), window_width, window_height, pode_evoluir(stats))

    defesa_y = evolucao_y + 31
    draw_action_label(defesa_label, "defesa", player_index, bar_x, defesa_y, label_scale, defesa_disponivel, window_width, window_height)
    draw_segmented_stat_bar(bar_x, defesa_y + 15, bar_w, 10, stats["defesa_pontos"], stats["defesa_max"], (0.65, 0.65, 0.70), window_width, window_height, defesa_disponivel)

    return card_h


def draw_player_panel(player_number, x, y, w, h, window_width, window_height):
    painel = player_panels[player_number]

    draw_button(x + 5, y + 5, w, h, (0.03, 0.03, 0.04), window_width, window_height)
    draw_button(x, y, w, h, (0.06, 0.07, 0.09), window_width, window_height)

    header_color = (0.20, 0.55, 1.00) if player_number == 1 else (1.00, 0.35, 0.35)
    draw_button(x, y, w, 16, header_color, window_width, window_height)

    item_y = y + 30
    for personagem in painel["personagens"]:
        item_h = draw_personagem_info(x + 12, item_y, w - 24, personagem, window_width, window_height)
        item_y += item_h + 14

    muro_y = y + h - 76
    draw_button(x + 12, muro_y, w - 24, 66, (0.12, 0.13, 0.16), window_width, window_height)
    draw_text("BARREIRA", x + 24, muro_y + 8, 2, (0.92, 0.92, 0.90), window_width, window_height)
    draw_segmented_stat_bar(x + 24, muro_y + 24, w - 48, 10, painel["muro"], painel["muro_max"], (0.65, 0.65, 0.70), window_width, window_height)
    draw_text("SACO MOEDAS", x + 24, muro_y + 40, 2, (0.92, 0.92, 0.90), window_width, window_height)
    draw_segmented_stat_bar(x + 24, muro_y + 56, w - 48, 10, painel["saco_moedas"], painel["saco_moedas_max"], (1.00, 0.82, 0.20), window_width, window_height)


def draw_status_panels(window_width, window_height):
    normal_w = 230
    normal_h = 455
    active_w = 260
    active_h = 500
    normal_y = 88
    active_y = 66

    p1_w = active_w if jogador_turno == 1 else normal_w
    p1_h = active_h if jogador_turno == 1 else normal_h
    p1_y = active_y if jogador_turno == 1 else normal_y

    p2_w = active_w if jogador_turno == 2 else normal_w
    p2_h = active_h if jogador_turno == 2 else normal_h
    p2_y = active_y if jogador_turno == 2 else normal_y

    p1_x = 18
    p2_x = window_width - p2_w - 18

    draw_text("JOGADOR 1", p1_x + 8, p1_y - 24, 3, (0.0, 0.0, 0.0), window_width, window_height)
    draw_text("JOGADOR 2", p2_x + p2_w - get_text_width("JOGADOR 2", 3) - 8, p2_y - 24, 3, (0.0, 0.0, 0.0), window_width, window_height)

    draw_player_panel(1, p1_x, p1_y, p1_w, p1_h, window_width, window_height)
    draw_player_panel(2, p2_x, p2_y, p2_w, p2_h, window_width, window_height)


def mouse_inside_roleta(mouse_x, mouse_y):
    roleta_tela_x = get_roleta_x(current_window_width)
    return (
        roleta_tela_x <= mouse_x <= roleta_tela_x + roleta_largura
        and roleta_y <= mouse_y <= roleta_y + roleta_altura
    )


def pode_atacar(stats):
    return stats["ataque_pontos"] >= stats["ataque_max"]


def pode_roubar(stats):
    return stats["pode_roubar"] and stats["roubo_pontos"] >= stats["roubo_max"]


def pode_roubar_contra_alvo(stats, team):
    if not pode_roubar(stats):
        return False
    alvo = player_adversario(team)
    return not stats["roubo_requer_muro_destruido"] or player_panels[alvo]["muro"] == 0


def pode_evoluir(stats):
    return stats["evolucao_pontos"] >= stats["evolucao_max"]


def adicionar_pontos_personagem(player_index, tipo, pontos):
    stats = players[player_index].stats

    if tipo == "ataque":
        stats["ataque_pontos"] = min(stats["ataque_max"], stats["ataque_pontos"] + pontos)
    elif tipo == "roubo" and stats["pode_roubar"]:
        stats["roubo_pontos"] = min(stats["roubo_max"], stats["roubo_pontos"] + pontos)
    elif tipo == "evolucao":
        stats["evolucao_pontos"] = min(stats["evolucao_max"], stats["evolucao_pontos"] + pontos)
    elif tipo == "defesa":
        stats["defesa_pontos"] = min(stats["defesa_max"], stats["defesa_pontos"] + pontos)

    atualizar_painel_do_player(player_index)


def evoluir_personagem(player_index):
    stats = players[player_index].stats

    if not pode_evoluir(stats):
        return False

    stats["evolucao_pontos"] = 0
    stats["nivel"] += 1
    stats["dano"] += 1

    atualizar_painel_do_player(player_index)
    return True


def atualizar_painel_do_player(player_index):
    team = players[player_index].team
    slot = 0 if player_index in [0, 2] else 1

    player_panels[team]["personagens"][slot] = {
        "name": players[player_index].name,
        "stats": players[player_index].stats,
        "team": team,
        "player_index": player_index,
    }


def player_adversario(player_number):
    return 2 if player_number == 1 else 1


def atacar_muro(player_number, dano):
    alvo = player_adversario(player_number)
    player_panels[alvo]["muro"] = max(0, player_panels[alvo]["muro"] - dano)
    return player_panels[alvo]["muro"] == 0


def atacar_saco_moedas(player_number, dano):
    alvo = player_adversario(player_number)
    player_panels[alvo]["saco_moedas"] = max(0, player_panels[alvo]["saco_moedas"] - dano)
    return player_panels[alvo]["saco_moedas"] == 0


def roubar_moedas(player_number, quantidade):
    alvo = player_adversario(player_number)
    roubado = min(quantidade, player_panels[alvo]["saco_moedas"])
    player_panels[alvo]["saco_moedas"] -= roubado
    player_panels[player_number]["saco_moedas"] = min(
        player_panels[player_number]["saco_moedas_max"],
        player_panels[player_number]["saco_moedas"] + roubado
    )
    return player_panels[alvo]["saco_moedas"] == 0


def pode_defender(player_number):
    return player_panels[player_number]["muro"] < player_panels[player_number]["muro_max"]


def evoluir_barreira(player_index):
    stats = players[player_index].stats
    team = players[player_index].team

    if stats["defesa_pontos"] < stats["defesa_max"] or not pode_defender(team):
        return False

    stats["defesa_pontos"] = 0
    player_panels[team]["muro_max"] = 5
    player_panels[team]["muro"] = min(player_panels[team]["muro_max"], player_panels[team]["muro"] + 2)
    atualizar_painel_do_player(player_index)
    return True


def iniciar_reacao_de_impacto(team_atacante, tipo):
    # O objeto realmente atingido (a barreira ou o saco de moedas do time
    # que recebeu o golpe) treme por um instante; a troca de turno (e o
    # movimento da camera) so acontece depois dessa pausa, para dar tempo
    # do jogador perceber visualmente o golpe.
    global hit_reaction
    global pending_turn_change_time

    tempo_atual = glfw.get_time()
    time_alvo = player_adversario(team_atacante)

    hit_reaction = {"tipo": tipo, "team": time_alvo, "start_time": tempo_atual}
    pending_turn_change_time = tempo_atual + HIT_SHAKE_DURATION + HIT_PAUSE_AFTER_SHAKE


def executar_acao_personagem(player_index, acao):
    # Aplica a regra da acao escolhida e informa se o turno foi consumido.
    global vencedor

    if player_index is None:
        return False

    if players[player_index].team != jogador_turno:
        return False

    stats = players[player_index].stats
    team = players[player_index].team

    if acao == "ataque":
        if not pode_atacar(stats):
            return False

        stats["ataque_pontos"] = 0
        alvo = player_adversario(team)
        if stats["ataque_requer_muro_destruido"] and player_panels[alvo]["muro"] > 0:
            atacar_muro(team, stats["dano"])
            atualizar_painel_do_player(player_index)
            iniciar_reacao_de_impacto(team, "muro")
            return True

        venceu = atacar_saco_moedas(team, stats["dano"])
        atualizar_painel_do_player(player_index)
        if venceu:
            vencedor = team
        else:
            iniciar_reacao_de_impacto(team, "saco")
        return True

    if acao == "roubo":
        if not pode_roubar_contra_alvo(stats, team):
            return False

        stats["roubo_pontos"] = 0
        venceu = roubar_moedas(team, stats["roubo_moedas"])
        atualizar_painel_do_player(player_index)
        if venceu:
            vencedor = team
        else:
            iniciar_reacao_de_impacto(team, "saco")
        return True

    if acao == "evolucao":
        return evoluir_personagem(player_index)

    if acao == "defesa":
        return evoluir_barreira(player_index)

    return False


def finalizar_turno_apos_acao():
    global jogador_turno
    global selected_action_player

    jogador_turno = player_adversario(jogador_turno)
    selected_action_player = None
    atualizar_camera_por_turno()


def handle_action_click(mouse_x, mouse_y):
    if selected_action_player is None:
        return False

    for action_button in action_buttons:
        if not mouse_inside_rect(mouse_x, mouse_y, action_button["x"], action_button["y"], action_button["w"], action_button["h"]):
            continue
        if action_button["player_index"] != selected_action_player or not action_button["active"]:
            return True
        if executar_acao_personagem(selected_action_player, action_button["acao"]):
            if vencedor is None and pending_turn_change_time is None:
                finalizar_turno_apos_acao()
            return True
        return True

    return False


def verificar_teclas_de_acao():
    global action_key_1_last
    global action_key_2_last
    global action_key_3_last
    global action_key_4_last

    key_1 = glfw.get_key(window, glfw.KEY_1) == glfw.PRESS
    key_2 = glfw.get_key(window, glfw.KEY_2) == glfw.PRESS
    key_3 = glfw.get_key(window, glfw.KEY_3) == glfw.PRESS
    key_4 = glfw.get_key(window, glfw.KEY_4) == glfw.PRESS
    fez_acao = False

    if key_1 and not action_key_1_last:
        fez_acao = executar_acao_personagem(selected_action_player, "ataque")

    if not fez_acao and key_2 and not action_key_2_last:
        if selected_action_player is not None and players[selected_action_player].stats["pode_roubar"]:
            fez_acao = executar_acao_personagem(selected_action_player, "roubo")
        else:
            fez_acao = executar_acao_personagem(selected_action_player, "evolucao")

    if not fez_acao and key_3 and not action_key_3_last:
        if selected_action_player is not None and players[selected_action_player].stats["pode_roubar"]:
            fez_acao = executar_acao_personagem(selected_action_player, "evolucao")
        else:
            fez_acao = executar_acao_personagem(selected_action_player, "defesa")

    if not fez_acao and key_4 and not action_key_4_last:
        if selected_action_player is not None and players[selected_action_player].stats["pode_roubar"]:
            fez_acao = executar_acao_personagem(selected_action_player, "defesa")

    if fez_acao and vencedor is None and pending_turn_change_time is None:
        finalizar_turno_apos_acao()

    action_key_1_last = key_1
    action_key_2_last = key_2
    action_key_3_last = key_3
    action_key_4_last = key_4


def sortear_roleta_resultados():
    return [random.choice(roleta_tipos) for _ in range(5)]


def iniciar_roleta(tempo_atual):
    global roleta_girando
    global roleta_fim_tempo
    global roleta_proximo_tick
    global roleta_resultados

    roleta_girando = True
    roleta_fim_tempo = tempo_atual + 1.25
    roleta_proximo_tick = tempo_atual
    roleta_resultados = sortear_roleta_resultados()


def atualizar_roleta(tempo_atual):
    global roleta_girando
    global roleta_proximo_tick
    global roleta_resultados
    global jogador_turno
    global selected_action_player

    if not roleta_girando:
        return

    if tempo_atual >= roleta_proximo_tick:
        roleta_resultados = sortear_roleta_resultados()
        roleta_proximo_tick = tempo_atual + 0.08

    if tempo_atual >= roleta_fim_tempo:
        roleta_girando = False
        roleta_resultados = sortear_roleta_resultados()
        aplicar_resultado_roleta(jogador_turno)
        jogador_turno = player_adversario(jogador_turno)
        selected_action_player = None
        atualizar_camera_por_turno()


def aplicar_resultado_roleta(player_number):
    player_indices = [i for i, p in enumerate(players) if p.team == player_number]

    for resultado in roleta_resultados:
        if resultado == "ataque":
            for index in player_indices:
                adicionar_pontos_personagem(index, "ataque", 1)

        elif resultado == "roubo":
            for index in player_indices:
                adicionar_pontos_personagem(index, "roubo", 1)

        elif resultado == "evolucao":
            for index in player_indices:
                adicionar_pontos_personagem(index, "evolucao", 1)

        elif resultado == "barreira":
            for index in player_indices:
                adicionar_pontos_personagem(index, "defesa", 1)


def atualizar_camera_por_turno():
    global camera_target_angle

    if jogador_turno == 1:
        camera_target_angle = CAMERA_ANGLE
    else:
        camera_target_angle = 0.0


def get_selection_options(window_width, window_height):
    option_size = 110
    gap = 34
    total_width = option_size * 4 + gap * 3
    start_x = (window_width - total_width) / 2
    y = window_height / 2 - option_size / 2

    options = []
    for i in range(len(player_names)):
        options.append({
            "index": i,
            "x": start_x + i * (option_size + gap),
            "y": y,
            "w": option_size,
            "h": option_size,
        })

    return options


def aplicar_selecao_players():
    player_slots = [
        {"pos": glm.vec3(4.62, 0.5, -12.88), "team": 1},
        {"pos": glm.vec3(-4.31, 0.5, -12.76), "team": 1},
        {"pos": glm.vec3(-4.49, 0.5, 12.56), "team": 2},
        {"pos": glm.vec3(4.47, 0.5, 12.60), "team": 2},
    ]

    ordem_escolhida = jogador1_selecao + jogador2_selecao

    for slot, escolha in enumerate(ordem_escolhida):
        players[slot].pos = glm.vec3(player_slots[slot]["pos"])
        players[slot].name = player_names[escolha]
        players[slot].personagem = escolha
        players[slot].stats = dict(personagem_stats[escolha])
        players[slot].team = player_slots[slot]["team"]

    player_panels[1]["personagens"] = [
        {"name": players[0].name, "stats": players[0].stats, "team": 1, "player_index": 0},
        {"name": players[1].name, "stats": players[1].stats, "team": 1, "player_index": 1},
    ]
    player_panels[2]["personagens"] = [
        {"name": players[2].name, "stats": players[2].stats, "team": 2, "player_index": 2},
        {"name": players[3].name, "stats": players[3].stats, "team": 2, "player_index": 3},
    ]


def draw_selection_screen(window_width, window_height):
    draw_button(0, 0, window_width, window_height, (0.08, 0.09, 0.11), window_width, window_height)

    for option in get_selection_options(window_width, window_height):
        index = option["index"]
        if jogador_selecionando == 1:
            border_color = (0.20, 0.55, 1.00)
        elif jogador_selecionando == 2:
            border_color = (1.00, 0.35, 0.35)
        else:
            border_color = (0.72, 0.74, 0.78)

        nome = player_names[index]
        nome_scale = 3
        nome_x = option["x"] + option["w"] / 2 - get_text_width(nome, nome_scale) / 2
        draw_text(nome, nome_x, option["y"] - 34, nome_scale, (0.88, 0.90, 0.95), window_width, window_height)

        draw_button(option["x"] - 8, option["y"] - 8, option["w"] + 16, option["h"] + 16, border_color, window_width, window_height)
        draw_button(option["x"], option["y"], option["w"], option["h"], (0.03, 0.03, 0.04), window_width, window_height)
        draw_character_portrait(index, option["x"] + 4, option["y"] + 4, option["w"] - 8, option["h"] - 8, window_width, window_height)

    slot_w = 72
    slot_h = 44
    slot_gap = 18
    group_w = slot_w * 2 + slot_gap
    j1_x = window_width / 2 - group_w - 80
    j2_x = window_width / 2 + 80
    slot_y = window_height - 115
    label_scale = 2
    draw_text("JOGADOR 1", j1_x + group_w / 2 - get_text_width("JOGADOR 1", label_scale) / 2, slot_y - 28, label_scale, (0.88, 0.90, 0.95), window_width, window_height)
    draw_text("JOGADOR 2", j2_x + group_w / 2 - get_text_width("JOGADOR 2", label_scale) / 2, slot_y - 28, label_scale, (0.88, 0.90, 0.95), window_width, window_height)

    for slot in range(2):
        j1_slot_x = j1_x + slot * (slot_w + slot_gap)
        draw_button(j1_slot_x, slot_y, slot_w, slot_h, (0.18, 0.20, 0.24), window_width, window_height)
        if slot < len(jogador1_selecao):
            draw_character_portrait(jogador1_selecao[slot], j1_slot_x + 3, slot_y + 3, slot_w - 6, slot_h - 6, window_width, window_height)

        j2_slot_x = j2_x + slot * (slot_w + slot_gap)
        draw_button(j2_slot_x, slot_y, slot_w, slot_h, (0.18, 0.20, 0.24), window_width, window_height)
        if slot < len(jogador2_selecao):
            draw_character_portrait(jogador2_selecao[slot], j2_slot_x + 3, slot_y + 3, slot_w - 6, slot_h - 6, window_width, window_height)


def handle_selection_click(mouse_x, mouse_y):
    global tela_atual
    global jogador_selecionando

    for option in get_selection_options(current_window_width, current_window_height):
        inside_x = option["x"] <= mouse_x <= option["x"] + option["w"]
        inside_y = option["y"] <= mouse_y <= option["y"] + option["h"]

        if not (inside_x and inside_y):
            continue

        index = option["index"]
        if jogador_selecionando == 1:
            jogador1_selecao.append(index)
            if len(jogador1_selecao) == 2:
                jogador_selecionando = 2
        else:
            jogador2_selecao.append(index)
            if len(jogador2_selecao) == 2:
                aplicar_selecao_players()
                atualizar_camera_por_turno()
                tela_atual = "tabuleiro"

        return


def draw_button(x, y, w, h, color, window_width, window_height):
    # Retangulo 2D usado nos paineis, barras, roleta e overlays.
    glUseProgram(button_shader)
    left, top = to_ndc(x, y, window_width, window_height)
    right, bottom = to_ndc(x + w, y + h, window_width, window_height)

    r, g, b = color

    vertices = np.array([
        left,  bottom, r, g, b,
        right, bottom, r, g, b,
        right, top,    r, g, b,

        left,  bottom, r, g, b,
        right, top,    r, g, b,
        left,  top,    r, g, b,
    ], dtype=np.float32)

    glBindBuffer(GL_ARRAY_BUFFER, button_vbo)
    glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)

    glBindVertexArray(button_vao)
    glDrawArrays(GL_TRIANGLES, 0, 6)


def draw_text(text, x, y, scale, color, window_width, window_height):
    text_renderer.draw(text, x, y, scale, color, window_width, window_height)


def draw_centered_text(text, y, scale, color, window_width, window_height):
    draw_text(text, window_width / 2 - get_text_width(text, scale) / 2, y, scale, color, window_width, window_height)


def draw_game_over(window_width, window_height):
    if vencedor is None:
        return

    draw_button(0, 0, window_width, window_height, (0.02, 0.02, 0.03), window_width, window_height)
    draw_centered_text("GAME OVER", window_height / 2 - 75, 7, (1.00, 0.25, 0.20), window_width, window_height)
    draw_centered_text(f"PLAYER {vencedor} GANHOU", window_height / 2 + 10, 4, (0.92, 0.92, 0.90), window_width, window_height)


def get_text_width(text, scale):
    return text_renderer.measure(text, scale)


def mouse_to_world_on_plane(mouse_x, mouse_y, plane_y):
    if current_view is None or current_projection is None:
        return None

    x = (2.0 * mouse_x) / current_window_width - 1.0
    y = 1.0 - (2.0 * mouse_y) / current_window_height

    ray_clip_near = glm.vec4(x, y, -1.0, 1.0)
    ray_clip_far = glm.vec4(x, y, 1.0, 1.0)

    inverse_matrix = glm.inverse(current_projection * current_view)

    world_near = inverse_matrix * ray_clip_near
    world_far = inverse_matrix * ray_clip_far

    world_near /= world_near.w
    world_far /= world_far.w

    ray_origin = glm.vec3(world_near)
    ray_end = glm.vec3(world_far)
    ray_dir = glm.normalize(ray_end - ray_origin)

    if abs(ray_dir.y) < 0.0001:
        return None

    distance = (plane_y - ray_origin.y) / ray_dir.y

    if distance < 0:
        return None

    return ray_origin + ray_dir * distance


def get_clicked_player(mouse_x, mouse_y):
    nearest_index = None
    nearest_distance = 999999.0

    for index, player in enumerate(players):
        world_pos = mouse_to_world_on_plane(mouse_x, mouse_y, 0.5)
        if world_pos is None:
            continue

        dx = world_pos.x - player.pos.x
        dz = world_pos.z - player.pos.z
        distance = math.sqrt(dx * dx + dz * dz)

        if distance < 0.9 and distance < nearest_distance:
            nearest_index = index
            nearest_distance = distance

    return nearest_index


def mouse_button_callback(window, button, action, mods):
    global selected_action_player

    if button != glfw.MOUSE_BUTTON_LEFT:
        return

    mouse_x, mouse_y = glfw.get_cursor_pos(window)

    if action != glfw.PRESS:
        return

    if tela_atual == "selecao":
        handle_selection_click(mouse_x, mouse_y)
        return

    if vencedor is not None:
        return

    if pending_turn_change_time is not None:
        return

    if handle_action_click(mouse_x, mouse_y):
        return

    if mouse_inside_roleta(mouse_x, mouse_y):
        return

    clicked_player = get_clicked_player(mouse_x, mouse_y)
    if clicked_player is not None and players[clicked_player].team == jogador_turno:
        selected_action_player = clicked_player




def run():
    global window, hand_cursor, shader, button_shader, button_vao, button_vbo, text_renderer, character_textures, character_models, cube_vao, cube_count, barrier_vao, barrier_count, moedas_vao, moedas_count, floor_vao, floor_count, floor_texture, barreira_texture, projection_loc, view_loc, model_loc, object_color_loc, use_vertex_color_loc, use_texture_loc, light_color_loc, light_pos_loc, view_pos_loc, camera_distance, camera_angle, camera_target_angle, camera_forward_offset, board_half_width, board_bottom_length, board_top_length, action_buttons, action_hovered, tela_atual, jogador_selecionando, jogador1_selecao, jogador2_selecao, current_view, current_projection, current_window_width, current_window_height, blue_barrier_pos, red_barrier_pos, roleta_x, roleta_y, roleta_largura, roleta_altura, roleta_tipos, roleta_opcoes, roleta_resultados, roleta_girando, roleta_fim_tempo, roleta_proximo_tick, jogador_turno, space_pressed_last, selected_action_player, action_key_1_last, action_key_2_last, action_key_3_last, action_key_4_last, vencedor, players, player_names, personagem_stats, player_panels, blue_bag, red_bag, hit_reaction, pending_turn_change_time

    # Inicializacao da janela, contexto OpenGL e buffers usados pelo jogo.
    if not glfw.init():
        raise Exception("GLFW nao iniciou")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.SAMPLES, 4)

    window = glfw.create_window(
        WINDOW_WIDTH,
        WINDOW_HEIGHT,
        GAME_TITLE,
        None,
        None
    )

    if not window:
        glfw.terminate()
        raise Exception("Erro ao criar janela")

    glfw.make_context_current(window)
    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)
    glfw.set_mouse_button_callback(window, mouse_button_callback)
    hand_cursor = glfw.create_standard_cursor(glfw.HAND_CURSOR)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_MULTISAMPLE)

    shader = create_shader_program(VERTEX_SHADER, FRAGMENT_SHADER)
    button_shader, button_vao, button_vbo = create_button_renderer()
    text_renderer = TextRenderer()
    character_textures = load_character_textures()

    cube_vao, cube_count = create_cube()
    character_models = load_character_models()
    barrier_vao, barrier_count = create_mesh_from_npz(MODEL_DIR / "barreira.npz")
    moedas_vao, moedas_count = create_mesh_from_npz(MODEL_DIR / "moedas.npz")
    floor_vao, floor_count = create_textured_quad(1.0, 1.0)
    floor_texture = load_floor_texture(ASSET_DIR / "texturas" / "piso.jpg")
    barreira_texture = load_floor_texture(ASSET_DIR / "texturas" / "madeira_musgo.jpg")

    camera_distance = CAMERA_DISTANCE
    camera_angle = CAMERA_ANGLE
    camera_target_angle = CAMERA_ANGLE
    camera_forward_offset = CAMERA_FORWARD_OFFSET

    board_half_width = BOARD_HALF_WIDTH
    board_bottom_length = BOARD_BOTTOM_LENGTH
    board_top_length = BOARD_TOP_LENGTH

    action_buttons = []
    action_hovered = False
    tela_atual = "selecao"
    jogador_selecionando = 1
    jogador1_selecao = []
    jogador2_selecao = []
    current_view = None
    current_projection = None
    current_window_width = WINDOW_WIDTH
    current_window_height = WINDOW_HEIGHT

    blue_barrier_pos = glm.vec3(0.18, 0.05, 8.99)
    red_barrier_pos = glm.vec3(-0.04, 0.05, -8.59)
    roleta_x = ROLETA_X
    roleta_y = ROLETA_Y
    roleta_largura = ROLETA_LARGURA
    roleta_altura = ROLETA_ALTURA
    roleta_tipos = ["ataque", "roubo", "evolucao", "barreira"]
    roleta_opcoes = {
        "ataque": {"color": (1.00, 0.25, 0.20)},
        "roubo": {"color": (0.20, 0.70, 1.00)},
        "evolucao": {"color": (0.85, 0.30, 0.95)},
        "barreira": {"color": (0.62, 0.62, 0.66)},
    }
    roleta_resultados = ["ataque", "roubo", "evolucao", "barreira", "ataque"]
    roleta_girando = False
    roleta_fim_tempo = 0.0
    roleta_proximo_tick = 0.0
    jogador_turno = 1
    space_pressed_last = False
    selected_action_player = None
    action_key_1_last = False
    action_key_2_last = False
    action_key_3_last = False
    action_key_4_last = False
    vencedor = None
    hit_reaction = None
    pending_turn_change_time = None

    players = [
        Player("TIGRE", glm.vec3(-4.49, 0.5, 12.56), team=1),
        Player("DRAGAO", glm.vec3(4.47, 0.5, 12.60), team=1),
        Player("PANDA", glm.vec3(-4.31, 0.5, -12.76), team=2),
        Player("MACACO", glm.vec3(4.62, 0.5, -12.88), team=2),
    ]

    player_names = [
        "TIGRE",
        "DRAGAO",
        "PANDA",
        "MACACO",
    ]

    personagem_stats = [
        {
            "ataque_pontos": 3,
            "ataque_max": 5,
            "dano": 3,
            "ataque_requer_muro_destruido": True,
            "roubo_pontos": 0,
            "roubo_max": 0,
            "pode_roubar": False,
            "roubo_requer_muro_destruido": False,
            "roubo_moedas": 0,
            "evolucao_pontos": 0,
            "evolucao_max": 8,
            "defesa_pontos": 0,
            "defesa_max": 5,
            "evolucao_bonus": "dano",
            "nivel": 1,
        },
        {
            "ataque_pontos": 1,
            "ataque_max": 5,
            "dano": 1,
            "ataque_requer_muro_destruido": False,
            "roubo_pontos": 0,
            "roubo_max": 0,
            "pode_roubar": False,
            "roubo_requer_muro_destruido": False,
            "roubo_moedas": 0,
            "evolucao_pontos": 0,
            "evolucao_max": 8,
            "defesa_pontos": 0,
            "defesa_max": 5,
            "evolucao_bonus": "dano",
            "nivel": 1,
        },
        {
            "ataque_pontos": 3,
            "ataque_max": 5,
            "dano": 3,
            "ataque_requer_muro_destruido": True,
            "roubo_pontos": 0,
            "roubo_max": 3,
            "pode_roubar": True,
            "roubo_requer_muro_destruido": True,
            "roubo_moedas": 2,
            "evolucao_pontos": 0,
            "evolucao_max": 8,
            "defesa_pontos": 0,
            "defesa_max": 5,
            "evolucao_bonus": "dano",
            "nivel": 1,
        },
        {
            "ataque_pontos": 1,
            "ataque_max": 5,
            "dano": 1,
            "ataque_requer_muro_destruido": False,
            "roubo_pontos": 0,
            "roubo_max": 7,
            "pode_roubar": True,
            "roubo_requer_muro_destruido": False,
            "roubo_moedas": 1,
            "evolucao_pontos": 0,
            "evolucao_max": 8,
            "defesa_pontos": 0,
            "defesa_max": 5,
            "evolucao_bonus": "roubo",
            "nivel": 1,
        },
    ]

    player_panels = {
        1: {
            "muro": 5,
            "muro_max": 5,
            "saco_moedas": 10,
            "saco_moedas_max": 10,
            "personagens": [
                {"name": player_names[0], "stats": dict(personagem_stats[0]), "team": 1, "player_index": 0},
                {"name": player_names[1], "stats": dict(personagem_stats[1]), "team": 1, "player_index": 1},
            ],
        },
        2: {
            "muro": 5,
            "muro_max": 5,
            "saco_moedas": 10,
            "saco_moedas_max": 10,
            "personagens": [
                {"name": player_names[2], "stats": dict(personagem_stats[2]), "team": 2, "player_index": 2},
                {"name": player_names[3], "stats": dict(personagem_stats[3]), "team": 2, "player_index": 3},
            ],
        },
    }

    blue_bag = {"pos": glm.vec3(0.15, 0.4, 9.44), "carrier": None}
    red_bag = {"pos": glm.vec3(-0.03, 0.4, -9.22), "carrier": None}

    last_frame_time = glfw.get_time()

    while not glfw.window_should_close(window):
        current_frame = glfw.get_time()
        delta_time = current_frame - last_frame_time
        last_frame_time = current_frame

        glfw.poll_events()

        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            glfw.set_window_should_close(window, True)

        if tela_atual == "selecao":
            width, height = glfw.get_framebuffer_size(window)
            current_window_width = width
            current_window_height = height

            glClearColor(0.08, 0.09, 0.11, 1.0)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            glDisable(GL_DEPTH_TEST)
            glUseProgram(button_shader)
            draw_selection_screen(width, height)
            glEnable(GL_DEPTH_TEST)

            glfw.swap_buffers(window)
            continue

        space_pressed = glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS
        if space_pressed and not space_pressed_last and not roleta_girando and vencedor is None:
            iniciar_roleta(current_frame)
        space_pressed_last = space_pressed

        atualizar_roleta(current_frame)

        if pending_turn_change_time is not None and current_frame >= pending_turn_change_time:
            pending_turn_change_time = None
            hit_reaction = None
            if vencedor is None:
                finalizar_turno_apos_acao()

        if not roleta_girando and vencedor is None and pending_turn_change_time is None:
            verificar_teclas_de_acao()

        for i, player in enumerate(players):
            pos = player.pos

            if players[i].team == 1 and red_bag["carrier"] is None:
                if glm.distance(pos, red_bag["pos"]) < 1.2:
                    red_bag["carrier"] = i

            if players[i].team == 2 and blue_bag["carrier"] is None:
                if glm.distance(pos, blue_bag["pos"]) < 1.2:
                    blue_bag["carrier"] = i

        if blue_bag["carrier"] is not None:
            blue_bag["pos"] = players[blue_bag["carrier"]].pos + glm.vec3(0, 0.7, 0)

        if red_bag["carrier"] is not None:
            red_bag["pos"] = players[red_bag["carrier"]].pos + glm.vec3(0, 0.7, 0)

        if red_bag["carrier"] is not None and players[red_bag["carrier"]].team == 1:
            carrier_pos = players[red_bag["carrier"]].pos

            if glm.distance(carrier_pos, glm.vec3(0, 0.05, 5.5)) < 1.5:
                red_bag["carrier"] = None
                red_bag["pos"] = glm.vec3(0, 0.4, -5.5)

        if blue_bag["carrier"] is not None and players[blue_bag["carrier"]].team == 2:
            carrier_pos = players[blue_bag["carrier"]].pos

            if glm.distance(carrier_pos, glm.vec3(0, 0.05, -5.5)) < 1.5:
                blue_bag["carrier"] = None
                blue_bag["pos"] = glm.vec3(0, 0.4, 5.5)

        glClearColor(0.82, 0.86, 0.91, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(shader)

        width, height = glfw.get_framebuffer_size(window)
        aspect = width / height

        # Aproximacao suave (lerp) do angulo atual em direcao ao angulo alvo,
        # em vez de saltar instantaneamente quando o turno muda.
        angle_diff = camera_target_angle - camera_angle
        camera_angle += angle_diff * min(1.0, delta_time * CAMERA_TURN_SPEED)

        forward_x = -math.sin(camera_angle)
        forward_z = -math.cos(camera_angle)

        camera_focus = glm.vec3(
            forward_x * camera_forward_offset,
            0,
            forward_z * camera_forward_offset
        )

        camera_pos = camera_focus + glm.vec3(
            math.sin(camera_angle) * camera_distance,
            25,
            math.cos(camera_angle) * camera_distance
        )

        view = glm.lookAt(
            camera_pos,
            camera_focus,
            glm.vec3(0, 1, 0)
        )

        projection = glm.perspective(
            glm.radians(25),
            aspect,
            0.1,
            100.0
        )

        current_view = view
        current_projection = projection
        current_window_width = width
        current_window_height = height

        projection_loc = glGetUniformLocation(shader, "projection")
        view_loc = glGetUniformLocation(shader, "view")
        model_loc = glGetUniformLocation(shader, "model")
        object_color_loc = glGetUniformLocation(shader, "objectColor")
        use_vertex_color_loc = glGetUniformLocation(shader, "useVertexColor")
        use_texture_loc = glGetUniformLocation(shader, "useTexture")
        glUniform1i(glGetUniformLocation(shader, "objectTexture"), 0)
        light_color_loc = glGetUniformLocation(shader, "lightColor")
        light_pos_loc = glGetUniformLocation(shader, "lightPos")
        view_pos_loc = glGetUniformLocation(shader, "viewPos")

        glUniformMatrix4fv(projection_loc, 1, GL_FALSE, glm.value_ptr(projection))
        glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(view))

        board_center_z = (board_bottom_length - board_top_length) / 2.0

        # Iluminacao dinamica: a luz orbita lentamente sobre o tabuleiro,
        # mas a intensidade fica sempre fixa e clara (sem escurecer).
        light_angle = current_frame * LIGHT_ORBIT_SPEED
        light_pos = glm.vec3(
            math.sin(light_angle) * LIGHT_ORBIT_RADIUS,
            LIGHT_ORBIT_HEIGHT,
            math.cos(light_angle) * LIGHT_ORBIT_RADIUS + board_center_z
        )

        glUniform3f(light_color_loc, 1.0, 1.0, 1.0)
        glUniform3fv(light_pos_loc, 1, glm.value_ptr(light_pos))
        glUniform3fv(view_pos_loc, 1, glm.value_ptr(camera_pos))
        board_total_half = (board_bottom_length + board_top_length) / 2.0

        draw_cube(
            glm.vec3(0, -0.15, board_center_z),
            glm.vec3(board_half_width, 0.1, board_total_half),
            (0.45, 0.35, 0.22)
        )

        draw_floor(glm.vec3(0, -0.03, board_center_z), board_half_width * 2, board_total_half * 2)

        border_color = (0.55, 0.55, 0.55)

        draw_cube(glm.vec3(0, 0.35, -board_top_length), glm.vec3(board_half_width + 0.2, 0.4, 0.2), border_color)
        draw_cube(glm.vec3(0, 0.35, board_bottom_length), glm.vec3(board_half_width + 0.2, 0.4, 0.2), border_color)
        draw_cube(glm.vec3(-board_half_width, 0.35, board_center_z), glm.vec3(0.2, 0.4, board_total_half), border_color)
        draw_cube(glm.vec3(board_half_width, 0.35, board_center_z), glm.vec3(0.2, 0.4, board_total_half), border_color)

        if player_panels[1]["muro"] > 0:
            draw_barrier(red_barrier_pos, 0, 1, current_frame)
        if player_panels[2]["muro"] > 0:
            draw_barrier(blue_barrier_pos, 180, 2, current_frame)

        for index, player in enumerate(players):
            if selected_action_player == index:
                draw_character_model(index, 1.15, current_frame)
            else:
                draw_character_model(index, 1.0, current_frame)

        draw_bag_model(blue_bag["pos"], (1.0, 0.9, 0.15), 2, current_frame)
        draw_bag_model(red_bag["pos"], (1.0, 0.65, 0.05), 1, current_frame)

        glDisable(GL_DEPTH_TEST)
        glUseProgram(button_shader)

        action_hovered = False
        action_buttons.clear()
        draw_roleta_tela(width, height)
        draw_status_panels(width, height)
        draw_game_over(width, height)
        glfw.set_cursor(window, hand_cursor if action_hovered else None)

        glEnable(GL_DEPTH_TEST)

        glfw.swap_buffers(window)

    glfw.terminate()



if __name__ == "__main__":
    run()
