# Progresso — Alocação de Frota Elétrica (EVSP) — 2026-09-12

Notas pra retomar amanhã e servir de base pro Capítulo 5 (ETL e algoritmos utilizados).

## 1. Arquitetura atual

```
parametros/
├── load.py        # GTFS + MCO loaders, TIPOS_DIAS, linhas_move
├── extract.py      # get_trips_for_routes
├── fleet.py        # frota_por_demanda_todas_linhas (Di), ciclos_completo_km_ev, ciclos_diarios_totais
├── schedule.py     # horarios_saida, horario_chegada, headway_por_hora
└── metrics.py      # extensao_produtiva_mensal (Ei/Ki), custo_rodagem_por_linha (Ri),
                     # variabilidade_tempo_operacional (CV/F3), folga_recarga_garagem (Foi/F4),
                     # tempo_recarga_necessario, percentual_bateria_consumido (F4)

orquestrador/
└── pipeline.py     # tabela_parametros: monta a tabela de PARÂMETROS por linha (não os ci)

busca/              # ainda não criada — camada de decisão (Bellman-Zadeh, LP-τ, Wald/Laplace/Savage/Hurwicz)
```

**Decisão de arquitetura importante**: `tabela_parametros` produz só os *ingredientes* por linha (`Di`, `Ei`, `CV`, `Foi`, `percentual_bateria`, `tempo_recarga`, `Ri`...). Os coeficientes `c1i`-`c4i` das funções objetivo (combinando esses ingredientes) ficam numa camada **separada**, ainda não criada — não devem entrar na tabela de parâmetros.

## 2. Status por coeficiente (F1-F4)

### F1 — custo operacional, `c1i = Ci·T·Ki + Ri + Aci`
| Peça | Status |
|---|---|
| `Ki` | ✅ pronto (`extensao_produtiva_mensal`, com `filtra_mes=True` pra evitar somar os 12 meses do MCO) |
| `Ci` (consumo kWh/km) | ❌ **decisão em aberto** — usar o valor do edital direto, ou construir uma métrica própria por linha? Ainda não decidido (ver Seção 3) |
| `T` (tarifa energia) | ❌ não iniciado — fonte ainda não levantada |
| `Ri` (rodagem, ANTP 2017 Eq. 2.9-2.11) | ✅ fórmula pronta (`custo_rodagem_por_linha`), mas só com `ppu`/`pre`/`npn`/`vdu`/`beta` de **teste** — precisa dos valores reais do edital/fabricante |
| `Aci` (peças e acessórios, ANTP 2023) | ⚠️ fórmula pesquisada (tabela fixa R$/km por perfil de veículo, Quadro 13 — **sem** faixa etária, diferente do 2017), mas função ainda **não escrita**; falta confirmar qual perfil (Midi/Básico/Padron/Articulado × Plug-In/Pantógrafo) se aplica |

### F2 — atendimento à demanda, `c2i = Pi·Ei/Di`
| Peça | Status |
|---|---|
| `Ei`, `Di` | ✅ prontos |
| `Pi` (passageiros) | ❌ **bloqueado** — `TOTAL USUARIOS` do MCO tem mediana zero numa amostra grande (provável falha de catraca, não demanda real zero). Reformulação de F2 sem `Pi` ainda não começou |

### F3 — variabilidade operacional, `c3i = σ/μ`
✅ **Pronta** (`variabilidade_tempo_operacional`), sem pendência.

### F4 — folga para recarga, `c4i = Foi - TCi(B)`
| Peça | Status |
|---|---|
| `Foi` (Eq. 4.43) | ✅ pronto (`folga_recarga_garagem`) — filtra o dia com mais viagens por linha, corrige virada de meia-noite só quando a saída é às 23h (evita inflar por erro de registro de poucos minutos) |
| `percentual_bateria` (B) | ✅ pronto (`percentual_bateria_consumido`), depende de `Ci` (ver F1) |
| `tempo_recarga` (TCi, Eq. 4.44) | ✅ pronto (`tempo_recarga_necessario`), só com `capacidade_bateria`/`potencia_carregador`/`conectores_carregador` de **teste** |
| `c4i` (combinação final, Eq. 4.45) | ❌ ainda não escrito — vai para a camada separada de funções objetivo, não pra `tabela_parametros` |

## 3. Decisões em aberto (bloqueiam o progresso)

1. **`Ci`** — usar o parâmetro do edital direto (como pensado inicialmente) ou construir uma métrica própria por linha? A Seção 4.4.1 da metodologia já reconhece que o consumo varia "de acordo com a criticidade da operação da linha" — se for calcular por linha, precisa decidir a partir de quê (velocidade média, topografia/shapes do GTFS, etc.).
2. **`T`** — tarifa da concessionária de energia, fonte ainda não levantada.
3. **`Aci`** — qual linha do Quadro 13 (ANTP 2023) usar (perfil de veículo).
4. **Valores reais do edital**: `ppu`, `pre`, `vdu`, `beta` (pneu/rodagem) e `capacidade_bateria`, `potencia_carregador`, `conectores_carregador` (bateria/recarga) — hoje só temos valores de teste plausíveis.
5. **F2 sem `Pi`** — como reformular.
6. **MCO `tipo dia`** — códigos observados: 8 (~840k linhas, o mais comum), 14, 7, 1, 10, 9, 12, 29, 13, 24... Nunca confirmamos qual código é "dia útil" de fato nesta sessão.
7. **Estrutura de pastas** — `load`/`extract`/`schedule` ficam dentro de `parametros/` (como estão agora) ou um pacote de ingestão separado? Ainda em aberto, não é urgente.

## 4. Bugs corrigidos nesta sessão (histórico, caso precise consultar)

- `headway_por_hora` contava `trip_id` misturando `service_id`s de calendários diferentes (dia útil + sábado + domingo juntos), inflando a frota estimada — corrigido filtrando por tipo de dia.
- `frota_por_demanda_todas_linhas`: performance 19s → ~1s, pré-agrupando `mco` por linha uma vez em vez de escanear a tabela inteira por linha dentro do loop.
- `folga_recarga_garagem`: a correção de "viagem que cruza meia-noite" inflava viagens com pequeno erro de registro (ex: saída 19:18, chegada 19:16 — só 2 min de erro, não uma virada de dia real); corrigido restringindo a correção a viagens cuja saída é às 23h. Também corrigido o problema de `Hi`/`Ui` misturarem dias de calendário diferentes (agora filtra pelo dia com mais viagens, por linha, antes de calcular).
- `extensao_produtiva_mensal`: sem filtro, soma os 12 meses do `mco_move` inteiro; com `filtra_mes=True`, agora soma só o mês com mais quilometragem por linha.

## 5. Material pro Capítulo 5 (ETL e algoritmos utilizados)

Sugestão de estrutura, mapeando pro que já está implementado:

- **5.1 Fontes de dados**: GTFS BHTrans (`gtfsbhtrans/`) e MCO (Mapa de Controle Operacional, `mco_move/`, ~31 linhas, 12 meses).
- **5.2 Pré-processamento**: filtragem de linhas e `service_id`/tipo de dia (`load.py`, `extract.py`, `schedule.py`).
- **5.3 Dimensionamento de frota (`Di`)**: `frota_por_demanda_todas_linhas` — frequência de pico (GTFS) × tempo de ciclo observado (MCO).
- **5.4 Cálculo dos parâmetros por linha**: `Ei`/`Ki` (extensão produtiva), `CV` (variabilidade), `Foi`/`TCi` (folga de recarga) — pode descrever o **método** mesmo sem os valores finais de `Ci`/`T`/`Aci`, já que o capítulo é sobre o algoritmo, não sobre os resultados.
- **5.5 Composição dos coeficientes**: como `c1i`-`c4i` são montados a partir dos parâmetros (mesmo que `c4i` ainda não esteja implementado, a fórmula/lógica já está definida).
- **5.6 Limitações metodológicas**: indisponibilidade de `Pi` confiável (F2), valores de edital ainda pendentes (`Ci`, `T`, `Aci`, parâmetros de pneu/bateria).

Dá pra escrever a maior parte do Capítulo 5 com o que já está pronto — as decisões em aberto (Seção 3 acima) não impedem descrever o **método**, só os **resultados numéricos finais**.
