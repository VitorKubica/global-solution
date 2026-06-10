"""
=============================================================================
SISTEMA INTELIGENTE DE MONITORAMENTO DE MISSAO ESPACIAL - AURORA-1
=============================================================================
Autor  : Vitor Kubica Silveira
RM     : 573465
Curso  : Ciencias da Computacao - FIAP
Global Solution 2026 - Fase 3
=============================================================================
"""

import csv
import os
from collections import deque


# leitura do csv de telemetria

def carregar_dados(caminho_csv: str) -> list:
    """Le o arquivo CSV e retorna lista de dicionarios."""
    registros = []
    with open(caminho_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for linha in reader:
            registros.append(linha)
    return registros


# organiza os registros brutos nas estruturas usadas pelo sistema

def organizar_dados(registros: list) -> dict:
    """
    Retorna dict com:
      modulos       -> hash nome: status bool
      energia_lista -> matriz [horario, geracao, consumo, reserva]
      fila_alertas  -> deque FIFO de alertas pendentes
      pilha_eventos -> lista LIFO de eventos criticos
      ambientais    -> leituras ambientais mais recentes
      hierarquia    -> arvore de subsistemas da missao
      log_eventos   -> todos os registros de log
    """

    modulos = {}
    energia_por_horario = {}
    fila_alertas = deque()
    pilha_eventos = []
    ambientais = {}
    log_eventos = []

    for r in registros:
        tipo = r["tipo"]

        if tipo == "modulo_status":
            modulos[r["nome"]] = bool(int(r["valor"]))

        elif tipo == "energia":
            h = r["horario"]
            if h not in energia_por_horario:
                energia_por_horario[h] = {"horario": h, "geracao": None,
                                          "consumo": None, "reserva": None}
            nome = r["nome"]
            if nome == "geracao_solar":
                energia_por_horario[h]["geracao"] = float(r["valor"])
            elif nome == "consumo":
                energia_por_horario[h]["consumo"] = float(r["valor"])
            elif nome == "reserva":
                energia_por_horario[h]["reserva"] = float(r["valor"])

        elif tipo == "ambiental":
            chave = f"{r['nome']}_{r['horario']}"
            ambientais[chave] = r["valor"]
            # ultima leitura simples para acesso rapido no diagnostico
            ambientais[r["nome"]] = r["valor"]

        elif tipo == "log":
            entrada_log = {
                "evento" : r["nome"],
                "detalhe": r["valor"],
                "nivel"  : r["unidade"],
                "horario": r["horario"],
            }
            log_eventos.append(entrada_log)
            if r["unidade"] in ("critico", "erro", "alerta"):
                fila_alertas.append(entrada_log)
            if r["unidade"] == "critico":
                pilha_eventos.append(entrada_log)

    # converte para lista de listas ordenada por horario
    energia_lista = []
    for h in sorted(energia_por_horario.keys()):
        linha = energia_por_horario[h]
        energia_lista.append([
            linha["horario"],
            linha["geracao"],
            linha["consumo"],
            linha["reserva"],
        ])

    hierarquia = {
        "AURORA-1": {
            "Energia": {
                "Solar"    : {"geracao": energia_lista[-1][1] if energia_lista else 0},
                "Baterias" : {"reserva": energia_lista[-1][3] if energia_lista else 0},
            },
            "Habitat": {
                "Oxigenio"    : {"modulo": modulos.get("suporte_vida", False)},
                "Temperatura" : {"valor": ambientais.get("temperatura_interna", "N/A")},
                "Comunicacao" : {"modulo": modulos.get("comunicacao", False)},
            },
            "Laboratorio": {
                "status": modulos.get("laboratorio", False),
            },
            "Armazenamento": {
                "status": modulos.get("armazenamento", False),
            },
        }
    }

    return {
        "modulos"      : modulos,
        "energia_lista": energia_lista,
        "fila_alertas" : fila_alertas,
        "pilha_eventos": pilha_eventos,
        "ambientais"   : ambientais,
        "hierarquia"   : hierarquia,
        "log_eventos"  : log_eventos,
    }


# regras de diagnostico com IF/ELIF/ELSE e operadores AND/OR/NOT
#
# STATUS_CRITICO = (reserva < 25) OR (NOT comunicacao AND reserva < 40)
#                  OR (radiacao == 'critica' AND NOT suporte_vida)
# STATUS_ALERTA  = (reserva < 40) OR (NOT comunicacao) OR (radiacao == 'alta')
#                  OR (temperatura_interna < 18)

def diagnosticar(dados: dict) -> dict:
    """Classifica o estado operacional em: normal, alerta ou critico."""

    modulos = dados["modulos"]
    energia = dados["energia_lista"]
    amb     = dados["ambientais"]

    reserva_atual = energia[-1][3] if energia else 100.0
    consumo_atual = energia[-1][2] if energia else 0.0

    comunicacao  = modulos.get("comunicacao", True)
    suporte_vida = modulos.get("suporte_vida", True)

    radiacao     = amb.get("radiacao", "normal")
    temp_interna = float(amb.get("temperatura_interna", 22))
    qual_com     = float(amb.get("qualidade_comunicacao", 100))

    alertas = []
    status  = "normal"

    # reserva < 25 E consumo alto -> critico imediato
    if reserva_atual < 25 and consumo_atual > 60:
        alertas.append({
            "nivel"  : "CRITICO",
            "msg"    : f"Reserva de energia critica: {reserva_atual:.1f}% com consumo {consumo_atual:.1f} kWh",
            "acao"   : "Desligar todos os sistemas nao essenciais imediatamente.",
        })
        status = "critico"

    # comunicacao OFFLINE E reserva < 40 -> sem fallback possivel
    if not comunicacao and reserva_atual < 40:
        alertas.append({
            "nivel"  : "CRITICO",
            "msg"    : f"Comunicacao offline e energia baixa ({reserva_atual:.1f}%) — sem fallback disponivel.",
            "acao"   : "Priorizar comunicacao de emergencia e redirecionar energia.",
        })
        status = "critico"

    # radiacao critica sem suporte a vida -> risco a tripulacao
    if radiacao == "critica" and not suporte_vida:
        alertas.append({
            "nivel"  : "CRITICO",
            "msg"    : "Radiacao em nivel critico com suporte a vida inativo — risco imediato a tripulacao.",
            "acao"   : "Acionar blindagem de emergencia e reativar suporte a vida.",
        })
        status = "critico"

    # comunicacao offline sozinha ja gera alerta
    if not comunicacao:
        alertas.append({
            "nivel"  : "ALERTA",
            "msg"    : "Modulo de comunicacao offline.",
            "acao"   : "Verificar antena e tentar reboot do transceptor.",
        })
        if status == "normal":
            status = "alerta"

    # reserva < 40 OR consumo > 75
    if reserva_atual < 40 or consumo_atual > 75:
        alertas.append({
            "nivel"  : "ALERTA",
            "msg"    : f"Nivel de energia baixo: reserva {reserva_atual:.1f}% / consumo {consumo_atual:.1f} kWh.",
            "acao"   : "Ativar modo de economia. Desligar laboratorio e sistemas nao criticos.",
        })
        if status == "normal":
            status = "alerta"

    if radiacao in ("alta", "critica"):
        alertas.append({
            "nivel"  : "ALERTA" if radiacao == "alta" else "CRITICO",
            "msg"    : f"Nivel de radiacao: {radiacao.upper()} — tempestade solar detectada.",
            "acao"   : "Reduzir exposicao externa. Ativar escudos de radiacao do habitat.",
        })
        if status == "normal":
            status = "alerta"

    # faixa segura: 18-26 C
    if temp_interna < 18 or temp_interna > 26:
        alertas.append({
            "nivel"  : "ALERTA",
            "msg"    : f"Temperatura interna fora da faixa segura: {temp_interna:.1f} C (seguro: 18-26 C).",
            "acao"   : "Ajustar sistema de climatizacao do habitat.",
        })
        if status == "normal":
            status = "alerta"

    if qual_com < 40:
        alertas.append({
            "nivel"  : "ALERTA",
            "msg"    : f"Qualidade do sinal de comunicacao: {qual_com:.0f}% (minimo seguro: 40%).",
            "acao"   : "Reorientar antena direcional. Reduzir ruido eletromagnetico local.",
        })
        if status == "normal":
            status = "alerta"

    # coleta leituras marcadas como erro no log (ex: temperatura externa -120C)
    inconsistencias = []
    for ev in dados["log_eventos"]:
        if ev["nivel"] == "erro":
            inconsistencias.append(f"DADO INCONSISTENTE [{ev['horario']}]: {ev['detalhe']}")

    return {
        "status"          : status.upper(),
        "alertas"         : alertas,
        "inconsistencias" : inconsistencias,
        "reserva_atual"   : reserva_atual,
        "consumo_atual"   : consumo_atual,
        "radiacao"        : radiacao,
        "comunicacao_ok"  : comunicacao,
        "temp_interna"    : temp_interna,
    }


# regressao linear simples sobre o historico de reservas (sem libs externas)
# x = indice do horario, y = reserva %
# y = a*x + b, extrapola para x = n

def prever_reserva(energia_lista: list) -> dict:
    """Estima a reserva no proximo ciclo por regressao linear."""

    pontos = [(i, linha[3]) for i, linha in enumerate(energia_lista)
              if linha[3] is not None]

    n   = len(pontos)
    sx  = sum(p[0] for p in pontos)
    sy  = sum(p[1] for p in pontos)
    sxy = sum(p[0] * p[1] for p in pontos)
    sx2 = sum(p[0] ** 2 for p in pontos)

    denominador = n * sx2 - sx ** 2
    if denominador == 0:
        a, b = 0, sy / n
    else:
        a = (n * sxy - sx * sy) / denominador
        b = (sy - a * sx) / n

    proximo_x    = n
    previsao_val = a * proximo_x + b

    return {
        "horarios"   : [energia_lista[p[0]][0] for p in pontos],
        "reservas"   : [p[1] for p in pontos],
        "inclinacao" : round(a, 4),
        "intercepto" : round(b, 4),
        "previsao"   : round(previsao_val, 2),
        "tendencia"  : "queda" if a < 0 else "alta",
    }


# funcoes de exibicao

def linha_separadora(char="─", largura=70):
    print(char * largura)

def exibir_cabecalho():
    linha_separadora("═")
    print("  AURORA-1 :: SISTEMA INTELIGENTE DE MONITORAMENTO ESPACIAL")
    print("  Vitor Kubica Silveira  |  RM 573465  |  FIAP 2026")
    linha_separadora("═")

def exibir_modulos(modulos: dict):
    print("\n[ MODULOS CRITICOS ]")
    linha_separadora()
    for nome, status in modulos.items():
        icone = "OK " if status else "FALHA"
        estado = "OPERACIONAL" if status else "OFFLINE"
        print(f"  {icone}  {nome.upper().replace('_', ' '):<22} {estado}")
    linha_separadora()

def exibir_matriz_energia(energia_lista: list):
    print("\n[ MATRIZ DE ENERGIA (kWh / % reserva) ]")
    linha_separadora()
    header = f"  {'Horario':<10} {'Geracao':>10} {'Consumo':>10} {'Reserva %':>12}"
    print(header)
    linha_separadora("-")
    for linha in energia_lista:
        h, g, c, r = linha
        g_str = f"{g:.1f}" if g is not None else "N/A"
        c_str = f"{c:.1f}" if c is not None else "N/A"
        r_str = f"{r:.1f}%" if r is not None else "N/A"
        print(f"  {h:<10} {g_str:>10} {c_str:>10} {r_str:>12}")
    linha_separadora()

def exibir_fila_alertas(fila: deque):
    print("\n[ FILA DE ALERTAS PENDENTES (FIFO) ]")
    linha_separadora()
    if not fila:
        print("  Nenhum alerta pendente.")
    for i, alerta in enumerate(fila, 1):
        print(f"  #{i:02d} [{alerta['nivel'].upper():<7}] {alerta['horario']}  {alerta['evento']}")
        print(f"       {alerta['detalhe']}")
    linha_separadora()

def exibir_pilha_eventos(pilha: list):
    print("\n[ PILHA DE EVENTOS CRITICOS ANALISADOS (LIFO) ]")
    linha_separadora()
    if not pilha:
        print("  Nenhum evento critico registrado.")
    for ev in reversed(pilha):  # topo da pilha primeiro
        print(f"  >> [{ev['horario']}] {ev['evento']}: {ev['detalhe']}")
    linha_separadora()

def exibir_diagnostico(diag: dict):
    print("\n[ DIAGNOSTICO OPERACIONAL ]")
    linha_separadora("═")
    status = diag["status"]
    icone = {"NORMAL": "✔ NORMAL", "ALERTA": "⚠ ALERTA", "CRITICO": "✘ CRITICO"}.get(status, status)
    print(f"  STATUS GERAL: {icone}")
    linha_separadora()

    if diag["inconsistencias"]:
        print("\n  !! INCONSISTENCIAS DETECTADAS NOS DADOS !!")
        for inc in diag["inconsistencias"]:
            print(f"     {inc}")

    print(f"\n  Reserva atual  : {diag['reserva_atual']:.1f}%")
    print(f"  Consumo atual  : {diag['consumo_atual']:.1f} kWh")
    print(f"  Radiacao       : {diag['radiacao'].upper()}")
    print(f"  Comunicacao    : {'OK' if diag['comunicacao_ok'] else 'OFFLINE'}")
    print(f"  Temp. interna  : {diag['temp_interna']:.1f} C")
    linha_separadora()

def exibir_alertas_e_recomendacoes(alertas: list):
    print("\n[ ALERTAS E RECOMENDACOES PRIORIZADOS ]")
    linha_separadora("═")

    criticos = [a for a in alertas if a["nivel"] == "CRITICO"]
    normais  = [a for a in alertas if a["nivel"] == "ALERTA"]

    prioridade = criticos + normais

    for i, alerta in enumerate(prioridade, 1):
        nivel = alerta["nivel"]
        print(f"\n  Acao {i} ({nivel})")
        print(f"  Problema   : {alerta['msg']}")
        print(f"  Recomendacao: {alerta['acao']}")
        linha_separadora("-")

def exibir_previsao(prev: dict):
    print("\n[ ANALISE E PREVISAO DE ENERGIA (Regressao Linear) ]")
    linha_separadora("═")
    print(f"  Metodologia : Regressao linear simples (sem bibliotecas externas)")
    print(f"  Variavel    : Reserva de energia (%)")
    print(f"  Equacao     : y = {prev['inclinacao']}x + {prev['intercepto']:.2f}")
    print(f"  Tendencia   : {prev['tendencia'].upper()}")
    print(f"\n  Horarios analisados : {prev['horarios']}")
    print(f"  Reservas registradas: {prev['reservas']}")
    print(f"\n  >> PREVISAO PROXIMO CICLO: {prev['previsao']:.2f}%")

    if prev["previsao"] < 15:
        print("  [!] CRITICO: Reserva prevista abaixo de 15% — risco de blackout total.")
        print("      RECOMENDACAO: Desligar todos os nao essenciais antes do proximo ciclo.")
    elif prev["previsao"] < 30:
        print("  [!] ALERTA: Reserva prevista abaixo de 30% — iniciar modo de emergencia.")
        print("      RECOMENDACAO: Reduzir consumo em pelo menos 30% no proximo turno.")
    else:
        print("  [OK] Reserva prevista dentro da faixa operacional aceitavel.")
    linha_separadora()

def exibir_hierarquia(h: dict, nivel: int = 0):
    """Exibe a hierarquia da missao de forma recursiva."""
    for chave, valor in h.items():
        prefixo = "  " * nivel + ("└─ " if nivel > 0 else "")
        if isinstance(valor, dict):
            print(f"{prefixo}{chave}")
            exibir_hierarquia(valor, nivel + 1)
        else:
            print(f"{prefixo}{chave}: {valor}")


# ponto de entrada

def main():
    base_dir    = os.path.dirname(os.path.abspath(__file__))
    caminho_csv = os.path.join(base_dir, "..", "data", "dados.csv")

    exibir_cabecalho()

    print("\n  Carregando telemetria de dados.csv...")
    registros = carregar_dados(caminho_csv)
    print(f"  {len(registros)} registros carregados com sucesso.")

    dados = organizar_dados(registros)

    exibir_modulos(dados["modulos"])
    exibir_matriz_energia(dados["energia_lista"])
    exibir_fila_alertas(dados["fila_alertas"])
    exibir_pilha_eventos(dados["pilha_eventos"])

    print("\n[ HIERARQUIA DA MISSAO AURORA-1 ]")
    linha_separadora()
    exibir_hierarquia(dados["hierarquia"])
    linha_separadora()

    diag = diagnosticar(dados)
    exibir_diagnostico(diag)
    exibir_alertas_e_recomendacoes(diag["alertas"])

    prev = prever_reserva(dados["energia_lista"])
    exibir_previsao(prev)

    print("\n  Monitoramento concluido. Proxima atualizacao em 30 min.")
    linha_separadora("═")


if __name__ == "__main__":
    main()
