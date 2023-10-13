from pydantic_settings import BaseSettings
from typing import List 
from config.models.annotations.proteome import Proteome




class UniprotAnnotationSettings(BaseSettings):
    """
    Defines the proteomes in a List that should be downloaded from
    the given API_URL Link. By default the Uniprot DB is used. The 
    """
    proteomes : List[Proteome] = [
        Proteome(upid="UP000005640", name="Homo sapiens (Human)", domain="Eukaryota"),
        Proteome(upid="UP000000589", name="Mus musculus (Mouse)", domain="Eukaryota"),
        Proteome(upid="UP000001940", name="Caenorhabditis elegans", domain="Eukaryota")
    ]
    uniprotKBAPI_URL :str = "https://rest.uniprot.org/uniprotkb/search"


















