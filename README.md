# AURORA-1 — Sistema Inteligente de Monitoramento Espacial

## Equipe

| Nome | RM |
|---|---|
| Vitor Kubica Silveira | 573465 |

---

## Resumo do Problema e Cenário

A missão **AURORA-1** é uma operação espacial experimental em órbita de Marte. O sistema monitora continuamente seis módulos críticos da espaçonave e processa dados de telemetria para identificar situações de risco, gerar alertas automáticos e fornecer recomendações operacionais à equipe de controle.

O cenário simulado envolve uma **tempestade solar** que causa falha na comunicação, elevação crítica da radiação e queda progressiva da reserva de energia — exigindo decisões rápidas e priorizadas pelo sistema.

---

## Estruturas de Dados Utilizadas

| Estrutura | Aplicação no Sistema |
|---|---|
| **Dicionário (hash)** | Módulos críticos acessados pelo nome (`modulos["comunicacao"]`) |
| **Lista de listas (matriz)** | Leituras de energia organizadas por horário × variável |
| **Fila — `deque` (FIFO)** | Alertas pendentes ordenados por chegada para processamento sequencial |
| **Pilha — `list` (LIFO)** | Últimos eventos críticos analisados; exibidos do mais recente ao mais antigo |
| **Dicionário aninhado (árvore)** | Hierarquia da missão: AURORA-1 → Energia → Solar / Baterias, Habitat → Oxigênio / Temperatura / Comunicação |
| **Lista simples** | Série histórica de reservas para cálculo de regressão linear |

---

## Regras Lógicas Principais do Diagnóstico

**Expressão booleana principal:**

```
STATUS_CRITICO = (reserva < 25 AND consumo > 60)
              OR (NOT comunicacao AND reserva < 40)
              OR (radiacao == 'critica' AND NOT suporte_vida)

STATUS_ALERTA  = (reserva < 40 OR consumo > 75)
              OR (NOT comunicacao)
              OR (radiacao IN ['alta', 'critica'])
              OR (temp_interna < 18 OR temp_interna > 26)
              OR (qualidade_comunicacao < 40)
```

| # | Regra | Operadores | Resultado |
|---|---|---|---|
| 1 | `reserva < 25 AND consumo > 60` | AND | CRÍTICO — blackout iminente |
| 2 | `NOT comunicacao AND reserva < 40` | NOT, AND | CRÍTICO — sem fallback |
| 3 | `radiacao == 'critica' AND NOT suporte_vida` | AND, NOT | CRÍTICO — risco à tripulação |
| 4 | `NOT comunicacao` | NOT | ALERTA — módulo offline |
| 5 | `reserva < 40 OR consumo > 75` | OR | ALERTA — energia baixa |
| 6 | `radiacao in ('alta','critica')` | OR | ALERTA/CRÍTICO — tempestade solar |
| 7 | `temp < 18 OR temp > 26` | OR | ALERTA — habitabilidade |
| 8 | `qualidade_comunicacao < 40` | — | ALERTA — sinal degradado |

---

## Técnica de Previsão Utilizada

**Regressão linear simples** implementada manualmente (sem bibliotecas externas).

- **Variável analisada:** Reserva de energia (%)
- **Dados usados:** 6 leituras horárias (06:00 às 21:00)
- **Equação encontrada:** `y = -4.5x + 46.43`
- **Previsão próximo ciclo:** **19,43%**
- **Influência na decisão:** A previsão abaixo de 30% ativou automaticamente a recomendação de reduzir consumo em 30% antes do próximo ciclo.

---

## Como Executar

```bash
# Clonar o repositório
git clone https://github.com/<seu-usuario>/global-solution-aurora1
cd global-solution-aurora1

# Executar (Python 3.8+ — sem dependências externas)
python src/sistema.py
```

Não é necessário instalar nenhuma biblioteca. O sistema usa apenas a biblioteca padrão do Python.

---

## Exemplo de Entrada e Saída

**Entrada (trecho do `data/dados.csv`):**
```
modulo_status,comunicacao,0,bool,00:00
energia,reserva,22.3,percent,21:00
ambiental,radiacao,critica,nivel,18:00
```

**Saída (trecho do terminal):**
```
STATUS GERAL: ✘ CRITICO

  Acao 1 (CRITICO)
  Problema   : Reserva de energia critica: 22.3% com consumo 65.0 kWh
  Recomendacao: Desligar todos os sistemas nao essenciais imediatamente.

  >> PREVISAO PROXIMO CICLO: 19.43%
  [!] ALERTA: Reserva prevista abaixo de 30% — iniciar modo de emergencia.
```

---

## Recomendações Geradas pelo Sistema

1. **(CRÍTICO)** Desligar todos os sistemas não essenciais imediatamente.
2. **(CRÍTICO)** Priorizar comunicação de emergência e redirecionar energia.
3. **(CRÍTICO)** Ativar escudos de radiação do habitat.
4. **(ALERTA)** Verificar antena e tentar reboot do transceptor.
5. **(ALERTA)** Ativar modo de economia — desligar laboratório.
6. **(ALERTA)** Reorientar antena direcional para melhorar sinal.

---

## Link do Vídeo no YouTube

> *(inserir link após gravação)*

---

## Conclusões e Aprendizados

O projeto demonstrou como conceitos fundamentais de computação — estruturas de dados, lógica booleana e análise estatística simples — podem ser combinados para construir um sistema de decisão funcional em um cenário realista. A regressão linear implementada do zero, sem dependências externas, evidenciou que algoritmos de previsão não exigem ferramentas complexas para ser efetivos. A inconsistência proposital nos dados (leitura de temperatura de -120°C) testou a capacidade diagnóstica do sistema, que a identificou e reportou corretamente.
