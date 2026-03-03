# exporta_propriedades_completas.py

import numpy as np
import pandas as pd
from pathlib import Path
from dados_amostras import dados  # dicionário com todas as amostras
import time  # só para simular leve delay se quiser visualizar a barra

# --- Parâmetro global ---
angulo_rad = np.deg2rad(45)  # ângulo oblíquo usado nos cálculos

# --- Função de processamento de uma amostra ---
def processar_amostra(dados_amostra, angulo_rad):
    massa = dados_amostra["massa"]
    volume = dados_amostra["volume"]
    rho = massa / volume

    medidas = dados_amostra["medidas"]
    vel = {k: medidas[k]["dist"] / medidas[k]["tempo"] for k in medidas}

    # médias iguais ao index1 original
    V_LL = vel["LL"]
    V_RR = vel["RR"]
    V_TT = vel["TT"]
    V_LR = (vel.get("LR", 0) + vel.get("RL", 0)) / 2
    V_LT = (vel.get("LT", 0) + vel.get("TL", 0)) / 2
    V_RT = (vel.get("RT", 0) + vel.get("TR", 0)) / 2
    V_12a = (vel.get("RL1", 0) + vel.get("RL2", 0)) / 2
    V_13a = (vel.get("LT1", 0) + vel.get("LT2", 0)) / 2
    V_23a = (vel.get("RT1", 0) + vel.get("RT2", 0)) / 2

    # diagonais
    C11 = rho * V_LL**2
    C22 = rho * V_RR**2
    C33 = rho * V_TT**2
    C44 = rho * V_RT**2
    C55 = rho * V_LT**2
    C66 = rho * V_LR**2

    n1 = np.sin(angulo_rad)
    n2 = np.cos(angulo_rad)
    n3 = np.cos(angulo_rad)

    # off-diagonais
    try:
        C12 = (np.sqrt((C11*n1**2 + C66*n2**2 - rho*V_12a**2) *
                       (C66*n1**2 + C22*n2**2 - rho*V_12a**2)) - C66*n1*n2) / (n1*n2)
        C13 = (np.sqrt((C11*n1**2 + C55*n3**2 - rho*V_13a**2) *
                       (C55*n1**2 + C33*n3**2 - rho*V_13a**2)) - C55*n1*n3) / (n1*n3)
        C23 = (np.sqrt((C22*n2**2 + C44*n3**2 - rho*V_23a**2) *
                       (C44*n2**2 + C33*n3**2 - rho*V_23a**2)) - C44*n2*n3) / (n2*n3)
    except ZeroDivisionError:
        C12 = C13 = C23 = np.nan

    C = np.array([
        [C11, C12, C13, 0,   0,   0],
        [C12, C22, C23, 0,   0,   0],
        [C13, C23, C33, 0,   0,   0],
        [0,   0,   0,   C44, 0,   0],
        [0,   0,   0,   0,   C55, 0],
        [0,   0,   0,   0,   0,   C66]
    ])

    S = np.linalg.inv(C)

    E = { "L": 1.0/S[0,0], "R": 1.0/S[1,1], "T": 1.0/S[2,2] }
    G = { "RT": 1.0/S[3,3], "LT": 1.0/S[4,4], "LR": 1.0/S[5,5] }
    nu = {
        "LR": -S[0,1]/S[0,0], "LT": -S[0,2]/S[0,0],
        "RL": -S[1,0]/S[1,1], "TL": -S[2,0]/S[2,2],
        "RT": -S[1,2]/S[1,1], "TR": -S[1,2]/S[2,2]
    }

    return {
        "massa": massa,
        "volume": volume,
        "densidade": rho,
        "velocidades": vel,
        "C": C,
        "S": S,
        "E": E,
        "G": G,
        "nu": nu,
        "medidas": medidas  # incluir distâncias e tempos originais
    }

# --- Exportar todas as amostras para CSV com barra de progresso ---
linhas = []
total = len(dados)
print(f"Processando {total} amostras...\n")

for i, (nome, dados_amostra) in enumerate(dados.items(), start=1):
    props = processar_amostra(dados_amostra, angulo_rad)

    linha = {
        "amostra": nome,
        "massa": props["massa"],
        "volume": props["volume"],
        "densidade": props["densidade"]
    }

    # Velocidades
    for k, v in props["velocidades"].items():
        linha[f"V_{k}"] = v

    # Coeficientes de rigidez (C)
    C = props["C"]
    for idx, label in enumerate(["C11","C22","C33","C44","C55","C66"]):
        linha[label] = C[idx, idx]
    linha["C12"] = C[0,1]
    linha["C13"] = C[0,2]
    linha["C23"] = C[1,2]

    # Propriedades mecânicas
    for k, v in props["E"].items():
        linha[f"E_{k}"] = v
    for k, v in props["G"].items():
        linha[f"G_{k}"] = v
    for k, v in props["nu"].items():
        linha[f"nu_{k}"] = v

    # Distâncias e tempos originais
    for k, med in props["medidas"].items():
        linha[f"dist_{k}"] = med.get("dist", np.nan)
        linha[f"tempo_{k}"] = med.get("tempo", np.nan)

    linhas.append(linha)

    # --- Barra de progresso simples ---
    pct = int(i / total * 100)
    print(f"\rProgresso: {pct}% ({i}/{total})", end="", flush=True)
    # time.sleep(0.01)  # opcional: para simular atraso e visualizar barra

print("\nProcessamento concluído!\n")

# --- Criar DataFrame e salvar ---
df = pd.DataFrame(linhas)
caminho_csv = Path(__file__).parent / "amostras_completas.csv"
df.to_csv(caminho_csv, index=False)
print(f"CSV completo gerado em: {caminho_csv}")
