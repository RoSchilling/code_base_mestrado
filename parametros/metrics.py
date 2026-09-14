from __future__ import annotations
import pandas as pd
import os 
import numpy as np
from datetime import datetime, timedelta
from typing import Literal

def _determina_mes_com_maior_extensao(
        dataframe: pd.DataFrame,
        col_extensao: str,
        col_data: str = 'mes',
        col_linha: str = 'linha'
) -> pd.DataFrame:
    df = dataframe.copy()

    resultado = df.groupby([col_data, col_linha])[col_extensao].sum().rename('extensao_total').reset_index()
    idx_maior_extensao = resultado.groupby(col_linha)['extensao_total'].idxmax()
    resultado = resultado.loc[idx_maior_extensao, [col_data, col_linha]]

    return df.merge(resultado, on=[col_data, col_linha])

def extensao_produtiva_mensal(
        dataframe: pd.DataFrame,
        col_linha: str,
        col_extensao: str,
        filtra_mes: bool = False,
        col_data: str = None,
        format: str = '%d/%m/%Y',
        tipo_metragem: Literal['metros', 'km'] = 'km'
) -> pd.DataFrame:
    """
    Calcula Ei (extensao produtiva percorrida no mes, por linha).

    """

    resultado = dataframe.copy()
    resultado[col_extensao] = resultado[col_extensao].astype(float)

    if filtra_mes:
        if col_data == None:
            raise ValueError('Informe a coluna de data paro filtro')

        resultado['mes'] = pd.to_datetime(resultado[col_data], format=format).dt.month

        resultado = _determina_mes_com_maior_extensao(
            resultado,
            col_extensao=col_extensao,
            col_data='mes',
            col_linha=col_linha
        )


    if tipo_metragem == 'metros':
        resultado[col_extensao] = resultado[col_extensao] / 1000

    resultado = resultado.groupby(col_linha)[col_extensao].agg(extensao_produtiva_mensal = 'sum').reset_index()
    return resultado[[col_linha, 'extensao_produtiva_mensal']]



def custo_rodagem_por_linha(
        extensao_percorrida: pd.Series,
        ppu: float,
        pre: float,
        npn: int,
        vdu: float,
        beta: int,
) -> pd.Series:
    """
    dataframe: base de dados com a extensão por linha
    ppu: preço unitário pneu novo.
    pre: preco unitário recapagem.
    npn: numero de pneus por veiculo
    vdu: vida util do pneu (km)
    beta: numero recapagens do pneu
    """

    resultado = extensao_percorrida.copy()

    pnu = ppu * npn
    rec = beta * pre * npn

    resultado = resultado * (pnu + rec) / vdu

    return resultado

def variabilidade_tempo_operacional(
        dataframe: pd.DataFrame,
        col_data: str, 
        col_linha: str,
        col_inicio: str,
        col_fim: str
) -> np.ndarray:
    """
    df: DataFrame completo 
    col_data: coluna da data da viagem
    col_linha: coluna de linhas
    col_inicio: coluna horario de inicio da viagem
    col_fim: coluna do horario de fim da viagem
    """

    df = dataframe.copy()

    inicio_viagem = pd.to_datetime(df[col_data] + ' ' + df[col_inicio] + ':00', format='%d/%m/%Y %H:%M:%S')
    fim_viagem = pd.to_datetime(df[col_data] + ' ' + df[col_fim] + ':00', format='%d/%m/%Y %H:%M:%S')

    fim_viagem = np.where(inicio_viagem > fim_viagem, fim_viagem + timedelta(days=1), fim_viagem)

    df['tempo_viagem'] = ( fim_viagem - inicio_viagem ).dt.total_seconds()/60

    resultado = df.groupby(col_linha)['tempo_viagem'].agg(mu='mean', sigma='std').reset_index()

    resultado['cv'] = resultado['sigma']/resultado['mu']

    return resultado

def _garante_segundos(serie: pd.Series) -> pd.Series:
    """Completa 'HH:MM' -> 'HH:MM:SS' quando faltam os segundos; deixa 'HH:MM:SS' como esta."""
    tem_segundos = serie.str.count(':') == 2
    return serie.where(tem_segundos, serie + ':00')

def _filtra_data_com_maior_numero_viagens(
        dataframe: pd.DataFrame,
        col_data: str = 'viagem',
        col_linha: str = 'linha'
) -> pd.Dataframe:
    df = dataframe.copy()
    resultado = df.groupby([col_data, col_linha])[col_linha].count().rename('qnt_viagem').reset_index()

    idx_dia_mais_viagem = resultado.groupby(col_linha)['qnt_viagem'].idxmax()
    dias_mais_viagens = resultado.loc[idx_dia_mais_viagem, [col_linha, col_data]]

    return df.merge(dias_mais_viagens, on=[col_linha, col_data])

def folga_recarga_garagem(
          dataframe: pd.DataFrame,
          col_inicio: str = None,
          col_fim: str = None,
          col_linha: str = None,
          filtra_dia_mais_viagem = False,
          col_data = None
) -> pd.DataFrame:

     if col_linha == None:
          raise ValueError('Informe a coluna das linhas')

     if col_inicio == None:
          raise ValueError('Informe a coluna referente ao horario de saida das viagens')

     if col_fim == None:
        raise ValueError('Informe a coluna referente ao horario de fim das viagens')

     if dataframe.empty:
          raise ValueError('Dataframe informado esta vazio')

     df = dataframe.copy()

     if filtra_dia_mais_viagem:
         if col_data == None:
             raise ValueError('Para filtrar a data informe a coluna que contém as informações de data.')
         
         df = _filtra_data_com_maior_numero_viagens(
             df, 
             col_data=col_data,
             col_linha=col_linha
         )

     inicio = pd.to_timedelta(_garante_segundos(df[col_inicio]))
     fim = pd.to_timedelta(_garante_segundos(df[col_fim]))

     # Viagens que atravessam o dia necessitam ser corrigidas
     condicoes = (fim < inicio) & (inicio.dt.components.hours == 23)
     fim = pd.Series(
        np.where(condicoes, fim + pd.Timedelta(days=1), fim),
        index=fim.index
     )

     hi = inicio.groupby(df[col_linha]).min().rename('Hi')
     ui = fim.groupby(df[col_linha]).max().rename('Ui')

     resultado = pd.concat([hi, ui], axis=1).reset_index()

     folga_td = pd.Timedelta(hours=24) - (resultado['Ui'] - resultado['Hi'])
     resultado['folga_recarga'] = folga_td.dt.total_seconds() / 60

     return resultado[[col_linha, 'folga_recarga']]


def tempo_recarga_necessario(
        capacidade_bateria: float,
        potencia_carregador: float,
        conectores_carregador: int,
        percentual_bateria: float
) -> float:
    """
    capacidade_bateria: capacidade da bateria do veículo (kWh)
    potencia_carregador: potencia do carregador (kW)
    conectores_carregador: número de conectores simultaneos por carregador.
    percentual_bateria: percentual da bateria ja consumido pela linha antes do retorno a garagem
    """

    return (capacidade_bateria * (1-percentual_bateria)) / (potencia_carregador/conectores_carregador)

def percentual_bateria_consumido(
        Ci: float, 
        km_diario_por_veiculo: float,
        capacidade_bateria: float
) -> float:
    """
    Ci: consumo do veículo
    km_diario_por_veiculo: quilometragem percorrida por dia por um unico veiculo da linha
    bm: capacidade da bateria do veiculo (kWh)
    """

    return (Ci * km_diario_por_veiculo) / capacidade_bateria
