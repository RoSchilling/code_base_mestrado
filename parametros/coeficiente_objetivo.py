import pandas as pd
import numpy as np 
from typing import Literal


def custo_operacional(
        Ci: float,
        T: float,
        Ki: float,
        Ri: float,
        Aci: float
) -> float:
    """
    Ci: consumo do veículo em kWh/km
    T: tarifa aplicada pela concessionária de energia
    Ki: quilometragem rodada mensal
    Ri: custo da rodagem mensal
    Aci: custo com peças e acessórios mensal
    """
    return (Ci * T * Ki) + Ri + Aci 

def atendimento_a_demanda(
        Pi: int,
        Ei: float,
        Di: int 
) -> float:
    """
    Pi: passageiros transportados por mês
    Ei: extensão produtiva no mês
    Di: número de ônibus necessário para operar a linha 
    """

    return Pi * Ei / Di


def recarga_por_linha(
        dataframe: pd.DataFrame,
        tempo_recarga: pd.Series,
        col_linha: str = 'linha',
        col_foi = 'folga_recarga'
) -> pd.DataFrame:
    resultado = dataframe.copy()
    resultado['c4i'] = resultado[col_foi] - tempo_recarga
    return resultado

