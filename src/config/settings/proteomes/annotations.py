from pydantic_settings import BaseSettings
from typing import List 
from config.models.annotations.proteome import ProteomeModel




class UniprotAnnotationSettings(BaseSettings):
    """
    Defines the proteomes in a List that should be downloaded from
    the given API_URL Link. By default the Uniprot DB is used. The 
    """
    proteomes : List[ProteomeModel] = [
        ProteomeModel(upid="UP000005640", name="Homo sapiens (Human)", domain="Eukaryota"),
        ProteomeModel(upid="UP000000589", name="Mus musculus (Mouse)", domain="Eukaryota"),
        ProteomeModel(upid="UP000001940", name="Caenorhabditis elegans", domain="Eukaryota"),
        ProteomeModel(upid="UP000002311", name="Saccharomyces cerevisiae (strain ATCC 204508 / S288c) (Baker's yeast)", domain="Eukaryota")
    ]
    uniprotKBAPI_URL :str = "https://rest.uniprot.org/uniprotkb/search"


















