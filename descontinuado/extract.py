
from __future__ import annotations
import pandas as pd
from pathlib import Path



def find_routes_id(routes: pd.DataFrame, routes_short_name:str) -> str:
    """
    Função que garante que exista apenas uma rota para determinda linha
    """

    find = routes[routes["route_short_name"] == routes_short_name]
    assert len(find) == 1

    return find

def filter_trips(
        trips: pd.DataFrame,
        route_id: str,
        direction_id: str | None = None,
        service_id: str | None = None,
) -> pd.DataFrame:

    filtro = trips[trips["route_id"] == route_id]

    if direction_id is not None:
        filtro = filtro[filtro["direction_id"] == direction_id]

    if service_id is not None:
        filtro = filtro[filtro["service_id"] == service_id]

    return filtro

def get_trips_for_route(
        trips: pd.DataFrame,
        routes: pd.DataFrame,
        route_short_name: str,
        direction_id: str | None = None,
        service_id: str | None = None
) -> pd.DataFrame:
    """Função construida para ler apenas """


    route = find_routes_id(routes, route_short_name)
    route_id = route['route_id'].iloc[0]

    time_table = filter_trips(
        trips,
        route_id,
        direction_id,
        service_id
    )

    
    for col in route.columns:
        time_table[col] = route[col].iloc[0]

    return time_table