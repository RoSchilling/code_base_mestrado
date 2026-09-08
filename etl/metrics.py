import pandas as pd
import os 
import numpy as np


def conversao_extensao_percorrida(
        extensao: pd.Series[int],
) -> pd.Series:
        
        extensao = extensao.astype(float)

        return extensao/1000

