from OpenGL.GL import *
import OpenGL.GL.shaders as gls


def criar_programa_de_arquivos(caminho_vertice: str, caminho_fragmento: str) -> int:
    """Lê os arquivos de shader, compila e linka um programa OpenGL."""
    with open(caminho_vertice, "r", encoding="utf-8") as arquivo:
        fonte_vertice = arquivo.read()
    with open(caminho_fragmento, "r", encoding="utf-8") as arquivo:
        fonte_fragmento = arquivo.read()
    # Compilação separada do shader de vértice e do shader de fragmento.
    id_vertice = gls.compileShader(fonte_vertice, GL_VERTEX_SHADER)
    id_fragmento = gls.compileShader(fonte_fragmento, GL_FRAGMENT_SHADER)
    # Linkagem: cria o programa final usado na renderização.
    return gls.compileProgram(id_vertice, id_fragmento)
