
from __future__ import annotations
import pandas as pd
from pathlib import Path


def get_trips_for_routes(
        trips: pd.DataFrame,
        routes: pd.DataFrame,
        route_short_names: list[str],
        direction_id: str | None = None,
        service_id: str | None = None
) -> pd.DataFrame:

    routes_ids = routes[routes['route_short_name'].isin(route_short_names)][["route_id", "route_short_name"]]
    encontrados = set(routes_ids["route_short_name"])
    faltando = set(route_short_names) - encontrados

    if faltando:
        raise ValueError(f"route_short_name não encontrado em routes.txt: {faltando}")

    time_table = trips.merge(routes_ids, on="route_id")

    if direction_id is not None:
        time_table = time_table[time_table["direction_id"] == direction_id]
        
    if service_id is not None:
        time_table = time_table[time_table["service_id"] == service_id]
 
    return time_table.reset_index(drop=True)






    
    


