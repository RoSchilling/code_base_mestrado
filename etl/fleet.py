from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import math

def pico_frequencia(headway_por_hora: pd.DataFrame) -> tuple[str, int]:
   """ 
   Identifica a hora de maior frequência PROGRAMADA (mais partidas no GTFS) para UMA linha, a partir do resultado de headway_por_hora (schedule.py).
   Retorna: (hora_pico como string de 2 dígitos, n_partidas naquela hora).
    """

   linha_pico = headway_por_hora.loc[headway_por_hora['n_partidas'].idxmax()]

   hora_pico = str(int(linha_pico['hora'])).zfill(2)
   n_partidas = int(linha_pico['n_partidas'])

   return hora_pico, n_partidas


def tempo_ciclo_no_pico(mco: pd.DataFrame, 
                        hora_pico: str, 
                        linha: str, 
                        col_linha:str ='linha', 
                        col_inicio: str = 'saida', 
                        col_fim: str = 'chegada',
                        col_data: str = 'viagem',
                        col_hora: str = 'hora') -> float:

    df = mco.copy()

    if col_hora not in df.columns:
        df[col_hora] = df[col_inicio].str[:2]

    condicoes = (df[col_linha] == linha) & (df[col_hora] == hora_pico)

    df  = df[condicoes]
    
    saida = pd.to_datetime(df[col_data] + ' ' + df[col_inicio] + ':00', format='%d/%m/%Y %H:%M:%S')
    chegada = pd.to_datetime(df[col_data] + ' ' + df[col_fim] + ':00', format='%d/%m/%Y %H:%M:%S')

    chegada = np.where(saida > chegada, chegada + pd.Timedelta(days=1), chegada)

    tempo_viagem = (chegada - saida).dt.total_seconds()/60

    tempo_medio_pico = tempo_viagem.mean()
    return tempo_medio_pico

def frota_por_demanda(n_partidas_pico: int, tempo_ciclo_pico_min: float) -> float:
    return n_partidas_pico * tempo_ciclo_pico_min / 60



def frota_por_demanda_todas_linhas(
    headway: pd.DataFrame,
    mco: pd.DataFrame,
    col_linha_gtfs: str = 'route_short_name',
    col_linha_mco: str = 'linha',
    col_inicio: str = 'saida',
    col_fim: str = 'chegada',
    col_data: str = 'viagem',
    col_hora: str = 'hora',
) -> pd.DataFrame:
    resultados = []

    for linha, grupo in headway.groupby(col_linha_gtfs):
        hora_pico, n_partidas = pico_frequencia(grupo)

        tempo_ciclo = tempo_ciclo_no_pico(
            mco, hora_pico, linha,
            col_linha=col_linha_mco, col_inicio=col_inicio, col_fim=col_fim,
            col_data=col_data, col_hora=col_hora,
        )

        n_k = frota_por_demanda(n_partidas, tempo_ciclo)

        resultados.append({
                'linha': linha,
                'frota_necessaria': n_k,
                'hora_pico_frequencia': hora_pico,
                'n_partidas_pico': n_partidas,
                'tempo_ciclo_pico_min': tempo_ciclo,
            })
 
    return pd.DataFrame(resultados)


def frota_por_energia(
        comprimento_ciclo_km: float,
        consumo_kwh_km: float,
        capacidade_bateria_kwh: float,
        ciclos_diario_totais: int,
        margem_seguranca: float = 0.85
) -> float:
    energia_por_ciclo = comprimento_ciclo_km * consumo_kwh_km
    ciclos_por_carga = math.floor(
        margem_seguranca * capacidade_bateria_kwh / energia_por_ciclo
    )
    if ciclos_por_carga < 1:
        raise ValueError("Uma carga completa não sustenta a operacação nesta linha")

    n_k_energia = math.ceil(ciclos_diario_totais/ciclos_por_carga)
    return n_k_energia


def ciclos_completo_km_ev(
        trips: pd.DataFrame,
        stop_times: pd.DataFrame,
        col_linha: str = 'route_short_name'
) -> pd.DataFrame:

    st = stop_times.dropna(subset=['shape_dist_traveled']).copy()
    st['shape_dist_traveled'] = st['shape_dist_traveled'].astype(float)

    dist_por_viagem = st.groupby('trip_id')['shape_dist_traveled'].max().reset_index()
    dist_por_viagem = dist_por_viagem.rename(columns={'shape_dist_traveled': 'extensao_km'})

    dist_com_linha = dist_por_viagem.merge(
        trips[['trip_id', col_linha, 'direction_id']],
        on='trip_id'
    )

    extensao_por_sentido = dist_com_linha.groupby([col_linha, 'direction_id'])['extensao_km'].mean().reset_index()
 
    ciclo_por_linha = extensao_por_sentido.groupby(col_linha)['extensao_km'].sum().reset_index()
    ciclo_por_linha = ciclo_por_linha.rename(columns={'extensao_km': 'comprimento_ciclo_km'})

    return ciclo_por_linha


def ciclos_diarios_totais(headway: pd.DataFrame, 
                          trips: pd.DataFrame, 
                          col_linha='route_short_name'):
    
    n_sentidos = trips.groupby(col_linha)['direction_id'].nunique().reset_index(name='n_sentidos')

    total_partidas = headway.groupby(col_linha)['n_partidas'].sum().reset_index()

    resultado = total_partidas.merge(n_sentidos, on=col_linha)
    resultado['ciclos_diarios_totais'] = resultado.apply(
        lambda row: int(round(row['n_partidas'] / row['n_sentidos'])), axis=1
    )

    return resultado[[col_linha, 'ciclos_diarios_totais']]




    