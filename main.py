import glfw

from game import TabuleiroGame


def main():
    if not glfw.init():
        raise Exception("GLFW nao iniciou")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    game = TabuleiroGame()

    window = glfw.create_window(
        game.resolution[0],
        game.resolution[1],
        "Proteja os Personagens - Captura Completa",
        None,
        None,
    )

    if not window:
        glfw.terminate()
        raise Exception("Erro ao criar janela")

    glfw.make_context_current(window)

    game.init_gl()

    glfw.set_framebuffer_size_callback(window, game.update_framebuffer)

    last_frame = glfw.get_time()

    while not glfw.window_should_close(window):
        current_frame = glfw.get_time()
        delta_time = current_frame - last_frame
        last_frame = current_frame

        glfw.poll_events()
        game.update(window, delta_time)
        game.render(window)
        glfw.swap_buffers(window)

    glfw.terminate()


if __name__ == "__main__":
    main()
