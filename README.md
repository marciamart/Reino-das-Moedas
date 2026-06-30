# Reino das Moedas

Jogo em Python com GLFW, PyOpenGL, PyGLM, NumPy e Pillow.

## Como executar

```bash
pip install glfw PyOpenGL PyGLM numpy pillow
python main.py
```

## Estrutura

- `main.py`: ponto de entrada do jogo.
- `game.py`: logica, estado e desenho do jogo.
- `config.py`: configuracoes iniciais da janela, camera, tabuleiro e roleta.
- `shaders/`: shaders GLSL usados pelo OpenGL, incluindo texto e objetos texturizados (piso e barreira).
- `obj/`: criacao da geometria 3D (`geometry.py`) e os modelos pre-processados.
  - `obj/models/`: modelos 3D dos personagens, barreira e saco de moedas (formato .npz compacto, ja decimado, orientado e colorido/com UV).
- `assets/personagens/`: imagens 2D usadas nos paineis e na tela de selecao.
- `assets/texturas/`: texturas do piso (mapeamento planar) e da barreira (mapeamento cilindrico, baseado no angulo da normal).

## Notas de implementacao

- Personagens, barreira e saco de moedas sao posicionados de forma fixa (sem arrastar).
- A camera interpola suavemente entre os angulos de cada turno (sem teletransportar).
- A fonte de luz orbita o tabuleiro e pulsa de intensidade (iluminacao dinamica).
- Cada jogador e representado por uma classe `Player` (`game.py`), em vez de dicionarios soltos.
