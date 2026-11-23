import time
from robo import Robo

# Sensores IR: esquerda para direita
Y_CANAIS = [26.6, 8.9, -8.9, -26.6]
PRETO = 50

# Seguidor PD
VELOCIDADE_BASE = 30
KP = 1.6
KD = 3.0
REDUCAO_ERRO = 0.4
VELOCIDADE_MINIMA = 12
VELOCIDADE_MAXIMA = 65

# Curvas e recuperacao
LIMITE_CURVA = 10
LIMITE_RETA = 6
TEMPO_RETA = 0.35
VELOCIDADE_GIRO = 28
TEMPO_GIRO_90 = 1.5
TEMPO_GIRO_180 = 3.0
TEMPO_ALINHAMENTO = 3.0
TEMPO_CENTRO = 0.15
LIMITE_CENTRO = 3

# Gap
VELOCIDADE_GAP = 30
TEMPO_MAX_GAP = 4.5

# Marcadores
COR_VERDE = "verde"
COR_VERMELHA = "vermelho"
IR_PRETOS_INTERSECAO = 2
LIMITE_ALINHAMENTO_VERDE = 8
LEITURAS_VERDE = 3
TEMPO_LIBERAR_VERDE = 0.30
TEMPO_RETA_ANTES_VERDE = 0.50

DISTANCIA_INTERSECAO = 70
VELOCIDADE_INTERSECAO = 30
ANGULO_CONVERSAO = 45
ANGULO_MEIA_VOLTA = 150
ANGULO_BUSCA = 110


def calcular_posicao(ir):
    pesos = [max(0, min(1, (100 - v) / 100)) for v in ir]
    intensidade = sum(pesos)

    if intensidade < 0.25:
        return None, intensidade

    posicao = sum(p * y for p, y in zip(pesos, Y_CANAIS)) / intensidade
    return posicao, intensidade


def controlar_pd(erro, erro_anterior):
    derivada = erro - erro_anterior
    return KP * erro + KD * derivada


def velocidades_motores(correcao, erro):
    velocidade = VELOCIDADE_BASE - REDUCAO_ERRO * abs(erro)
    velocidade = max(VELOCIDADE_MINIMA, min(VELOCIDADE_MAXIMA, velocidade))

    ve = max(-100, min(100, velocidade - correcao))
    vd = max(-100, min(100, velocidade + correcao))
    return ve, vd


def buscar_linha_girando(robo, direcao, tempo):
    inicio = time.monotonic()
    encontrou = False
    inicio_alinhamento = None
    inicio_centro = None

    while True:
        posicao, intensidade = calcular_posicao(robo.reflexao())

        if not encontrou:
            if time.monotonic() - inicio >= tempo:
                robo.para()
                return False, None

            if posicao is not None and intensidade >= 0.25:
                encontrou = True
                inicio_alinhamento = time.monotonic()

        if encontrou:
            if time.monotonic() - inicio_alinhamento >= TEMPO_ALINHAMENTO:
                robo.para()
                return False, None

            if posicao is None:
                inicio_centro = None
                if direcao == "DIREITA":
                    robo.anda(VELOCIDADE_GIRO, -VELOCIDADE_GIRO)
                else:
                    robo.anda(-VELOCIDADE_GIRO, VELOCIDADE_GIRO)

            elif abs(posicao) <= LIMITE_CENTRO:
                robo.para()
                if inicio_centro is None:
                    inicio_centro = time.monotonic()
                elif time.monotonic() - inicio_centro >= TEMPO_CENTRO:
                    return True, posicao

            else:
                inicio_centro = None
                if posicao > 0:
                    robo.anda(-VELOCIDADE_GIRO, VELOCIDADE_GIRO)
                else:
                    robo.anda(VELOCIDADE_GIRO, -VELOCIDADE_GIRO)

        elif direcao == "DIREITA":
            robo.anda(VELOCIDADE_GIRO, -VELOCIDADE_GIRO)
        else:
            robo.anda(-VELOCIDADE_GIRO, VELOCIDADE_GIRO)

        time.sleep(0.02)


def recuperar_linha(robo, ultima_posicao):
    if ultima_posicao > 0:
        primeira, segunda = "ESQUERDA", "DIREITA"
    else:
        primeira, segunda = "DIREITA", "ESQUERDA"

    tentativas = [
        (primeira, TEMPO_GIRO_90),
        (segunda, TEMPO_GIRO_180),
        (primeira, TEMPO_GIRO_90)
    ]

    for direcao, tempo in tentativas:
        encontrou, posicao = buscar_linha_girando(robo, direcao, tempo)
        if encontrou:
            return True, posicao

    robo.para()
    return False, None


def procurar_linha(robo, sentido, max_graus):
    z_inicial = robo.z()

    while abs(robo.z() - z_inicial) < max_graus:
        ir = robo.reflexao()

        if ir[1] < PRETO or ir[2] < PRETO:
            robo.para()
            return True

        robo.anda(-VELOCIDADE_GIRO * sentido, VELOCIDADE_GIRO * sentido)
        time.sleep(0.01)

    robo.para()
    return False


def tratar_verde(robo, esquerda, direita):
    if esquerda and direita:
        angulo = ANGULO_MEIA_VOLTA
        sentido = 1
    elif esquerda:
        angulo = ANGULO_CONVERSAO
        sentido = 1
    else:
        angulo = -ANGULO_CONVERSAO
        sentido = -1

    robo.anda_mm(DISTANCIA_INTERSECAO+25, vel=VELOCIDADE_INTERSECAO)
    robo.gira(angulo)

    encontrou = procurar_linha(robo, sentido, ANGULO_BUSCA)

    if not encontrou:
        encontrou = procurar_linha(robo, -sentido, ANGULO_BUSCA)

    if encontrou:
        robo.anda_mm(25, vel=-VELOCIDADE_INTERSECAO)
        return True

    return False


def atravessar_gap(robo):
    inicio = time.monotonic()
    tempo_minimo = 0.25

    robo.anda(VELOCIDADE_GAP, VELOCIDADE_GAP)

    while time.monotonic() - inicio < TEMPO_MAX_GAP:
        posicao, intensidade = calcular_posicao(robo.reflexao())
        tempo = time.monotonic() - inicio

        if (
            tempo >= tempo_minimo
            and posicao is not None
            and intensidade >= 0.25
        ):
            robo.para()
            return True, posicao

        robo.anda(VELOCIDADE_GAP, VELOCIDADE_GAP)
        time.sleep(0.02)

    robo.para()
    return False, None


def main():
    robo = Robo()

    erro_anterior = 0.0
    ultima_posicao = 0.0
    curva_detectada = False
    inicio_reta = None
    inicio_reta_estavel = None

    cores_anteriores = None
    verde_bloqueado = False
    inicio_sem_verde = None

    print("Aguardando inicio...")
    robo.espera_botao()
    print("Seguidor iniciado!")

    try:
        while True:
            cores = robo.cores()
            ir = robo.reflexao()

            # Chegada
            if cores.count(COR_VERMELHA) >= 2:
                print("Chegada!")
                robo.para()
                break

            # Aceita o verde somente na transicao de branco/preto/branco
            # para uma das sequencias de marcador.
            branco_anterior = cores_anteriores == ["branco", "preto", "branco"]

            verde_direita = (
                branco_anterior
                and cores == ["branco", "preto", "verde"]
            )

            verde_esquerda = (
                branco_anterior
                and cores == ["verde", "preto", "branco"]
            )

            verde_dos_dois_lados = (
                branco_anterior
                and cores == ["verde", "preto", "verde"]
            )

            algum_verde = (
                verde_esquerda
                or verde_direita
                or verde_dos_dois_lados
            )

            quantidade_pretos = sum(1 for v in ir if v < PRETO)

            if cores_anteriores is not None and COR_VERDE in cores and not algum_verde:
                print(
                    f"Verde ignorado: sequencia incorreta | "
                    f"Anterior: {cores_anteriores} | Atual: {cores}"
                )

            # Depois de executar uma decisao, espera sair do marcador
            # antes de permitir outra leitura.
            if verde_bloqueado:
                if COR_VERDE not in cores:
                    if inicio_sem_verde is None:
                        inicio_sem_verde = time.monotonic()
                    elif time.monotonic() - inicio_sem_verde >= TEMPO_LIBERAR_VERDE:
                        verde_bloqueado = False
                        inicio_sem_verde = None
                else:
                    inicio_sem_verde = None

            if algum_verde and not verde_bloqueado:
                verde_bloqueado = True
                inicio_sem_verde = None

                print(f"Marcador verde confirmado: {cores_anteriores} -> {cores}")

                if verde_dos_dois_lados:
                    print("Verde dos dois lados: meia-volta.")
                elif verde_esquerda:
                    print("Verde a esquerda: virar a esquerda.")
                else:
                    print("Verde a direita: virar a direita.")

                if not tratar_verde(
                    robo,
                    verde_esquerda or verde_dos_dois_lados,
                    verde_direita or verde_dos_dois_lados
                ):
                    print("Nao encontrou a linha depois do verde.")
                    break

                posicao, _ = calcular_posicao(robo.reflexao())
                if posicao is None:
                    direcao = (
                        "ESQUERDA"
                        if verde_esquerda or verde_dos_dois_lados
                        else "DIREITA"
                    )
                    encontrou, posicao = buscar_linha_girando(
                        robo, direcao, TEMPO_GIRO_90
                    )
                    if not encontrou:
                        print("Nao recuperou a linha.")
                        break

                erro_anterior = posicao
                ultima_posicao = posicao
                curva_detectada = False
                inicio_reta = None
                inicio_reta_estavel = None
                cores_anteriores = cores
                continue

            # Seguidor de linha
            posicao, intensidade = calcular_posicao(ir)

            if posicao is not None:
                if abs(posicao) >= LIMITE_CURVA:
                    curva_detectada = True
                    inicio_reta = None

                elif curva_detectada:
                    if abs(posicao) <= LIMITE_RETA:
                        if inicio_reta is None:
                            inicio_reta = time.monotonic()
                        elif time.monotonic() - inicio_reta >= TEMPO_RETA:
                            curva_detectada = False
                            inicio_reta = None
                    else:
                        inicio_reta = None

            # Linha perdida
            if posicao is None:
                robo.para()

                if curva_detectada:
                    print("Linha perdida: tentando recuperar curva.")
                    encontrou, nova_posicao = recuperar_linha(robo, ultima_posicao)
                    if not encontrou:
                        print("Curva nao encontrada. Tentando como GAP...")
                        encontrou, nova_posicao = atravessar_gap(robo)
                else:
                    print("Tentando atravessar GAP...")
                    encontrou, nova_posicao = atravessar_gap(robo)

                if not encontrou:
                    print("Nao foi possivel recuperar a linha.")
                    break

                posicao = nova_posicao
                erro_anterior = posicao
                ultima_posicao = posicao
                curva_detectada = False
                inicio_reta = None

            # Controle PD
            erro = posicao
            correcao = controlar_pd(erro, erro_anterior)
            ve, vd = velocidades_motores(correcao, erro)

            robo.anda(ve, vd)

            erro_anterior = erro
            ultima_posicao = erro

            print(
                f"Erro: {erro:+.2f} | "
                f"Correcao: {correcao:+.2f} | "
                f"IR: {ir} | "
                f"Cores: {cores} | "
                f"Motores: {ve:.1f}, {vd:.1f}"
            )

            cores_anteriores = cores
            time.sleep(0.01)

    finally:
        robo.para()


if __name__ == "__main__":
    main()
