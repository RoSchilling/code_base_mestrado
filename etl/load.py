"""
Importação dos dados do GTFS

"""

from __future__ import annotations
import pandas as pd
from pathlib import Path
import os

linhas_move = ['10', '50','51','52','61','62','63','64','65','66', '67', '68', '82', '83D','83P','85','1031',
               '5106', '5107', '5201', '5250', '5401', '5550', '6030', '6031', '6150', '6350', '8101', '8251', '8550', '8551']


TIPOS_DIAS = {
    "uteis": "307679",
    "sabado": "307681", 
    "domingo": "307680",
}

def load_gtfs_tables(gtfs_dir: str | Path, 
                     files: list[str] | str | None = None, 
                     chunk_size:int | None = None,
                     filtros: dict[str, tuple[str, set[str]]] | None = None) -> dict[str, pd.DataFrame]:
    """
        Carrega um ou mais arquivos GTFS como DataFrame.

        **gtfs_dir**: diretorio com os arquivos GTFS salvos.
    
        **files**: nome(s) de arquivo, com ou sem ".txt" (ex: "routes" ou "routes.txt" — os dois funcionam). 
        Pode ser uma string única ou uma lista.
    
        **chunk_size**: se None (padrão), lê o arquivo inteiro de uma vez, 
        recomendado para arquivos pequenos (routes, trips, calendar). Se definido,
        lê em lotes desse tamanho, aplicando o filtro (se houver) a cada
        lote antes de concatenar — use isso pra stop_times.txt.
    
        **filtros**: dict opcional {nome_do_arquivo: (coluna, valores_aceitos)}.
        Só entra em ação para arquivos lidos com chunk_size definido; para
        arquivos lidos de uma vez, o filtro é aplicado depois, sobre o
        DataFrame já completo (menos vantagem de memória, mas ainda funciona
        se você quiser usar o mesmo parâmetro pros dois casos).
    
        Retorna: dict {nome_do_arquivo_sem_extensão: DataFrame}.
    """


    if files == None:
        raise ValueError('Necessário apresentar pelo menos o nome de um arquivo gtfs')

    if isinstance(files, str):
        files = [files]

    dict_gtfs = {}
    gtfs_dir = Path(gtfs_dir)

    for file in files:
        name = file.split('.')[0] if '.txt' in file else file
        caminho = gtfs_dir / (file if '.txt' in file else file + '.txt')
        filtro_deste_arquivo = filtros.get(name) if filtros is not None else None

        if chunk_size is None:
            df = pd.read_csv(caminho, dtype=str)
            if filtro_deste_arquivo is not None:
                coluna, valores = filtro_deste_arquivo
                df = df[df[coluna].isin(valores)]
            dict_gtfs[name] = df

        else:
            lotes_filtrados = []
            for lote in pd.read_csv(caminho, dtype=str, chunksize=chunk_size):
                if filtro_deste_arquivo is not None:
                    coluna, valores = filtro_deste_arquivo
                    lote = lote[lote[coluna] == valores]

                if not lote.empty:
                    lotes_filtrados.append(lote)

            dict_gtfs[name] = (
                pd.concat(lotes_filtrados, ignore_index=True) if lotes_filtrados else pd.DataFrame()
            )



    return dict_gtfs

def load_mco_table(mco_dir: str | Path, filtro_linhas: list[str] | str | None = None, **kwargs) -> pd.DataFrame:
    mco_dir = Path(mco_dir)

    list_mco = []

    for file in os.listdir(mco_dir):
        df = pd.read_csv(mco_dir / file, **kwargs)

        df.columns = [col.strip().lower() for col in df.columns]
        if filtro_linhas is not None:
            df = df[df['linha'].isin(filtro_linhas)]

        list_mco.append(df)

    return pd.concat(list_mco)