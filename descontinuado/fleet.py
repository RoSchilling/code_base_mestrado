from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import math

def tratamento_col_passageiros(col_passageiros: pd.Series) -> pd.Series:
    "Função construida exclusivamente para a converção da coluna de passageiros em inteiro"
    passageiros = col_passageiros.copy()

    passageiros = passageiros.replace(' ', '0')
    passageiros = passageiros.astype(int)
    return passageiros

def carga_por_hora(mco: pd.DataFrame, 
                   col_linha: str = 'linha', 
                   col_saida: str = 'saida', 
                   col_passageiros: str = 'total usuarios',
                   col_data: str = 'viagem') -> pd.DataFrame:

    """
    Calcula a quantidade de passegeiros foram transportados por hora.

    mco: É o DataFrame contendo o mapa de controle operacional
    col_linha: nome da coluna que contém a informação da linha
    col_saida: nome da coluna que tem a informação do horário da viagem
    col_passageiros: nome da coluna que contém a quantidade de passageiros
    """

    df = mco.copy()

    df['hora'] = mco[col_saida].str[:2]

    df['passageiros'] = tratamento_col_passageiros(df[col_passageiros])

    carga_por_dia = df.groupby([col_data, 'hora', col_linha]).agg(carga=('passageiros', 'sum'))

    carga_media = carga_por_dia.groupby(['hora', col_linha])['carga'].mean()
    return carga_media.reset_index()

def pico_passageiros(mco: pd.DataFrame, col_linha: str = 'linha') -> pd.DataFrame:
    df = mco.copy()
    df = carga_por_hora(df)
    pico_passageiro = df.groupby([col_linha])['carga'].idxmax()
    return df.iloc[pico_passageiro].reset_index(drop=True)

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

def frota_por_demanda(
        carga_pico: float,
        tempo_ciclo_pico_min: float,
        load_factor: float = 0.9,
        capacidade_total: int = 80
) -> float:
    """
    n_k - frota necessária pela demanda de passageiros no horário de pico (Othman et. al 2024)

    carga_pico: passageiros transportados na hora de pico (de pico_passageiros)
    tempo_ciclo_pico_min: duração média do ciclo naquela hora (de tempo_ciclo_no_pico)
    load_factor: fator de ocupação máxima aceitável (ex: 0.8 = 80% da capacidade)
    capacidade_total: capacidade do veículo de passageiros sentados e em pé (Manual de Especificações)

    """

    f_k = carga_pico / (load_factor * capacidade_total)

    n_k = f_k * tempo_ciclo_pico_min /60

    return math.ceil(n_k)

def frota_por_demanda_linhas(mco: pd.DataFrame, 
                             load_factor: float = 0.8, 
                             capacidade_total: int = 70,
                             col_linha:str ='linha', 
                             col_inicio: str = 'saida', 
                             col_fim: str = 'chegada',
                             col_data: str = 'viagem',
                             col_hora: str = 'hora') -> pd.DataFrame:

    picos = pico_passageiros(mco)

    resultados = []
    for _, linha_row in picos.iterrows():
        linha = linha_row['linha']
        hora_pico = linha_row['hora']
        carga_pico = linha_row['carga']

        tempo_ciclo = tempo_ciclo_no_pico(mco, 
                                          hora_pico, 
                                          linha,
                                          col_linha,
                                          col_inicio,
                                          col_fim,
                                          col_data, 
                                          col_hora)
        
        N_k = frota_por_demanda(carga_pico, tempo_ciclo, load_factor=load_factor, capacidade_total=capacidade_total)
        resultados.append({
            'linha': linha,
            'frota_necessaria' : N_k,
            'hora_pico_passaageiro': hora_pico,
            'carga_pico' : carga_pico
        })

    return pd.DataFrame(resultados)