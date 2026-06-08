import math
import os
import random
import time

import glfw
from OpenGL.GL import *
import glm

from obj import MalhaCubo, MalhaEsfera, MalhaBarreiraCurva
from config import criar_programa_de_arquivos


class TabuleiroGame:
    """
    Controla o estado do jogo e o loop de atualização/renderização.

    Estrutura geral:
    - "selecao": escolher os campeões de cada jogador.
    - "jogando": alterna turnos, gira roleta e executa ações (ataque/roubo/evolução/defesa).
    """

    def __init__(self):
        """Inicializa todos os estados do jogo e parâmetros de cena."""
        self.resolucao = [1280, 720]

        self.log_ativo = True
        self._contador_eventos = 0
        self._partida_finalizada = False
        self.vencedor_time = None

        # Programa de shader e locais (uniforms) usados na cena 3D.
        self.id_shader = 0
        self.locais = {}


        # Malhas básicas usadas para desenhar o tabuleiro e os elementos.
        self.cubo = None
        self.esfera = None
        self.barreira = None

        # Estado da UI em 3D: seleção de campeões ou partida.
        self.modo = "selecao"
        self.opcoes_campeoes = [
            {"nome": "Tigre", "tipo": "tigre", "cor": (0.2, 0.5, 1.0)},
            {"nome": "Macaco", "tipo": "macaco", "cor": (1.0, 0.2, 0.2)},
            {"nome": "Panda", "tipo": "panda", "cor": (0.2, 1.0, 0.4)},
            {"nome": "Dragao", "tipo": "dragao", "cor": (0.7, 0.3, 1.0)},
        ]
        self.indice_campeao_selecionado = 0
        self._slots_jogadores_time = [
            [2, 3],
            [0, 1],
        ]
        self._time_selecionando = 0
        self._slot_selecionando = 0
        self._indices_campeoes_escolhidos = [[None, None], [None, None]]
        self._estado_tecla_anterior = {}

        # Estado da partida (recursos, campeões e turno).
        self.campeoes = {}
        self.pontos_time = [
            {"esquerda": 0, "direita": 0, "muro": 0},
            {"esquerda": 0, "direita": 0, "muro": 0},
        ]
        self.vida_muro_time = [0, 0]
        self.moedas_time = [10, 10]
        self.jogador_turno = 0
        self.fase_turno = "roleta"
        self.roleta_girando = False
        self.tempo_roleta = 0.0
        self.duracao_giro_roleta = 0.9
        self.resultados_roleta = []

        # Parâmetros da câmera.
        self.distancia_camera = 45.0
        self.angulo_camera = 0.0
        self.deslocamento_frente_camera = 0.0

        # Dimensões do tabuleiro.
        self.tabuleiro_meia_largura = 7.0
        self.tabuleiro_comprimento_baixo = 16.0
        self.tabuleiro_comprimento_cima = 16.0

        # Posições fixas da barreira por time.
        self.pos_barreira_azul = glm.vec3(0, 0.05, 4.0)
        self.pos_barreira_vermelha = glm.vec3(0, 0.05, -4.0)

        # Jogadores (peças) e suas cores, ajustadas na escolha dos campeões.
        self.jogadores = [
            {"posicao": glm.vec3(-4, 0.5, 8), "cor": (0.2, 0.5, 1.0)},
            {"posicao": glm.vec3(4, 0.5, 8), "cor": (0.2, 0.5, 1.0)},
            {"posicao": glm.vec3(-4, 0.5, -8), "cor": (1.0, 0.2, 0.2)},
            {"posicao": glm.vec3(4, 0.5, -8), "cor": (1.0, 0.2, 0.2)},
        ]

        # Objetivos e sacos (representação das moedas) por lado.
        self.pos_gol_azul = glm.vec3(0, 0.05, 5.5)
        self.pos_gol_vermelho = glm.vec3(0, 0.05, -5.5)

        self.pos_saco_azul = glm.vec3(0, 0.4, 5.5)
        self.pos_saco_vermelho = glm.vec3(0, 0.4, -5.5)

        self._registrar_evento("Jogo iniciado (modo=selecao)")

    def _registrar_evento(self, mensagem: str):
        if not getattr(self, "log_ativo", False):
            return
        self._contador_eventos += 1
        timestamp_ms = int(time.time() * 1000)
        print(f"[{self._contador_eventos:04d} {timestamp_ms}] {mensagem}", flush=True)

    def _nome_tecla(self, tecla: int) -> str:
        mapeamento = {
            glfw.KEY_LEFT: "ESQUERDA",
            glfw.KEY_RIGHT: "DIREITA",
            glfw.KEY_ENTER: "ENTER",
            glfw.KEY_SPACE: "ESPACO",
            glfw.KEY_BACKSPACE: "BACKSPACE",
            glfw.KEY_ESCAPE: "ESC",
            glfw.KEY_0: "0",
            glfw.KEY_1: "1",
            glfw.KEY_2: "2",
            glfw.KEY_3: "3",
            glfw.KEY_4: "4",
            glfw.KEY_5: "5",
            glfw.KEY_6: "6",
            glfw.KEY_7: "7",
            glfw.KEY_P: "P",
        }
        if tecla in mapeamento:
            return mapeamento[tecla]
        nome = glfw.get_key_name(tecla, 0)
        if nome:
            return nome.upper()
        return str(tecla)

    def _resumo_time(self, time: int) -> str:
        return (
            f"time={time} moedas={self.moedas_time[time]} "
            f"muro={self.vida_muro_time[time]} "
            f"pontos(E={self.pontos_time[time]['esquerda']},D={self.pontos_time[time]['direita']},M={self.pontos_time[time]['muro']})"
        )

    def _desenhar_digito_7_segmentos(self, digito: int, centro: glm.vec3, tamanho: float, cor):
        segmentos_por_digito = {
            0: (0, 1, 2, 4, 5, 6),
            1: (2, 5),
            2: (0, 2, 3, 4, 6),
            3: (0, 2, 3, 5, 6),
            4: (1, 2, 3, 5),
            5: (0, 1, 3, 5, 6),
            6: (0, 1, 3, 4, 5, 6),
            7: (0, 2, 5),
            8: (0, 1, 2, 3, 4, 5, 6),
            9: (0, 1, 2, 3, 5, 6),
        }
        ativos = segmentos_por_digito.get(digito, ())
        comp_h = tamanho * 0.8
        comp_v = tamanho * 0.65
        esp = tamanho * 0.14
        prof = tamanho * 0.08
        dx = tamanho * 0.42
        dy = tamanho * 0.46
        posicoes = {
            0: (0.0, dy, comp_h, esp),
            3: (0.0, 0.0, comp_h, esp),
            6: (0.0, -dy, comp_h, esp),
            1: (-dx, dy / 2.0, esp, comp_v),
            4: (-dx, -dy / 2.0, esp, comp_v),
            2: (dx, dy / 2.0, esp, comp_v),
            5: (dx, -dy / 2.0, esp, comp_v),
        }
        for seg in ativos:
            x, y, sx, sy = posicoes[seg]
            self.desenhar_cubo(
                glm.vec3(centro.x + x, centro.y + y, centro.z),
                glm.vec3(sx / 2.0, sy / 2.0, prof / 2.0),
                cor,
            )

    def _desenhar_numero_7_segmentos(self, valor: int, centro: glm.vec3, tamanho: float, cor):
        texto = str(max(0, int(valor)))
        if len(texto) > 3:
            texto = texto[-3:]
        espacamento = tamanho * 0.9
        largura_total = len(texto) * espacamento
        x0 = centro.x - largura_total / 2.0 + espacamento / 2.0
        for i, ch in enumerate(texto):
            self._desenhar_digito_7_segmentos(
                int(ch),
                glm.vec3(x0 + i * espacamento, centro.y, centro.z),
                tamanho,
                cor,
            )

    def _renderizar_placar_superior(self, proporcao: float):
        glDisable(GL_DEPTH_TEST)
        glUseProgram(self.id_shader)

        projecao = glm.ortho(-proporcao, proporcao, -1.0, 1.0, -1.0, 1.0)
        visao = glm.mat4(1.0)
        posicao_camera = glm.vec3(0, 0, 1)
        glUniformMatrix4fv(self.locais["projection"], 1, GL_FALSE, glm.value_ptr(projecao))
        glUniformMatrix4fv(self.locais["view"], 1, GL_FALSE, glm.value_ptr(visao))
        glUniform3f(self.locais["lightColor"], 1, 1, 1)
        glUniform3f(self.locais["lightPos"], 0, 14, 0)
        glUniform3fv(self.locais["viewPos"], 1, glm.value_ptr(posicao_camera))

        margem = 0.18
        largura_painel = 0.95
        altura_painel = 0.30
        y = 0.83

        x_esquerda = -proporcao + margem + largura_painel / 2.0
        x_direita = proporcao - margem - largura_painel / 2.0

        cor_fundo = (0.08, 0.08, 0.1)
        cor_borda = (0.25, 0.25, 0.27)

        self.desenhar_cubo(glm.vec3(x_esquerda, y, 0.0), glm.vec3(largura_painel / 2.0, altura_painel / 2.0, 0.02), cor_borda)
        self.desenhar_cubo(glm.vec3(x_esquerda, y, 0.01), glm.vec3(largura_painel / 2.0 - 0.03, altura_painel / 2.0 - 0.03, 0.02), cor_fundo)

        self.desenhar_cubo(glm.vec3(x_direita, y, 0.0), glm.vec3(largura_painel / 2.0, altura_painel / 2.0, 0.02), cor_borda)
        self.desenhar_cubo(glm.vec3(x_direita, y, 0.01), glm.vec3(largura_painel / 2.0 - 0.03, altura_painel / 2.0 - 0.03, 0.02), cor_fundo)

        cor_p1 = (1.0, 0.85, 0.20)
        cor_p2 = (1.0, 0.85, 0.20)
        tamanho_digito = altura_painel * 0.65
        self._desenhar_numero_7_segmentos(self.moedas_time[0], glm.vec3(x_esquerda, y, 0.03), tamanho_digito, cor_p1)
        self._desenhar_numero_7_segmentos(self.moedas_time[1], glm.vec3(x_direita, y, 0.03), tamanho_digito, cor_p2)

        glEnable(GL_DEPTH_TEST)

    def _renderizar_tela_vitoria(self, proporcao: float):
        glDisable(GL_DEPTH_TEST)
        glUseProgram(self.id_shader)

        projecao = glm.ortho(-proporcao, proporcao, -1.0, 1.0, -1.0, 1.0)
        visao = glm.mat4(1.0)
        posicao_camera = glm.vec3(0, 0, 1)
        glUniformMatrix4fv(self.locais["projection"], 1, GL_FALSE, glm.value_ptr(projecao))
        glUniformMatrix4fv(self.locais["view"], 1, GL_FALSE, glm.value_ptr(visao))
        glUniform3f(self.locais["lightColor"], 1, 1, 1)
        glUniform3f(self.locais["lightPos"], 0, 14, 0)
        glUniform3fv(self.locais["viewPos"], 1, glm.value_ptr(posicao_camera))

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.desenhar_cubo(glm.vec3(0, 0, 0.0), glm.vec3(proporcao, 1.0, 0.02), (0.0, 0.75, 0.2))

        self.desenhar_cubo(glm.vec3(0, 0, 0.01), glm.vec3(min(proporcao, 1.2) * 0.65, 0.55, 0.02), (0.06, 0.12, 0.06))

        if self.vencedor_time == 0:
            numero = 1
        elif self.vencedor_time == 1:
            numero = 2
        else:
            numero = 0

        self._desenhar_numero_7_segmentos(numero, glm.vec3(0, 0, 0.03), 0.60, (0.95, 0.95, 0.95))

        glEnable(GL_DEPTH_TEST)

    def _reiniciar_estado_partida(self):
        """Reseta recursos da partida e sincroniza a câmera para o início."""
        self._partida_finalizada = False
        self.campeoes = {}
        self.campeoes = {}
        self.pontos_time = [
            {"esquerda": 0, "direita": 0, "muro": 0},
            {"esquerda": 0, "direita": 0, "muro": 0},
        ]
        self.vida_muro_time = [0, 0]
        self.moedas_time = [10, 10]
        self.jogador_turno = 0
        self.fase_turno = "roleta"
        self.roleta_girando = False
        self.tempo_roleta = 0.0
        self.resultados_roleta = []
        self._aplicar_camera_turno()
        self._registrar_evento("Partida reiniciada (turno=0, fase=roleta)")

    def _aplicar_camera_turno(self):
        """Posiciona a câmera do ponto de vista do jogador do turno atual."""
        if self.jogador_turno == 0:
            self.angulo_camera = 0.0
            self.deslocamento_frente_camera = 8.0
        else:
            self.angulo_camera = math.pi
            self.deslocamento_frente_camera = 8.0

    def _recursos_time(self, time: int):
        """Retorna posições/rotação associadas a um time (0/1) para desenhar objetos."""
        if time == 0:
            return {
                "pos_saco": self.pos_saco_vermelho,
                "pos_barreira": self.pos_barreira_vermelha,
                "rotacao_barreira": 0,
                "pos_gol": self.pos_gol_vermelho,
            }
        return {
            "pos_saco": self.pos_saco_azul,
            "pos_barreira": self.pos_barreira_azul,
            "rotacao_barreira": 180,
            "pos_gol": self.pos_gol_azul,
        }

    def _indice_jogador_time_lado(self, time: int, lado: int) -> int:
        """Mapeia (time, lado) -> índice do jogador no array self.jogadores."""
        return self._slots_jogadores_time[time][lado]

    def _iniciar_estado_campeao(self, tipo_campeao: str):
        """Cria o dicionário de atributos do campeão (custos/danos/regras)."""
        if tipo_campeao == "tigre":
            return {
                "tipo": "tigre",
                "custo_ataque": 5,
                "dano_ataque": 3,
                "custo_roubo": None,
                "quantidade_roubo": 0,
                "custo_evoluir": 8,
                "quantidade_evolucoes": 0,
                "ignorar_muro": False,
            }
        if tipo_campeao == "macaco":
            return {
                "tipo": "macaco",
                "custo_ataque": 5,
                "dano_ataque": 1,
                "custo_roubo": 7,
                "quantidade_roubo": 1,
                "custo_evoluir": 8,
                "quantidade_evolucoes": 0,
                "ignorar_muro": True,
            }
        if tipo_campeao == "panda":
            return {
                "tipo": "panda",
                "custo_ataque": 5,
                "dano_ataque": 3,
                "custo_roubo": 3,
                "quantidade_roubo": 2,
                "custo_evoluir": 8,
                "quantidade_evolucoes": 0,
                "ignorar_muro": False,
            }
        return {
            "tipo": "dragao",
            "custo_ataque": 5,
            "dano_ataque": 1,
            "custo_roubo": None,
            "quantidade_roubo": 0,
            "custo_evoluir": 8,
            "quantidade_evolucoes": 0,
            "ignorar_muro": True,
        }

    def _iniciar_giro_roleta(self):
        """Inicia a animação/temporização do giro da roleta."""
        self.roleta_girando = True
        self.tempo_roleta = 0.0
        self.resultados_roleta = []

    def _finalizar_roleta(self):
        """
        Conclui a roleta: sorteia 5 resultados e adiciona pontos ao jogador do turno.

        Os resultados são guardados em self.resultados_roleta para serem desenhados no tablet 3D.
        """
        cor_esquerda = self.jogadores[self._indice_jogador_time_lado(self.jogador_turno, 0)]["cor"]
        cor_direita = self.jogadores[self._indice_jogador_time_lado(self.jogador_turno, 1)]["cor"]
        cor_muro = (0.55, 0.55, 0.55)

        resultados = []
        for _ in range(5):
            categoria = random.randint(0, 2)
            if categoria == 0:
                self.pontos_time[self.jogador_turno]["esquerda"] += 1
                resultados.append(("esquerda", cor_esquerda))
            elif categoria == 1:
                self.pontos_time[self.jogador_turno]["direita"] += 1
                resultados.append(("direita", cor_direita))
            else:
                self.pontos_time[self.jogador_turno]["muro"] += 1
                resultados.append(("muro", cor_muro))

        self.resultados_roleta = resultados
        self.fase_turno = "acao"
        contagem = {"esquerda": 0, "direita": 0, "muro": 0}
        for categoria, _ in resultados:
            if categoria in contagem:
                contagem[categoria] += 1
        self._registrar_evento(
            "Roleta finalizada "
            f"(turno={self.jogador_turno} +E={contagem['esquerda']} +D={contagem['direita']} +M={contagem['muro']}) | "
            f"{self._resumo_time(self.jogador_turno)}"
        )

    def _pode_roubar_com_muro(self, estado_campeao) -> bool:
        """Regra especial: alguns campeões conseguem roubar mesmo com muro ativo."""
        return estado_campeao["tipo"] == "macaco"

    def _executar_ataque(self, lado: int) -> bool:
        """Executa ataque do lado (0=esquerda, 1=direita) do time do turno."""
        atacante = self.jogador_turno
        defensor = 1 - atacante
        chave_pool = "esquerda" if lado == 0 else "direita"
        pontos = self.pontos_time[atacante][chave_pool]
        campeao = self.campeoes.get(self._indice_jogador_time_lado(atacante, lado))
        if campeao is None:
            return False
        if pontos < campeao["custo_ataque"]:
            return False

        self.pontos_time[atacante][chave_pool] -= campeao["custo_ataque"]
        dano = campeao["dano_ataque"]

        if campeao["ignorar_muro"]:
            self.moedas_time[defensor] = max(0, self.moedas_time[defensor] - dano)
            return True

        if self.vida_muro_time[defensor] > 0:
            self.vida_muro_time[defensor] = max(0, self.vida_muro_time[defensor] - dano)
            return True

        if campeao["tipo"] in ("tigre", "panda"):
            self.moedas_time[defensor] = max(0, self.moedas_time[defensor] - dano)
            return True

        self.moedas_time[defensor] = max(0, self.moedas_time[defensor] - dano)
        return True

    def _executar_roubo(self, lado: int) -> bool:
        """Executa roubo do lado (0=esquerda, 1=direita) do time do turno."""
        atacante = self.jogador_turno
        defensor = 1 - atacante
        chave_pool = "esquerda" if lado == 0 else "direita"
        campeao = self.campeoes.get(self._indice_jogador_time_lado(atacante, lado))
        if campeao is None:
            return False
        if campeao["custo_roubo"] is None:
            return False
        if self.pontos_time[atacante][chave_pool] < campeao["custo_roubo"]:
            return False

        if self.vida_muro_time[defensor] > 0 and not (campeao["ignorar_muro"] or self._pode_roubar_com_muro(campeao)):
            return False

        quantidade = campeao["quantidade_roubo"]
        if quantidade <= 0:
            return False

        self.pontos_time[atacante][chave_pool] -= campeao["custo_roubo"]
        roubado = min(quantidade, self.moedas_time[defensor])
        self.moedas_time[defensor] -= roubado
        self.moedas_time[atacante] += roubado
        return True

    def _executar_evolucao(self, lado: int) -> bool:
        """Evolui o campeão do lado escolhido, consumindo pontos e aumentando atributos."""
        atacante = self.jogador_turno
        chave_pool = "esquerda" if lado == 0 else "direita"
        campeao = self.campeoes.get(self._indice_jogador_time_lado(atacante, lado))
        if campeao is None:
            return False
        if self.pontos_time[atacante][chave_pool] < campeao["custo_evoluir"]:
            return False

        self.pontos_time[atacante][chave_pool] -= campeao["custo_evoluir"]
        campeao["quantidade_evolucoes"] += 1
        if campeao["tipo"] == "macaco":
            campeao["quantidade_roubo"] += 1
        elif campeao["tipo"] == "panda":
            campeao["dano_ataque"] += 1
            campeao["quantidade_roubo"] += 1
        else:
            campeao["dano_ataque"] += 1
        return True

    def _executar_defesa(self) -> bool:
        """Converte pontos de muro em vida do muro do time do turno."""
        time = self.jogador_turno
        pontos_muro = self.pontos_time[time]["muro"]
        if pontos_muro <= 0:
            return False
        self.pontos_time[time]["muro"] = 0
        self.vida_muro_time[time] = min(40, self.vida_muro_time[time] + pontos_muro)
        return True

    def _tem_alguma_acao_para_time(self, time: int) -> bool:
        """
        Verifica se o time ainda tem alguma ação possível na fase de ação.

        Usado para pular automaticamente o turno quando não há ações possíveis.
        """
        if self.pontos_time[time]["muro"] > 0:
            return True

        defensor = 1 - time

        for lado in (0, 1):
            chave_pool = "esquerda" if lado == 0 else "direita"
            pontos = self.pontos_time[time][chave_pool]
            campeao = self.campeoes.get(self._indice_jogador_time_lado(time, lado))
            if campeao is None:
                continue

            if pontos >= campeao["custo_ataque"]:
                return True

            if pontos >= campeao["custo_evoluir"]:
                return True

            if campeao["custo_roubo"] is not None and pontos >= campeao["custo_roubo"]:
                if campeao["quantidade_roubo"] > 0 and self.moedas_time[defensor] > 0:
                    if self.vida_muro_time[defensor] == 0 or campeao["ignorar_muro"] or self._pode_roubar_com_muro(campeao):
                        return True

        return False

    def _finalizar_turno(self):
        """Passa o turno para o outro jogador e reseta a fase para nova roleta."""
        turno_anterior = self.jogador_turno
        self.jogador_turno = 1 - self.jogador_turno
        self.fase_turno = "roleta"
        self.resultados_roleta = []
        self._aplicar_camera_turno()
        self._registrar_evento(f"Turno finalizado: {turno_anterior} -> {self.jogador_turno} (fase=roleta)")

    def iniciar_gl(self):
        """Inicializa OpenGL, carrega shaders e cria as malhas."""
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.82, 0.86, 0.91, 1.0)

        aqui = os.path.dirname(os.path.abspath(__file__))
        diretorio_shaders = os.path.join(aqui, "shaders")

        self.id_shader = criar_programa_de_arquivos(
            os.path.join(diretorio_shaders, "vertexShader.glsl"),
            os.path.join(diretorio_shaders, "fragmentShader.glsl"),
        )

        self.locais["projection"] = glGetUniformLocation(self.id_shader, "projection")
        self.locais["view"] = glGetUniformLocation(self.id_shader, "view")
        self.locais["model"] = glGetUniformLocation(self.id_shader, "model")
        self.locais["objectColor"] = glGetUniformLocation(self.id_shader, "objectColor")
        self.locais["lightColor"] = glGetUniformLocation(self.id_shader, "lightColor")
        self.locais["lightPos"] = glGetUniformLocation(self.id_shader, "lightPos")
        self.locais["viewPos"] = glGetUniformLocation(self.id_shader, "viewPos")

        self.cubo = MalhaCubo()
        self.esfera = MalhaEsfera()
        self.barreira = MalhaBarreiraCurva()

    def atualizar_framebuffer(self, janela, largura: int, altura: int):
        """Atualiza o viewport quando a janela é redimensionada."""
        self.resolucao = [largura, altura]
        glViewport(0, 0, largura, altura)
        self._registrar_evento(f"Janela redimensionada: {largura}x{altura}")

    def _tecla_pressionada(self, janela, tecla: int) -> bool:
        """Detecta borda de subida (pressionou agora, não estava pressionada antes)."""
        tecla_glfw = tecla
        esta_pressionada = glfw.get_key(janela, tecla_glfw) == glfw.PRESS
        estava_pressionada = self._estado_tecla_anterior.get(tecla_glfw, False)
        self._estado_tecla_anterior[tecla_glfw] = esta_pressionada
        if esta_pressionada and not estava_pressionada:
            if self.modo == "jogando":
                self._registrar_evento(
                    f"Tecla: {self._nome_tecla(tecla_glfw)} (modo=jogando turno={self.jogador_turno} fase={self.fase_turno})"
                )
            else:
                self._registrar_evento(f"Tecla: {self._nome_tecla(tecla_glfw)} (modo=selecao)")
        return esta_pressionada and not estava_pressionada

    def atualizar(self, janela, delta_tempo: float):
        """
        Atualiza a lógica do jogo (entrada + estado).
        """
        if self._tecla_pressionada(janela, glfw.KEY_ESCAPE):
            self._registrar_evento("Saindo (ESC)")
            glfw.set_window_should_close(janela, True)
            return

        if self.modo == "selecao":
            # Navegação na lista de campeões.
            if self._tecla_pressionada(janela, glfw.KEY_LEFT):
                self.indice_campeao_selecionado = (self.indice_campeao_selecionado - 1) % len(self.opcoes_campeoes)
                selecionado = self.opcoes_campeoes[self.indice_campeao_selecionado]
                self._registrar_evento(f"Seleção: {selecionado['nome']} (indice={self.indice_campeao_selecionado})")
            if self._tecla_pressionada(janela, glfw.KEY_RIGHT):
                self.indice_campeao_selecionado = (self.indice_campeao_selecionado + 1) % len(self.opcoes_campeoes)
                selecionado = self.opcoes_campeoes[self.indice_campeao_selecionado]
                self._registrar_evento(f"Seleção: {selecionado['nome']} (indice={self.indice_campeao_selecionado})")

            for i in range(4):
                if self._tecla_pressionada(janela, glfw.KEY_1 + i):
                    self.indice_campeao_selecionado = i
                    selecionado = self.opcoes_campeoes[self.indice_campeao_selecionado]
                    self._registrar_evento(f"Seleção: {selecionado['nome']} (tecla={i+1})")

            # Desfazer seleção atual (volta slot/time).
            if self._tecla_pressionada(janela, glfw.KEY_BACKSPACE):
                if self._time_selecionando != 0 or self._slot_selecionando != 0:
                    if self._slot_selecionando == 1:
                        self._slot_selecionando = 0
                        self._indices_campeoes_escolhidos[self._time_selecionando][1] = None
                        self._registrar_evento(f"Desfazer: voltou para slot=0 (time={self._time_selecionando})")
                    else:
                        self._time_selecionando = 0
                        self._slot_selecionando = 1
                        self._indices_campeoes_escolhidos[1][0] = None
                        self._registrar_evento("Desfazer: voltou para time=0 slot=1")

            # Confirmar escolha do campeão atual para o slot selecionado.
            if self._tecla_pressionada(janela, glfw.KEY_ENTER) or self._tecla_pressionada(janela, glfw.KEY_SPACE):
                ja_escolhido = any(
                    self.indice_campeao_selecionado == idx
                    for idx in self._indices_campeoes_escolhidos[self._time_selecionando]
                    if idx is not None
                )
                if ja_escolhido:
                    selecionado = self.opcoes_campeoes[self.indice_campeao_selecionado]
                    self._registrar_evento(
                        f"Escolha ignorada (já escolhido no time atual): {selecionado['nome']} (time={self._time_selecionando})"
                    )
                    return

                self._indices_campeoes_escolhidos[self._time_selecionando][self._slot_selecionando] = (
                    self.indice_campeao_selecionado
                )
                escolhido = self.opcoes_campeoes[self.indice_campeao_selecionado]
                self._registrar_evento(
                    f"Escolhido: {escolhido['nome']} (time={self._time_selecionando} slot={self._slot_selecionando})"
                )
                if self._time_selecionando == 0 and self._slot_selecionando == 0:
                    self._slot_selecionando = 1
                    self._registrar_evento("Avançar seleção: time=0 slot=1")
                elif self._time_selecionando == 0 and self._slot_selecionando == 1:
                    self._time_selecionando = 1
                    self._slot_selecionando = 0
                    self._registrar_evento("Avançar seleção: time=1 slot=0")
                elif self._time_selecionando == 1 and self._slot_selecionando == 0:
                    self._slot_selecionando = 1
                    self._registrar_evento("Avançar seleção: time=1 slot=1")
                else:
                    # Quando os 4 campeões foram escolhidos, configura as cores/estados e inicia a partida.
                    escolhido_p1_a = self.opcoes_campeoes[self._indices_campeoes_escolhidos[0][0]]
                    escolhido_p1_b = self.opcoes_campeoes[self._indices_campeoes_escolhidos[0][1]]
                    escolhido_p2_a = self.opcoes_campeoes[self._indices_campeoes_escolhidos[1][0]]
                    escolhido_p2_b = self.opcoes_campeoes[self._indices_campeoes_escolhidos[1][1]]
                    self._registrar_evento(
                        "Seleção concluída | "
                        f"P1={escolhido_p1_a['nome']}/{escolhido_p1_b['nome']} "
                        f"P2={escolhido_p2_a['nome']}/{escolhido_p2_b['nome']}"
                    )

                    self._reiniciar_estado_partida()
                    self.jogadores[self._slots_jogadores_time[0][0]]["cor"] = escolhido_p1_a["cor"]
                    self.jogadores[self._slots_jogadores_time[0][1]]["cor"] = escolhido_p1_b["cor"]
                    self.jogadores[self._slots_jogadores_time[1][0]]["cor"] = escolhido_p2_a["cor"]
                    self.jogadores[self._slots_jogadores_time[1][1]]["cor"] = escolhido_p2_b["cor"]

                    self.campeoes[self._slots_jogadores_time[0][0]] = self._iniciar_estado_campeao(escolhido_p1_a["tipo"])
                    self.campeoes[self._slots_jogadores_time[0][1]] = self._iniciar_estado_campeao(escolhido_p1_b["tipo"])
                    self.campeoes[self._slots_jogadores_time[1][0]] = self._iniciar_estado_campeao(escolhido_p2_a["tipo"])
                    self.campeoes[self._slots_jogadores_time[1][1]] = self._iniciar_estado_campeao(escolhido_p2_b["tipo"])

                    self.modo = "jogando"
                    self._registrar_evento("Modo alterado: selecao -> jogando")
                    return

            return

        if self.modo == "jogando":
            # Voltar para a seleção (recomeçar).
            if self._tecla_pressionada(janela, glfw.KEY_BACKSPACE):
                self._registrar_evento("Voltar para seleção (BACKSPACE)")
                self.modo = "selecao"
                self._time_selecionando = 0
                self._slot_selecionando = 0
                self._indices_campeoes_escolhidos = [[None, None], [None, None]]
                return

            # Condição de término: um dos lados ficou sem moedas.
            if self.moedas_time[0] <= 0 or self.moedas_time[1] <= 0:
                if not self._partida_finalizada:
                    if self.moedas_time[0] <= 0 and self.moedas_time[1] <= 0:
                        vencedor = None
                    else:
                        vencedor = 1 if self.moedas_time[0] <= 0 else 0
                    self.vencedor_time = vencedor
                    self._registrar_evento(
                        f"Fim de partida: vencedor={'empate' if vencedor is None else f'time {vencedor}'} | {self._resumo_time(0)} | {self._resumo_time(1)}"
                    )
                    self._partida_finalizada = True
                return

            # Fase visual do giro (mostra cores alternando no tablet).
            if self.roleta_girando:
                self.tempo_roleta += delta_tempo
                cor_esquerda = self.jogadores[self._indice_jogador_time_lado(self.jogador_turno, 0)]["cor"]
                cor_direita = self.jogadores[self._indice_jogador_time_lado(self.jogador_turno, 1)]["cor"]
                cor_muro = (0.55, 0.55, 0.55)
                cores = [cor_esquerda, cor_direita, cor_muro]
                self.resultados_roleta = [("giro", cores[random.randint(0, 2)]) for _ in range(5)]
                if self.tempo_roleta >= self.duracao_giro_roleta:
                    self.roleta_girando = False
                    self._finalizar_roleta()

            if not self.roleta_girando:
                # Alterna entre roleta e fase de ação.
                if self.fase_turno == "roleta":
                    self._registrar_evento(f"Iniciar roleta (turno={self.jogador_turno})")
                    self._iniciar_giro_roleta()
                elif self.fase_turno == "acao":
                    if self._tecla_pressionada(janela, glfw.KEY_P) or self._tecla_pressionada(janela, glfw.KEY_0):
                        self._registrar_evento(f"Ação solicitada: pular turno (turno={self.jogador_turno})")
                        self._finalizar_turno()
                        return

                    action_done = False
                    acao_tentada = None
                    # Mapeamento das teclas 1..7 para ações.
                    if self._tecla_pressionada(janela, glfw.KEY_1):
                        acao_tentada = "ataque esquerda"
                        self._registrar_evento(f"Ação solicitada: {acao_tentada} (turno={self.jogador_turno})")
                        action_done = self._executar_ataque(0)
                    elif self._tecla_pressionada(janela, glfw.KEY_2):
                        acao_tentada = "ataque direita"
                        self._registrar_evento(f"Ação solicitada: {acao_tentada} (turno={self.jogador_turno})")
                        action_done = self._executar_ataque(1)
                    elif self._tecla_pressionada(janela, glfw.KEY_3):
                        acao_tentada = "evoluir esquerda"
                        self._registrar_evento(f"Ação solicitada: {acao_tentada} (turno={self.jogador_turno})")
                        action_done = self._executar_evolucao(0)
                    elif self._tecla_pressionada(janela, glfw.KEY_4):
                        acao_tentada = "evoluir direita"
                        self._registrar_evento(f"Ação solicitada: {acao_tentada} (turno={self.jogador_turno})")
                        action_done = self._executar_evolucao(1)
                    elif self._tecla_pressionada(janela, glfw.KEY_5):
                        acao_tentada = "roubo esquerda"
                        self._registrar_evento(f"Ação solicitada: {acao_tentada} (turno={self.jogador_turno})")
                        action_done = self._executar_roubo(0)
                    elif self._tecla_pressionada(janela, glfw.KEY_6):
                        acao_tentada = "roubo direita"
                        self._registrar_evento(f"Ação solicitada: {acao_tentada} (turno={self.jogador_turno})")
                        action_done = self._executar_roubo(1)
                    elif self._tecla_pressionada(janela, glfw.KEY_7):
                        acao_tentada = "defesa/muro"
                        self._registrar_evento(f"Ação solicitada: {acao_tentada} (turno={self.jogador_turno})")
                        action_done = self._executar_defesa()

                    if action_done:
                        self._registrar_evento(
                            "Ação executada com sucesso | "
                            f"{self._resumo_time(0)} | {self._resumo_time(1)}"
                        )
                        self._finalizar_turno()
                    else:
                        if acao_tentada is not None:
                            self._registrar_evento(
                                f"Ação falhou: {acao_tentada} (requisitos não atendidos) | "
                                f"{self._resumo_time(self.jogador_turno)}"
                            )

    def _definir_uniformes_objeto(self, matriz_modelo: glm.mat4, cor):
        """Atualiza uniforms do objeto atual (matriz de modelo e cor)."""
        glUniformMatrix4fv(self.locais["model"], 1, GL_FALSE, glm.value_ptr(matriz_modelo))
        glUniform3f(self.locais["objectColor"], *cor)

    def desenhar_cubo(self, posicao: glm.vec3, escala: glm.vec3, cor, rotacao_y: float = 0.0):
        """Desenha um cubo com transformação e cor."""
        model = glm.mat4(1.0)
        model = glm.translate(model, posicao)
        model = glm.rotate(model, glm.radians(rotacao_y), glm.vec3(0, 1, 0))
        model = glm.scale(model, escala)
        self._definir_uniformes_objeto(model, cor)
        self.cubo.desenhar()

    def desenhar_esfera(self, posicao: glm.vec3, escala: float, cor):
        """Desenha uma esfera com transformação e cor."""
        model = glm.mat4(1.0)
        model = glm.translate(model, posicao)
        model = glm.scale(model, glm.vec3(escala))
        self._definir_uniformes_objeto(model, cor)
        self.esfera.desenhar()

    def desenhar_barreira(self, posicao: glm.vec3, cor, rotacao_y: float = 0.0):
        """Desenha a barreira curva (muro) com rotação e cor."""
        model = glm.mat4(1.0)
        model = glm.translate(model, posicao)
        model = glm.rotate(model, glm.radians(rotacao_y), glm.vec3(0, 1, 0))
        self._definir_uniformes_objeto(model, cor)
        self.barreira.desenhar()

    def _desenhar_tablet_e_roleta(self):
        """Desenha o tablet 3D com os 5 resultados da roleta (ou estado de giro)."""
        time = self.jogador_turno
        z_atras = -12.0 if time == 0 else 12.0
        z_direcao_camera = 0.35 if time == 0 else -0.35

        cor_tablet = (0.12, 0.12, 0.14)
        cor_moldura = (0.25, 0.25, 0.27)
        self.desenhar_cubo(glm.vec3(0, 2.6, z_atras), glm.vec3(5.0, 2.8, 0.18), cor_moldura)
        self.desenhar_cubo(
            glm.vec3(0, 2.6, z_atras + z_direcao_camera * 0.15),
            glm.vec3(4.6, 2.5, 0.12),
            cor_tablet,
        )

        x_pinos = [-1.6, -0.8, 0.0, 0.8, 1.6]
        y = 2.6
        z = z_atras + z_direcao_camera

        if self.resultados_roleta:
            cores_pinos = [pip[1] for pip in self.resultados_roleta[:5]]
        else:
            cores_pinos = [(0.18, 0.18, 0.2)] * 5

        for i in range(5):
            self.desenhar_cubo(glm.vec3(x_pinos[i], y, z), glm.vec3(0.28, 0.28, 0.08), cores_pinos[i])

    def _desenhar_colunas_recursos(self):
        """Desenha colunas que representam pontos de ataque (esq/dir) e pontos de muro."""
        cor_muro = (0.55, 0.55, 0.55)
        for time in (0, 1):
            z_dir = -1.0 if time == 0 else 1.0
            indice_esquerda = self._indice_jogador_time_lado(time, 0)
            indice_direita = self._indice_jogador_time_lado(time, 1)

            pontos_esquerda = self.pontos_time[time]["esquerda"]
            pontos_direita = self.pontos_time[time]["direita"]
            pontos_muro = self.pontos_time[time]["muro"]

            pos_esquerda = self.jogadores[indice_esquerda]["posicao"] + glm.vec3(0, 0.0, z_dir * 1.4)
            pos_direita = self.jogadores[indice_direita]["posicao"] + glm.vec3(0, 0.0, z_dir * 1.4)
            pos_barreira = self._recursos_time(time)["pos_barreira"] + glm.vec3(0, 0.0, z_dir * 0.9)

            h_esquerda = 0.12 + min(pontos_esquerda, 30) * 0.08
            h_direita = 0.12 + min(pontos_direita, 30) * 0.08
            h_muro = 0.12 + min(pontos_muro, 30) * 0.08

            self.desenhar_cubo(
                glm.vec3(pos_esquerda.x, h_esquerda / 2.0, pos_esquerda.z),
                glm.vec3(0.18, h_esquerda, 0.18),
                self.jogadores[indice_esquerda]["cor"],
            )
            self.desenhar_cubo(
                glm.vec3(pos_direita.x, h_direita / 2.0, pos_direita.z),
                glm.vec3(0.18, h_direita, 0.18),
                self.jogadores[indice_direita]["cor"],
            )
            self.desenhar_cubo(glm.vec3(pos_barreira.x, h_muro / 2.0, pos_barreira.z), glm.vec3(0.18, h_muro, 0.18), cor_muro)

    def _desenhar_forca_muro(self):
        """Desenha uma barra acima da barreira indicando a vida do muro do time."""
        for time in (0, 1):
            vida_muro = self.vida_muro_time[time]
            if vida_muro <= 0:
                continue
            recursos = self._recursos_time(time)
            direcao_z = -1.0 if time == 0 else 1.0
            altura = 0.12 + min(vida_muro, 40) * 0.05
            posicao = recursos["pos_barreira"] + glm.vec3(0, altura / 2.0 + 0.45, direcao_z * 0.2)
            self.desenhar_cubo(glm.vec3(posicao.x, posicao.y, posicao.z), glm.vec3(0.5, altura, 0.5), (0.55, 0.55, 0.55))

    def _iniciar_cena(self, visao: glm.mat4, projecao: glm.mat4, posicao_camera: glm.vec3):
        """Configura a cena (limpa buffers, usa shader e define uniforms globais)."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.id_shader)

        glUniformMatrix4fv(self.locais["projection"], 1, GL_FALSE, glm.value_ptr(projecao))
        glUniformMatrix4fv(self.locais["view"], 1, GL_FALSE, glm.value_ptr(visao))
        glUniform3f(self.locais["lightColor"], 1, 1, 1)
        glUniform3f(self.locais["lightPos"], 0, 14, 0)
        glUniform3fv(self.locais["viewPos"], 1, glm.value_ptr(posicao_camera))

    def _renderizar_selecao_campeoes(self, janela, proporcao: float):
        """Renderiza a tela 3D de seleção de campeões."""
        posicao_camera = glm.vec3(0, 8.5, 18)
        visao = glm.lookAt(posicao_camera, glm.vec3(0, 0.5, 0), glm.vec3(0, 1, 0))
        projecao = glm.perspective(glm.radians(35), proporcao, 0.1, 100.0)
        self._iniciar_cena(visao, projecao, posicao_camera)

        self.desenhar_cubo(glm.vec3(0, -0.15, 0), glm.vec3(10, 0.1, 6), (0.88, 0.88, 0.90))

        cor_pedestal = (0.55, 0.55, 0.55)
        cor_destaque = (1.0, 0.9, 0.15)
        cor_escolhido = (0.9, 0.9, 0.95)
        cor_escolhido_outro = (0.82, 0.82, 0.86)

        posicoes_x = [-6.0, -2.0, 2.0, 6.0]
        for i, option in enumerate(self.opcoes_campeoes[:4]):
            x = posicoes_x[i]
            is_chosen = i in self._indices_campeoes_escolhidos[self._time_selecionando]
            is_other_chosen = i in self._indices_campeoes_escolhidos[1 - self._time_selecionando]
            is_selected = i == self.indice_campeao_selecionado
            pedestal = cor_pedestal
            escala_esfera = 0.6
            if is_chosen:
                pedestal = cor_escolhido
                escala_esfera = 0.68
            elif is_other_chosen:
                pedestal = cor_escolhido_outro
                escala_esfera = 0.64
            if is_selected:
                pedestal = cor_destaque
                escala_esfera = 0.75
            self.desenhar_cubo(glm.vec3(x, 0.25, 0), glm.vec3(1.2, 0.25, 1.2), pedestal)
            self.desenhar_esfera(glm.vec3(x, 0.85, 0), escala_esfera, option["cor"])

        y_previa = 0.25
        z_previa = -2.6
        cor_pedestal_previa = (0.6, 0.6, 0.62)
        cor_vazia = (0.75, 0.75, 0.78)
        posicoes_previas = [
            (-3.0, 0, 0),
            (-1.0, 0, 1),
            (1.0, 1, 0),
            (3.0, 1, 1),
        ]
        for x, time, posicao in posicoes_previas:
            esta_no_slot_atual = time == self._time_selecionando and posicao == self._slot_selecionando
            pedestal = cor_destaque if esta_no_slot_atual else cor_pedestal_previa
            idx = self._indices_campeoes_escolhidos[time][posicao]
            cor = self.opcoes_campeoes[idx]["cor"] if idx is not None else cor_vazia
            self.desenhar_cubo(glm.vec3(x, y_previa, z_previa), glm.vec3(0.9, 0.22, 0.9), pedestal)
            self.desenhar_esfera(glm.vec3(x, y_previa + 0.55, z_previa), 0.5, cor)

        glUseProgram(0)

    def renderizar(self, janela):
        """Renderiza a cena atual (seleção ou partida)."""
        largura, altura = glfw.get_framebuffer_size(janela)
        if altura == 0:
            return

        proporcao = largura / altura

        if self.modo == "selecao":
            self._renderizar_selecao_campeoes(janela, proporcao)
            self._renderizar_placar_superior(proporcao)
            return
        if self._partida_finalizada:
            self._renderizar_tela_vitoria(proporcao)
            return

        frente_x = -math.sin(self.angulo_camera)
        frente_z = -math.cos(self.angulo_camera)
        foco_camera = glm.vec3(frente_x * self.deslocamento_frente_camera, 0, frente_z * self.deslocamento_frente_camera)
        posicao_camera = foco_camera + glm.vec3(
            math.sin(self.angulo_camera) * self.distancia_camera,
            25,
            math.cos(self.angulo_camera) * self.distancia_camera,
        )

        visao = glm.lookAt(posicao_camera, foco_camera, glm.vec3(0, 1, 0))
        projecao = glm.perspective(glm.radians(25), proporcao, 0.1, 100.0)

        self._iniciar_cena(visao, projecao, posicao_camera)

        centro_tabuleiro_z = (self.tabuleiro_comprimento_baixo - self.tabuleiro_comprimento_cima) / 2.0
        metade_total_tabuleiro = (self.tabuleiro_comprimento_baixo + self.tabuleiro_comprimento_cima) / 2.0

        self.desenhar_cubo(
            glm.vec3(0, -0.15, centro_tabuleiro_z),
            glm.vec3(self.tabuleiro_meia_largura, 0.1, metade_total_tabuleiro),
            (0.88, 0.88, 0.90),
        )

        cor_borda = (0.55, 0.55, 0.55)
        self.desenhar_cubo(
            glm.vec3(0, 0.35, -self.tabuleiro_comprimento_cima),
            glm.vec3(self.tabuleiro_meia_largura + 0.2, 0.4, 0.2),
            cor_borda,
        )
        self.desenhar_cubo(
            glm.vec3(0, 0.35, self.tabuleiro_comprimento_baixo),
            glm.vec3(self.tabuleiro_meia_largura + 0.2, 0.4, 0.2),
            cor_borda,
        )
        self.desenhar_cubo(glm.vec3(-self.tabuleiro_meia_largura, 0.35, centro_tabuleiro_z), glm.vec3(0.2, 0.4, metade_total_tabuleiro), cor_borda)
        self.desenhar_cubo(glm.vec3(self.tabuleiro_meia_largura, 0.35, centro_tabuleiro_z), glm.vec3(0.2, 0.4, metade_total_tabuleiro), cor_borda)

        boost_azul = min(self.vida_muro_time[1], 40) * 0.008
        boost_vermelho = min(self.vida_muro_time[0], 40) * 0.008
        self.desenhar_barreira(self.pos_barreira_azul, (0.45 + boost_azul, 0.45 + boost_azul, 0.45 + boost_azul), 180)
        self.desenhar_barreira(self.pos_barreira_vermelha, (0.45 + boost_vermelho, 0.45 + boost_vermelho, 0.45 + boost_vermelho), 0)

        self.desenhar_cubo(self.pos_gol_azul, glm.vec3(0.9, 0.05, 0.9), (0.2, 0.75, 1.0), 45)
        self.desenhar_cubo(self.pos_gol_vermelho, glm.vec3(0.9, 0.05, 0.9), (1.0, 0.25, 0.25), 45)

        for jogador in self.jogadores:
            self.desenhar_esfera(jogador["posicao"], 0.6, jogador["cor"])

        base_altura = 0.22
        altura_azul = base_altura + min(self.moedas_time[1], 60) * 0.02
        altura_vermelho = base_altura + min(self.moedas_time[0], 60) * 0.02
        self.desenhar_cubo(
            self.pos_saco_azul + glm.vec3(0, altura_azul / 2.0 - 0.15, 0),
            glm.vec3(0.45, altura_azul, 0.45),
            (1.0, 0.9, 0.15),
        )
        self.desenhar_cubo(
            self.pos_saco_vermelho + glm.vec3(0, altura_vermelho / 2.0 - 0.15, 0),
            glm.vec3(0.45, altura_vermelho, 0.45),
            (1.0, 0.65, 0.05),
        )

        self._desenhar_colunas_recursos()
        self._desenhar_forca_muro()
        self._desenhar_tablet_e_roleta()

        self._renderizar_placar_superior(proporcao)
        glUseProgram(0)
