import os 
import json 
from threading import Lock 
from typing import List, Optional, Union
from config.settings.db import get_db_settings 
from config.models.genotype import GenotypeModel
from config.models.annotations.feature import FeatureModel
from lib.data.genotype.ABCGenotypeDatabase import MCGenotypes

from services.json import read_json, save_json

DB_SETTINGS = get_db_settings()



class PandaFileGenotype(MCGenotypes):
    """ProteoType of Genotype Database 
    ATTENTION
    ---------
    Returns Singleton.
    Saves the attribute values at the moment, in real life it should save the tags only? 
    
    Parameters
    ----------
    MCGenotypes : _type_
        _description_
    """
    def __init__(self) -> None:
        super().__init__()
        self._lock = Lock()  # Synchronization primitive to make it multi-threading safe
    
    def _import(self):
        """_summary_
        """
        genotype_file_path = DB_SETTINGS.genotype_file
        genotype_data =  read_json(genotype_file_path) #must be a list TODO check
        self._genotypes = [GenotypeModel(**genotypeProps) for genotypeProps in genotype_data]
        
    def _save(self):
        """
        """
        self._lock.acquire()
        genotype_file_path = DB_SETTINGS.genotype_file
        genotype_data = [genotype.model_dump(exclude_none=True) for genotype in self._genotypes]
        save_json(genotype_data,file_path=genotype_file_path)
        self._lock.release()
        
    def add(self, genotype : GenotypeModel) -> bool:
        """Addds a genotype to the database. 

        Parameters
        ----------
        proteome_id : str
            _description_
        genotype : _type_
            _description_

        Returns
        -------
        bool
            True if the addition of the genotype to the database was successful. 
        """
        self._genotypes.append(genotype)
        self._save()
        return self._genotypes
        
        
    
    def get(self, label : Optional[str] = None, proteome_ids : Optional[List[str]] = None, feature_key : Optional[str] = None, feature : Optional[FeatureModel] = None) ->  List[GenotypeModel] | GenotypeModel:
        """Returns the genotypes. By a proteome_id since genotypes are defined by certain
        features which are define for a proteome. 
        If feature_key is provided, the genotypes for the specific feature_key are returned
        
        Returns
        -------
        GenotypeModel
            If label is given
        List[GenotypeModel]
            If anything else but level is given.
            
        Raises
        ------
        ValueError 
            If a label is provided but was not found in the database or multiple were found.
        """
        self.update()
        if label is not None:
            genotypes_found_by_label = [genotype for genotype in self._genotypes if genotype.label == label]
            if len(genotypes_found_by_label) != 1: raise ValueError("Either the genotype labels are not unique or the label is not found.")
            return genotypes_found_by_label[0]
        
        elif feature_key is not None:
            return [genotype for genotype in self._genotypes if genotype.proteome_id in proteome_ids and genotype.feature.key == feature_key]

        elif feature is not None:
            return [genotype for genotype in self._genotypes if genotype.proteome_id in proteome_ids and genotype.feature.key == feature.key]
    
        elif proteome_ids is not None:
            return [genotype for genotype in self._genotypes if genotype.proteome_id in proteome_ids]
        
    def update(self):
        """
        Triggers a reload of the database.
        """
        self._import()