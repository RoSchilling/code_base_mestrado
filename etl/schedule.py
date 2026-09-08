"""
Pipeline de quadro de horários e headway
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import Literal



def horarios_saida(
    trips_filtrados: pd.DataFrame,
    stop_times: pd.DataFrame,
    service_id: Literal['uteis', 'sabado', 'domingo'] = None, 
    dict_service_id: dict = None
) -> pd.DataFrame:
    if dict_service_id == None:
        raise ValueError('Informe o dicionário do service_id.')

    
    stop_times = stop_times.astype({"stop_sequence": int})
    primeiras_paradas = stop_times.loc[stop_times.groupby("trip_id")["stop_sequence"].idxmin()]
    primeiras_paradas = primeiras_paradas.reset_index(drop=True)

    qnt_service_id = len(trips_filtrados['service_id'].unique())
    if qnt_service_id == 1:
        pass

    elif service_id == None:
        print('Service_id não informado, considerando dia útil')
        trips_filtrados = trips_filtrados[trips_filtrados['service_id'] == dict_service_id['uteis']]

    else:
        if service_id not in dict_service_id.keys():
            raise ValueError('Informe um service ID valido')
        
        trips_filtrados = trips_filtrados[trips_filtrados['service_id'] == dict_service_id[service_id]]
    
    resultado = primeiras_paradas.merge(
        trips_filtrados[["trip_id", "trip_headsign", "service_id", "route_short_name"]],
        on="trip_id",
    )
    resultado = resultado.sort_values("departure_time").reset_index(drop=True)

    

    return resultado
 
def headway_por_hora(horarios: pd.DataFrame, col_route_name: str = "route_short_name") -> pd.DataFrame:
    horarios = horarios.copy()
    horarios["hora"] = (horarios["departure_time"].str.slice(0, 2).astype(int)) % 24
 
    contagem = horarios.groupby(["hora", col_route_name]).agg(n_partidas=('trip_id', 'nunique')).reset_index()
    contagem["headway_min"] = 60 / contagem["n_partidas"]
    return contagem



    
    