from OpenGL.GL import *
import OpenGL.GL.shaders as gls


def create_program_from_files(vertex_path: str, fragment_path: str) -> int:
    with open(vertex_path, "r", encoding="utf-8") as f:
        vs_source = f.read()
    with open(fragment_path, "r", encoding="utf-8") as f:
        fs_source = f.read()
    vs_id = gls.compileShader(vs_source, GL_VERTEX_SHADER)
    fs_id = gls.compileShader(fs_source, GL_FRAGMENT_SHADER)
    return gls.compileProgram(vs_id, fs_id)
