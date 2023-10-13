
from config.settings.proteomes.annotations import UniprotAnnotationSettings
from services.annotations.uniprot import download_proteome_annotations
from services.paths.utils import check_dir_exists, join_path
import pandas as pd 

def download_annotations_from_uniprot(fileName : str = "uniprot_annotations.txt", verbose : bool = True):
    """Download Annotations form Uniprot"""
    settings = UniprotAnnotationSettings()
    proteomes = settings.proteomes
    uniprotKB_URL = settings.uniprotKBAPI_URL

    proteinAnnotations = []

    for proteome in proteomes:
        if verbose: print("Donwloading Uniprot Annotations")
        if verbose: print(proteome)
        proteomeAnnotations = download_proteome_annotations(annotationUrl=uniprotKB_URL, proteome=proteome)
        numberProteins = proteomeAnnotations.index.size
        if verbose:print(f"Annotations for {numberProteins} protein entries were downloaded from")
        proteinAnnotations.append(proteomeAnnotations)

    X = pd.concat(proteinAnnotations) if len(proteinAnnotations) > 1 else proteinAnnotations[0]

    exists, path = check_dir_exists("resources/proteomes/annotations",addRootPath=True,makeParents=True)
    if exists:
        X.to_csv(join_path(path,fileName),sep="\t")
    if verbose : print("Annotations downloaded and saved.")
