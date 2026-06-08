import glfw

from game import TabuleiroGame


def main():
    """Cria a janela, inicializa OpenGL e executa o loop principal."""
    if not glfw.init():
        raise Exception("GLFW nao iniciou")

    # Configuração do contexto OpenGL (Core Profile 3.3).
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    game = TabuleiroGame()

    # Título vazio: o projeto não exibe mais textos (HUD/título informativo).
    janela = glfw.create_window(
        game.resolucao[0],
        game.resolucao[1],
        "",
        None,
        None,
    )

    if not janela:
        glfw.terminate()
        raise Exception("Erro ao criar janela")

    glfw.make_context_current(janela)

    # Inicializa shaders, malhas e estados de OpenGL.
    game.iniciar_gl()

    # Mantém o viewport em sincronia com o tamanho da janela.
    glfw.set_framebuffer_size_callback(janela, game.atualizar_framebuffer)

    ultimo_frame = glfw.get_time()

    try:
        while not glfw.window_should_close(janela):
            # Delta de tempo para animações (roleta) e lógica de jogo.
            frame_atual = glfw.get_time()
            delta_tempo = frame_atual - ultimo_frame
            ultimo_frame = frame_atual

            glfw.poll_events()
            game.atualizar(janela, delta_tempo)
            game.renderizar(janela)
            glfw.swap_buffers(janela)
    except KeyboardInterrupt:
        pass
    finally:
        glfw.terminate()


if __name__ == "__main__":
    main()
