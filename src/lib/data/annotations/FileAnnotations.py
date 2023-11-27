
import os

import pandas as pd 
from .ABCAnnotations import Annotations
from config.settings.annotations import get_annotation_settings


ANNOTATION_SETTINGS = get_annotation_settings()

class PandaAnnoations(Annotations):
    """
    Annotations are strucutred by the organism. 
    The filstructure contains subfolders in the path_annotations.
    The foldername should be UPID des proteomes von uniprot. 
    """
    def __init__(self) -> None:
        super().__init__()
        self._readAnnotations() 

    def _readAnnotations(self) -> None:
        """"""
        dir_path  = ANNOTATION_SETTINGS.path_annotations    

        organisms = [organisms for organisms in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path,organisms))]
        print(organisms)
        self._annotations = organisms

    def _readAnnotationFile(self, organism_id : str) -> pd.DataFrame:
        """"""
        annotation_folder = os.path.join(ANNOTATION_SETTINGS.path_annotations,organism_id)
        annotation_files = os.listdir(annotation_folder)
        if len(annotation_files) == 0: raise ValueError("No annotations detected.")
        loaded_files = []
        for annotation_file in annotation_files:
            try:
                X = pd.read_csv(os.path.join(annotation_folder,annotation_file),sep=ANNOTATION_SETTINGS.annotation_file_seperator)
            except: print("Skipping file - could not read",annotation_file)
            key_names_found = [key_name for key_name in ANNOTATION_SETTINGS.annotation_feature_id_columns if key_name in X.columns]
            if len(key_names_found) == 0: raise ValueError("None of the key names found!!")
            X.set_index(key_names_found [0],drop=True,inplace=True)
            X.index.rename("uniprot_id")    
            loaded_files.append(X)

        annotations = pd.concat(loaded_files,join="outer")

        self._cached_annotations[organism_id] = annotations

    def get_annotations_by_featureID(self, feature_id: str, organism_id: str) -> pd.DataFrame:
        """"""
        if organism_id not in self._annotations: 
            raise ValueError("Organism id not found. No Annotations found.")
        if organism_id in self._cached_annotations:
            annotions = self._cached_annotations[organism_id]
        else:
            annotions = self._readAnnotationFile(organism_id)
    
        if feature_id in annotions.index:
            return annotions.loc[feature_id]
