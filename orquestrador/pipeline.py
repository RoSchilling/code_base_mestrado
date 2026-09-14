from typing import Literal
import pandas as pd
import numpy as np

import parametros.load as load
import parametros.extract as extract
import parametros.fleet as fleet
import parametros.schedule as schedule
import parametros.metrics as metrics

def tabela_parametros(
        dataframe: pd.DataFrame,
        dict_gtfs: dict[str, pd.DataFrame],
        dict_service_id: dict,
        ppu: float,
        pre: float,
        npn: int,
        vdu: float,
        beta: int,
        gtfs_route: str = 'routes',
        gtfs_trips: str = 'trips',
        gtfs_stop_times: str = 'stop_times',
        col_data: str = 'viagem',
        col_linha: str = 'linha',
        col_inicio: str = 'saida',
        col_fim: str = 'chegada',
        col_extensao: str = 'extensao',
        tipo_metragem: Literal['metros', 'km'] = 'metros',
        filtra_dia_mais_viagem: bool = False,
        filtra_mes: bool = False,
        dias_uteis_mes: int = 22,
        Ci: float = None,
        capacidade_bateria: int = 320,
        conectores_carregador: int = 2,
        potencia_carregador: int = 160,
) -> pd.DataFrame:
    df = dataframe.copy()
    linhas_move = load.linhas_move

    trips = extract.get_trips_for_routes(
        dict_gtfs[gtfs_trips], 
        dict_gtfs[gtfs_route], 
        route_short_names=linhas_move
        )
    
    horarios = schedule.horarios_saida(
        trips, 
        dict_gtfs[gtfs_stop_times],
        dict_service_id=dict_service_id
        )
    
    headway = schedule.headway_por_hora(
        horarios
        )
    
    frota_necessaria = fleet.frota_por_demanda_todas_linhas(
        headway,
        df
    )

    variabilidade_operacional = metrics.variabilidade_tempo_operacional(
        df, 
        col_data, 
        col_linha, 
        col_inicio, 
        col_fim
        )

    recarga = metrics.folga_recarga_garagem(
        dataframe=df[[col_data, col_linha, col_inicio, col_fim]],
        col_inicio=col_inicio,
        col_fim=col_fim,
        col_linha=col_linha,
        filtra_dia_mais_viagem=filtra_dia_mais_viagem,
        col_data = col_data
        )

    extensao = metrics.extensao_produtiva_mensal(
        df,
        col_linha=col_linha,
        col_extensao=col_extensao,
        tipo_metragem=tipo_metragem,
        filtra_mes=filtra_mes,
        col_data=col_data,
    )

    rodagem = extensao[[col_linha]].copy()
    rodagem['Ri'] = metrics.custo_rodagem_por_linha(
        extensao['extensao_produtiva_mensal'],
        ppu=ppu,
        pre=pre,
        npn=npn,
        vdu=vdu,
        beta=beta
    )

    df_resultado = (
        frota_necessaria
        .merge(variabilidade_operacional, on=col_linha, how='outer')
        .merge(recarga, on=col_linha, how='outer')
        .merge(extensao, on=col_linha, how='outer')
        .merge(rodagem, on=col_linha, how='outer')
    )

    df_resultado['km_por_veiculo'] = (
        df_resultado['extensao_produtiva_mensal']
        / (dias_uteis_mes * df_resultado['frota_necessaria'])
    )

    df_resultado['percentual_bateria'] = metrics.percentual_bateria_consumido(
        Ci=Ci, 
        km_diario_por_veiculo=df_resultado['km_por_veiculo'],
        capacidade_bateria=capacidade_bateria
    )

    df_resultado['tempo_recarga'] = metrics.tempo_recarga_necessario(
        capacidade_bateria=capacidade_bateria,
        potencia_carregador=potencia_carregador,
        conectores_carregador=conectores_carregador,
        percentual_bateria=df_resultado['percentual_bateria']
    )

    return df_resultado