from functools import lru_cache
from pydantic_settings import BaseSettings


class KeyFigures(BaseSettings):
    """
    BaseSettings that indicate which key figures should be provided
    to the user in the index page. 

    Parameters
    ----------
    
    """
    number_proteins : bool = True
    number_submissions : bool = True
    number_published_datasets : bool = True
    number_genotypes : bool = True
    number_users : bool = True
    turnover_time : bool = True
    
@lru_cache()
def get_key_figure_settings():
    return KeyFigures()