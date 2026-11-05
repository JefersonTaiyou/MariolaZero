"""Tutorial 1 — Olá, Mariola!

Acende os LEDs, anda para frente 1,5 s, para e mostra quanto cada encoder contou.
Roda igual no robô e no simulador:
    python simulador.py --robo robo_esteira.json --programa CAMINHO/01_ola_mariola/main.py
"""
import time

from motores import Motores

motores = Motores(True)                       # True = cada comando já vai para a placa
motores.direcao_motor(2, Motores.INVERTIDO)   # o motor 2 está espelhado no robô

try:    
    motores.reseta_angulo_motor(1)
    motores.reseta_angulo_motor(2)

    for i in range(2): #repete o loop 2x indo pr afrente depois pra tras
        dir = 1 if i == 0 else -1 #aqui utiliza do operador ternário para definir a direção do movimento, 1 para frente e -1 para trás
        motores.velocidade_motores(dir*40, dir*40)  #aplica a velocidade nos motores, multiplicando pela direção para ir para frente ou para trás
        inicio = time.time()
        while time.time() - inicio < 1: #aqui o loop while é usado para manter o movimento por 1 segundo, verificando o tempo decorrido
            motores.estado()                      # lê os encoders sem mudar nada
            time.sleep(0.25)
     
    motores.velocidade_motores(0, 0)
    time.sleep(0.3)
    motores.estado()
    for i in range(3): #repete o loop 3x acendendo os leds vermelho e desligando
        motores.set_led_rgb_all(100, 0, 0)         # vermelho aceso
        time.sleep(0.5)
        motores.set_led_rgb_all(0, 0, 0)         # tudo desligado
        time.sleep(0.5)
        
except KeyboardInterrupt:
    print('Interrompido pelo usuário')
finally:
    # acontece SEMPRE: no fim normal, no Ctrl+C e se der erro no meio
    motores.para_motores()
    motores.set_led_rgb_all(0, 0, 0)
    print('Motores parados.')
