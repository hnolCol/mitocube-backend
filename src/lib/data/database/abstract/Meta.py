from __future__ import annotations

from abc import abstractmethod, ABC
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
import pandas as pd

from config.models.user import UserModel


class MetaABC(ABC):


    @abstractmethod
    def exists(self, tag : str) -> bool:
        "Checks if there are metadata for the submission tag"

    
    @abstractmethod
    def add_owner(self, tag : str, user_tag : str):
        """Add an owner. Since there is only
        a single owner allowed per submission/dataset,
        this replaces the 'old' owner. 

        Parameters
        ----------
        tag : str
            _description_
        user_tag : str
            _description_
        """

    @abstractmethod
    def add_collaborators(self, tag : str, user_tags : List[str]):
        """Adds collaborators to a given
        submission/dataset.

        Parameters
        ----------
        tag : str
            The submission/dataset tag 
        user_tags : List[str]
            The list of collaborators given by a list of tags. 
        """
    
    def add_metatext(self, tag : str, user_tag : str, meta_texts : Dict[str,str]):
        """Adds metatext to the database. 

        Parameters
        ----------
        tag : str
            The submission tag
        user_tag : str
            The user_tag associated with the user that added the metatext
        meta_texts : Dict[str,str]
            The actual metatext as: keys(tags) -> values(Content)
        """
        
    @abstractmethod
    def add_samples_attributes(self, meta_data):
        """Adds sample attributes to the database.

        Parameters
        ----------
        meta_data : _type_
            _description_
        """
       
       
    @abstractmethod    
    def get(self, tags : List[str]) -> List[Dict]:
        """Retrieve the minimal information about a dataset. 

        Parameters
        ----------
        tags : List[str]
            The submission/dataset_tag for which the metadata should be retrieved.

        Returns
        -------
        List[Dict]
            The minimal metadata of a dataset in a list.
            If all tags exist, the length is equal to len(tags) 

        Raises
        ------
        Exception
            If the database throws an Exception
        """
        
        
    @abstractmethod
    def get_dataset_attributes(self, tag : str) -> Dict[str,List[str]]:
        """Returns the dataset attributes. Meta data that are 
        true for all samples. 

        Parameters
        ----------
        tag : str
            The submission tag

        Returns
        -------
        Dict[str,List[str]]
        Dataset attributes given by their tags (keys) and
                values are given in a List of str (tags). 
                Example:
                
                {
                    "att_protease" : [trypsin,lysc]
                }

        """
     
     
    @abstractmethod
    def get_metatext(self, tags : List[str]) -> pd.DataFrame:
        """Returns the metatext that is associated with 
        the provided dataset_tags

        Parameters
        ----------
        tags : List[str]
            The tag associated with the dataset. 
            w
        Returns
        -------
        pd.DataFrame
            The metatext given in a pandas data frame with 
            the following columns:
            
                - 'tag' (str) : The dataset tags. If multiple metatext are
                present for the tag, each metatext is in a separate row (e.g. duplicates)
                
                - 'meta_tag' (str) : The tag that was given to the metatext 
                
                - 'content' (str) : The actual content of the metatext. 
        """
        
        
    @abstractmethod
    def get_owner(self, tag : str) -> UserModel:
        """Returns the owner of the submission tag. If submission does not
        exist an ValueError is thrown."""
        
    @abstractmethod
    def get_users(self, tag : str) -> List[UserModel]:
        "Returns all users associated with the submission tag (owner, collaborators.)"
        
    @abstractmethod
    def get_sample_attributes(self, tag : str) -> Dict[str,Dict[str,List[int]]]:
        """Describes the attributes that were assigned to each sample.

        Parameters
        ----------
        tag : str
            The dataset tag for which the sample attributes
            should be returned. 

        Returns
        -------
        Dict[str,Dict[str,List[int]]]
            ```
            {'attribute_tag' : {'attribute_value_tag' : List[sample indices (int) ]}}
            ```
        """
        
    @abstractmethod
    def get_sample_genotypes(self, tag : str) -> Dict[str,Dict[str,List[int]]]:
        """Returns the sample attributes. 
        
        Parameters
        ----------
        tag : str
            The submission tag for which the genotypes should be returned. 
        """

        
    # def get_sample_attributes(self, tag : str):
    @abstractmethod
    def get_sample_attributes_and_genotypes(self, tag : str, as_sample_map : bool = True) -> Tuple[Dict[str,Dict[str,int]],pd.DataFrame]|Dict[str,Dict[str,int]]:
        """Returns the attributes and genotypes per sample. 

        Parameters
        ----------
        tag : str
            The submission tag for which the genotypes and sample attributes should be returned. 
        as_sample_map : bool, optional
            If True, a sample map (pd.DataFrame) is returned that has the following props/columns
                - index (int) - the sample index 
                - attribute_tags as columns 
            , by default True

        Returns
        -------
        Tuple[Dict[str,Dict[str,int]],pd.DataFrame]|Dict[str,Dict[str,int]]
            If as_sample_map, a tuple is returned with 
            
                a) Dict with:
                    - keys (str) - attribute_tag (example: att_compound)
                    - values (Dict[str,List[int]])
                        - keys : attribute_value_tag (example dmso, Uniprot id)
                        - values : list of sample index that were annotated with the attribute_value
                b) pd.DataFrame with 
                    - index (int) - the sample index 
                    - attribute_tags as columns 
                    
            else:
                a) Dict with:
                    - keys (str) - attribute_tag (example: att_compound)
                    - values (Dict[str,List[int]])
                        - keys : attribute_value_tag (example dmso, Uniprot id)
                        - values : list of sample index that were annotated with the attribute_value
            
        Example
        ------- 
        
        """
        
    @abstractmethod
    def update_owner(self, tag : str, user_tag : str):
        """Updates the ownership of data submission/dataset.

        Parameters
        ----------
        tag : str
            The tag associated with the submission / dataset 
        user_tag : str
            The tag that defines the user. 

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        Exception
            If the database query resulted in an error. 
        """
    