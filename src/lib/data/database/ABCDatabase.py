from __future__ import annotations

from abc import abstractmethod, ABC
from collections import OrderedDict

from typing import List, Dict, Optional, Tuple, Literal 
from deprecated import deprecated

import pandas as pd

from lib.data.dataset.ABCDataset import MCDataset
from lib.DesignPatterns import SingletonABCMeta 

from config.settings.db import get_db_settings
from config.models.attributes import AttributeModel, AttributeUnitResponseModel
from config.models.submissions.submissions import DatasetSubmissionModel
from config.models.user import UserModel 
from config.models.filter import Filter

DB_SETTINGS = get_db_settings()

## load database 
class DatabaseABC(ABC):
    meta : MetaABC = None 
    user : UserABC = None 
    attributes : AttributesABC = None
    filters : FilterABC = None
    def __init__(self):
        """The abstract database class that defines
        all the required methods as abstractmethod in order
        to make the backend function. You can use this as a guideline 
        to implement your own database class. 
        
        Class Attributes
        ----------
        Attributes
            Sub database classes:
            
                - 'meta' (MetaABC) : Metadata class. 
                - 'user' (UserABC) : User class which handles user verification, addition and blocking. 
                - 'attributes' (AttributesABC) : Attribute database class to manage attributes.
        Raises
        ------
        NotImplementedError
            If an attribute is missing. 
        TypeError
            If an attribute is not of the correct type. 
        """
        if self.meta is None:
            raise NotImplementedError("A database class must have the meta attribute defined.")
        
        if not isinstance(self.meta, MetaABC):
            raise TypeError("The attribute meta must be an instance of MetaABC")
        
        if self.user is None:
            raise NotImplementedError("A database class must have the user attribute defined.")
        
        if not isinstance(self.user, UserABC):
            raise TypeError("The attribute user must be an instance of UserABC")
    
        if self.attributes is None:
            raise NotImplementedError("A database class must have the attributes class attribute defined.")
        
        if not isinstance(self.user, AttributesABC):
            raise TypeError("The attribute class must be an instance of AttributesABC")
        
        if self.filters is None:
            raise NotImplementedError("A database class must have the filter attribute defined.")
        
        if not isinstance(self.filters, FilterABC):
            raise TypeError("The attribute filters must be an instance of FilterABC")
        
    @abstractmethod
    def dataset_exists(self, tag : str) -> bool:
        """Checks if the tag is associated with a dataset. 
        Use this function to check if a tag exists. 

        Parameters
        ----------
        tag : str
            The dataset/submission tag. 

        Returns
        -------
        bool
            If the tag is associated with a dataset/submission.
        """
        
    @abstractmethod
    def get_dataset_tags(self) -> List[str]:
        ""
        
    @abstractmethod
    def get_meta_data(self, tag : str) -> DatasetSubmissionModel:
        ""
    
    
    @abstractmethod
    def insert_dataset(self, data_table : pd.DataFrame, tag : str):
        ""
    
    @abstractmethod
    def insert_meta(self, meta_data : DatasetSubmissionModel):
        ""
        
class SubmissionFilterABC(ABC):
    
    @abstractmethod
    def get_all_tags(self, limit : int = None) -> List[str]:
        """Returns all tags in the database. 

        Parameters
        ----------
        limit : int, optional
            _description_, by default None

        Returns
        -------
        List[str]
            The submission tags in the database

        Raises
        ------
        Exception
            _description_
        """
        
    @abstractmethod
    def get_counts(self, tags : List[str] = None, by : Literal["user","state","attribute","attribute_value"] = "state") -> pd.DataFrame:
        """Returns the number of submissions/dataset associated with a certain param tag. A common
        use case would be to ask the question how many and which dataset/submission tags are associated with 
        a certain user or state or attribute_value (for example: Hypoxia, LC-Instrument)

        Parameters
        ----------
        tags : List[str]
            List of tags to consider, if None all submission are considered, by default None
        by : Literal[&quot;user&quot;,&quot;state&quot;,&quot;attribute&quot;,&quot;attribute_value&quot;], optional
            group counts by specific param. For example, setting by = "user" will list all submissions by 
            all users, by default "state"

        Returns
        -------
        pd.DataFrame
            The submission counts as a data frame, contains the following columns:
            ```
                - 'tag' (str) : The associated tag (user.tag, state.tag, attribute.tag or attribute_value.tag)
                - 'count' (int) : The count of submissions associated with the tag. 
                - 'tags' (List[str]) : The list of dataset or submission tags associated with the given tag.
            ```
        Raises
        ------
        Exception
            If the database query throws an exception. 
        """
        
        
    @abstractmethod
    def get(self,
            state : List[int] = None, 
            attribute_value_tag : List[str] = None, 
            attribute_tag : List[str]= None, 
            user_tag : List[str] = None, 
            protein_tag : List[str] = None, 
            genotype_tag : List[str] = None,
            limit : int = 10) -> List[str]:
        """_summary_

        Parameters
        ----------
        state : List[int], optional
            _description_, by default None
        attribute_value_tag : List[str], optional
            _description_, by default None
        attribute_tag : List[str], optional
            _description_, by default None
        user_tag : List[str], optional
            _description_, by default None
        protein_tag : List[str], optional
            _description_, by default None
        genotype_tag : List[str], optional
            _description_, by default None
        limit : int, optional
            _description_, by default 10

        Returns
        -------
        List[str]
            _description_

        Raises
        ------
        Exception
            _description_
        """

class AttributesABC(ABC):
    
    @abstractmethod
    def get(self, tags : List[str] = ["att_compound","att_protease"]) -> List[AttributeModel]:
        """Finds attributes by their tags. If the tag is not in the 
        database it is simply ignored. 

        Parameters
        ----------
        tags : List[str], optional
            The attribute tags, by default ["att_compound","att_protease"]

        Returns
        -------
        List[AttributeModel]
            The list of attributes associated with the provided tags. Please note
            that if the tag is not found, the attribute is simply ignored.

        Raises
        ------
        Exception
            _description_
        """
    
        
    @abstractmethod
    def get_mandatory_attributes(self)->List[AttributeModel]:
        """Mandatory attributes that are required to fill in
        at the submission state. 

        Returns
        -------
        List[AttributeModel]
            The required attributes for a submission.

        Raises
        ------
        Exception
            If the database query returns an error. 
        """
        
    @abstractmethod
    def unit(self, tag : str) -> List[AttributeUnitResponseModel]:
        """_summary_

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        Dict
            _description_

        Raises
        ------
        Exception
            _description_
        """
        
    
class UserABC(ABC):
    
    @abstractmethod
    def block_user_by_tag(self, tag : str) -> bool:
        ""
    
    def exists(self, tag : str) -> bool:
        return self.is_user(tag)
    
    @abstractmethod
    def get_user_by_email(self, email : str) -> None|UserModel:
        """Returns the user in the database using the database. 

        Parameters
        ----------
        email : str
            The email that is associated with an user.

        Returns
        -------
        None|UserModel
            None if not found otherwise the user. 
        """

    @abstractmethod
    def get_user_by_tag(self, tag : str) -> None|UserModel:
        ""
        
    @abstractmethod
    def get_users_by_tags(self, tags : List[str] = None) -> List[UserModel]:
        """Get all users from the database that match the given tags.
    
        Parameters
        ----------
        tags : List[str]
            The tags associated with users. If the tag is not present in the database
            it is simply ignored. If None, it returns all users in the database, default None

        Returns
        -------
        List[UserModel]
            Users that are associated with the given tags.
            

        Raises
        ------
        Exception
            If the database query resulted in an error. 
        """
    
    @abstractmethod 
    def is_user(self, tag : str) -> bool:
        """Checks if a user is associated with the 
        given tag. Use this method to check if a user
        exists. The function ```exists``` is an alias. 

        Parameters
        ----------
        tag : str
            The user tag to test.

        Returns
        -------
        bool
            If the user with the given tag is present.

        Raises
        ------
        Exception
            If the database query resulted in an error. 
        """
class MetaABC(ABC):
    
    def __init__(self, *args, **kwargs) -> None:
        ""
        
    def get(self, tags : List[str]) -> List[Dict]:
        """Retrieve the minimal information about a dataset. 

        Parameters
        ----------
        tags : List[str]
            The dataset_tag for which the metadata should be retrieved.

        Returns
        -------
        List[Dict]
            The minimal metadata of a dataset. 

        Raises
        ------
        Exception
            If the database throws an Exception
        """
    
    def update_owner(self, dataset_tag : str, user_tag : str):
        """Updates the ownership of data submission/dataset.

        Parameters
        ----------
        dataset_tag : str
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

class FilterABC(ABC):
    """Filters handle the available 
    filter (set of proteins) that can 
    be used by the user to create a subset of the 
    data. For example, the MitoCarta 3.0 
    is simply a list of proteins that can be used
    to subset a volcano plot or a heatmap. 
    Filters are proteome_id sepcific. 
    """

    @abstractmethod
    def add(self, protein_tags : List[str], 
            proteome_id : str, 
            filter_tag : str, 
            description : str,
            publication : Optional[str] = None) -> Tuple[bool,str]:
        """Adds a filter to the database. 

        Parameters
        ----------
        protein_tags : List[str]
            _description_
        proteome_id : str
            _description_
        filter_tag : str
            _description_
        description : str
            _description_
        publication : Optional[str], optional
            _description_, by default None
        """
    
    @abstractmethod
    def get(self, tag : str = None) -> List[Filter]:
        """Returns the available filters/protein sets
        from the database

        Parameters
        ----------
        tag : str
            The filter tag

        Returns
        -------
        List[Filter]
            The filters detected in the database. All if tag is None. 
            Otherwise a subset. 
        """
        
    @abstractmethod    
    def get_features(self, tag : str) -> List[FeatureNeoModel]:
        """Returns the list of proteins as a feature model that
        are associated with the provided tag. 

        Parameters
        ----------
        tag : str
            The filter tag. 

        Returns
        -------
        List[FeatureNeoModel]
            _description_

        Raises
        ------
        Exception
            If the database query returns an error. 
        """

    
    
class DatasetABC(ABC):
    def __init__(self, *args, **kwargs) -> None:
        ""

    @abstractmethod
    def get(self, tags : List[str]) -> List[str]:
        """Returns the minimal meta information of a dataset

        Parameters
        ----------
        tags : List[str]
            The list of tags that the minimal metadata should be returned. 

        Returns
        -------
        List[str]
            _description_
        """
    
    @abstractmethod
    def get_metatext(self, tags : List[str]) -> pd.DataFrame:
        """Returns the metatext that is associated with 
        the provided dataset_tags

        Parameters
        ----------
        tags : List[str]
            The tag associated with the dataset. 
            
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
    
    #     self.factory = Neo4JFactory(driver = driver)
    #     self._attributes = attributes
    #     self.create_title_search_index() ##put in creator!! TODO 
    
    # def get(self, tags : List[str]):
    #     """Returns the minimal meta information of a dataset node (e.g. properties)

    #     Parameters
    #     ----------
    #     tags : List[str]
    #         The list of tags that the minimal metadata should be returned. 
    #     """
    #     query = (
    #         "MATCH (d:Dataset) "
    #         "WHERE d.tag in $tags "
    #         "RETURN properties(d) "
    #     )
    
    #     metadata = self._driver.execute_query(query,result_transformer_=Result.value, tags = tags)
        
    # def get_metatext(self, tags : List[str]):
    #     ""
    #     query = (
    #         "MATCH (d:Dataset) "
    #         "WHERE d.tag in $tags "
    #         "MATCH (d)<-[:DESCRIBES]-(m:Metatext)-[:HAS_CONTENT]->(c:Content) "
    #         "WHERE c.tag = d.tag "
    #         "RETURN d.tag as tag, m.tag as meta_tag, c.content as content "
    #     )
        
    #     meta_text = self._driver.execute_query(query,tags=tags,result_transformer_=Result.to_df)
    #     return meta_text
    
    # def add_metatext(self, dataset_tag : str, user_tag : str, meta_texts : Dict[str,str]):
    #     "" 
    #     meta_texts = [{"tag" : tag, "content" : content} for tag,content in meta_texts.items() if content != ""]
        
    #     query = (
    #         "UNWIND $meta_texts as metatext "
    #         "MATCH (d:Dataset {tag : $dataset_tag}) "
    #         "MERGE (m:Metatext {tag : metatext.tag }) "
    #         "MERGE (d)<-[r_d:DESCRIBES]-(m) "
    #         "SET r_d.created_at = timestamp(), r_d.user_tag = $user_tag "
    #         "WITH d, m, metatext "
    #         "MERGE (m)-[:HAS_CONTENT]-(c:Content {tag : d.tag}) "
    #         "SET c.content = metatext.content"
    #     )
        
    #     self._driver.execute_query(query, dataset_tag = dataset_tag, meta_texts = meta_texts, user_tag = user_tag, routing_="w")
        
    # def add_samples_genotypes(self, meta_data : DatasetSubmissionModel = meta):
    #     """_summary_

    #     Parameters
    #     ----------
    #     meta_data : DatasetSubmissionModel, optional
    #         _description_, by default meta
    #     """
        
    #     samples_genotypes = meta_data.samples_genotypes
    #     if len(samples_genotypes) == 0: return 
    #     sample_names = meta_data.sample_names
        
    #     sample_genotypes_props = [
    #         {"tag" : genotype_tag, 
    #          "sample_name" : sample_names[sample_index]} for genotype_tag, sample_indices in samples_genotypes.items() for sample_index in sample_indices]
        
    #     query = ( 
    #             "MATCH (d:Dataset {tag : $dataset_tag}) "
    #             "UNWIND $props as prop "
    #             "MATCH (g:Genotype {tag : prop.tag}) "
    #             "MATCH (s:Sample {tag : prop.sample_name}) "
    #             "MERGE (d)-[:HAS_GENOTYPE]-(g) "
    #             "MERGE (g)<-[r:HAS_GENOTYPE]-(s) "
    #             "ON CREATE "
    #             "SET r.created_at = timestamp() "
    #             )

    #     self._driver.execute_query(query, props = sample_genotypes_props, dataset_tag = meta_data.label)
    
    # def add_samples_attributes(self, meta_data : DatasetSubmissionModel = meta):
    #     ## add sample attributes
    #     attributes  = self._attributes.get_attributes_by_tag(tags = list(meta.samples_attributes.keys()))
    #    # print(attributes)
    #    #attribute_value_tags = set()
    #     attributes_allow_feature_tags = [a.tag for a in attributes if a.has_features_value]
    #     sample_attributes_data = []
        
    #     attributes_to_connect = []
        
    #     for n, (attribute_tag, attribute_value) in enumerate(meta_data.samples_attributes.items()):
    #         attributes_to_connect.append({"attribute_tag" : attribute_tag, "values" : []})
    #         for attribute_value_tag, sample_idx in attribute_value.items():
    #             attr_value_tag = attribute_value_tag.split(":")[-1]
    #             attributes_to_connect[n]["values"].append(attr_value_tag)
                
    #             for idx in sample_idx:
    #                 sample_name = meta.sample_names[idx]
    #                 sample_attributes_data.append(
    #                     {
    #                         "attribute_tag" : attribute_tag,
    #                         "index" : n,
    #                         "sample_name" : sample_name, 
    #                         "attribute_value_tag" :  attr_value_tag##matching proteins by tag.
    #                     }
    #                 )

    #    # print(sample_attributes_data)
    #     with self._driver.session() as session:
    #         session.execute_write(self._add_sample_attrs,sample_attributes_data)
            
        
    #    # print(attribute_value_tags)
        
    #     query = (
    #         "MATCH (d:Dataset) "
    #         "WHERE d.tag = $dataset_tag "
    #         "UNWIND $attributes as attr "
    #         "MATCH (a:Attribute) "
    #         "WHERE a.tag = attr.attribute_tag "
    #         "MERGE (d)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a) "
    #         "WITH d, a, attr "
    #         "MATCH (av: AttributeValue) "
    #         "WHERE av.tag in attr.values "
    #         "MERGE (d)-[r:HAS_ATTRIBUTE_VALUE]-(av) "
    #         "SET r.attribute_tag = a.tag "
    #         "WITH a, av "
    #         "MERGE (a)-[:HAS_VALUE]->(av) "
    #     )
        
        
    #     self._driver.execute_query(query,dataset_tag=meta_data.label, 
    #                                attributes = attributes_to_connect,
    #                                database_="neo4j", 
    #                             routing_="w", 
    #                                )
        
        
    
    # @staticmethod
    # def _add_sample_attrs(tx, sample_attributes_data, relation_label : str = "HAS_SAMPLE_ATTRIBUTE_VALUE"):
    #     query = (
    #         f"UNWIND $props as prop "
    #         "MATCH (s:Sample {tag : prop.sample_name}) "
    #         "MATCH (a:AttributeValue {tag : prop.attribute_value_tag}) "
    #         "WITH s,a, prop "
    #         f"MERGE (s)-[r:{relation_label} {{index : prop.index, attribute_tag : prop.attribute_tag}}]->(a) "
    #         "RETURN count(r) as count"
    #     )
        
    #     r = tx.run(query,props = sample_attributes_data, relation_label = relation_label)
    #     #print("sample attributes!!")
        
        
        
    # def get_sample_attributes_and_genotypes(self, tag:str, as_sample_map : bool = True):
    #     ""
    #     query = (
    #         "MATCH (d:Dataset {tag : $tag})-[:HAS_SAMPLE]->(s:Sample)  "
    #         "MATCH (g:Genotype)<-[:HAS_GENOTYPE]->(s) "
    #         "RETURN s.index as sample_index, s.text as sample_text, g.tag as tag, -1 as attribute_index, 'att_genotype' as attribute_tag, g.text as text, false as is_feature  "
    #         "ORDER BY attribute_index, sample_index "
    #         "UNION ALL "
    #         "MATCH (d:Dataset {tag : $tag}) "
    #         "MATCH (d)-[:HAS_SAMPLE]->(s:Sample) "
    #         "MATCH (s)-[r:HAS_SAMPLE_ATTRIBUTE_VALUE]->(av:AttributeValue|Protein)<-[:HAS_VALUE]-(a:Attribute) "
    #        # "MATCH (g:Genotype)<-[:HAS_GENOTYPE]->(s) "# <-[:HAS_VALUE]-(a:Attribute)
    #         "RETURN s.index as sample_index, s.text as sample_text, av.tag as tag, r.index as attribute_index, a.tag as attribute_tag, av.text as text, 'Protein' in labels(av) as is_feature  " #g.tag as ag, g.tex as text, 
    #         "ORDER BY attribute_index, sample_index"
    #     )
    #     r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.to_df)
    #     print(r)
    #     if as_sample_map:
    #         result = []
    #         #pd.DataFrame().set_index()
    #         r["tag"] = r["attribute_tag"] + ":" + r["tag"]
    #         for attribute_index, data in r.set_index("sample_index").groupby("attribute_index"):
    #             print(data)
                
    #             grouped = data.groupby(data.index)["tag"].agg(lambda x: ";".join(x))
    #             print(grouped)
            
            
    #     return r 
        
    # def get_sample_genotypes(self, tag : str):
    #     "" 
    #     #(g)<-[r:HAS_GENOTYPE]-(s)
    #     query = (
    #         "MATCH (d:Dataset {tag : $tag}) "
    #         "MATCH (d)-[:HAS_SAMPLE]->(s:Sample)-[r:HAS_GENOTYPE]->(g:Genotype) "# <-[:HAS_VALUE]-(a:Attribute)
    #         "RETURN s.index as sample_index, s.text as sample_text, g.tag as tag, g.text as text, 'att_genotype' as attribute_tag "
    #         "ORDER BY sample_index "
    #     )
    #     r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.to_df)
    #     return r

        
    # def get_sample_attributes(self, tag : str):
        
    #     query = (
    #         "MATCH (d:Dataset {tag : $tag}) "
    #         "MATCH (d)-[:HAS_SAMPLE]->(s:Sample)-[r:HAS_SAMPLE_ATTRIBUTE_VALUE]->(av:AttributeValue|Protein)<-[:HAS_VALUE]-(a:Attribute) "
    #         "RETURN s.index as sample_index, s.text as sample_text, av.tag as attribute_value_tag, r.index as index, a.tag as attribute_tag, 'Protein' in labels(av) as is_feature "
    #         "ORDER BY r.index, s.index"
    #     )
        
        
    #     r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.to_df)
    #     return r 

        
        

    # def create_title_search_index(self):
    #     query = (
    #         f"CREATE FULLTEXT INDEX  titleSearch IF NOT EXISTS FOR (d:Dataset) ON EACH [d.title] "
    #         "OPTIONS {"
    #         "indexConfig: {"
    #         "    `fulltext.analyzer`: 'english', "
    #         "    `fulltext.eventually_consistent`: true "
    #         "}"
    #         "}"    
    #     )
        
    #     with self._driver.session() as session:
    #         r = session.run(query) 
            
            
    # def add_owner(self, user_tag : str, dataset_tag : str):
    #     ""
    #     query = (
    #         "MATCH (u:User) "
    #         "WHERE u.tag = $user_tag "
    #         "MATCH (d:Dataset) "
    #         "WHERE d.tag = $dataset_tag "
    #         "MERGE (u)-[r:OWNS]-(d) "
    #         "SET r.created_at = timestamp() "
    #     )
        
    #     self._driver.execute_query(query, user_tag = user_tag, dataset_tag = dataset_tag, routing_ = "w", database_ = "neo4j")


            
    # def add_collaborators(self, user_tags : List[str], dataset_tag : str):
    #     ""
    #     query = (
    #         "MATCH (u:User) "
    #         "WHERE u.tag in $user_tags "
    #         "MATCH (d:Dataset) "
    #         "WHERE d.tag = $dataset_tag "
    #         "MERGE (u)-[r:IS_PART]-(d) "
    #         "SET r.created_at = timestamp() "
    #         "WITH u,d "
    #         "MATCH (owner:User)-[:OWNS]->(d) "
    #         "MERGE (owner)-[:COLLABORATES_WITH]-(u) "
    #         "RETURN d.tag"
            
    #     )
        
    #     r,_,_ = self._driver.execute_query(query, user_tags = user_tags, dataset_tag = dataset_tag, routing_ = "w", database_ = "neo4j")




class InvalidDatasetLabelError(Exception):
    pass

class MCAttributes(metaclass=SingletonABCMeta):
    """"""
    # Todo: Write documentation

    @staticmethod
    def getAttributeDatabase() -> MCAttributes:
        """
        Returns a (singleton) database object depending on the settings. Either A PandaFileDatabase or PostgreSQLDatabase.
        """
        if DB_SETTINGS.db_handler == "postgresql":
            from lib.data.database.ProstgreSQLDatabase import PostgreSQLAttributes
            return PostgreSQLAttributes()
        elif DB_SETTINGS.db_handler == "pandafiles":
            from lib.data.database.FileDatabase import PandaFileAttributes
            return PandaFileAttributes()
        else:
            raise Exception("Invalid MitoCubeDatabase configuration. Only 'postgresql' and 'pandafiles' are supported.")

    @abstractmethod
    def getAttributes(self, sort : bool = True, sort_by : str = "priority", tags : List[str] = None) -> pd.DataFrame:
        """
        Returns the full attribute table as Panda DataFrame.
        
        Parameters
        ----------
        sort : bool, default True
            If true, the attributes will be sorted by the column priority. 
            
        Returns
        -------
        pd.DataFrame 
            The attributes in the database
        """
        pass

    @abstractmethod
    def getAttributeValues(self, tags : List[str] = None) -> pd.DataFrame:
        """
        Returns the full attribute value table as Panda DataFrame.
        """
        pass

    @abstractmethod
    def getAttributeTable(self) -> pd.DataFrame:
        """
        Returns a table combining attributes and attributes values as Panda DataFrame.
        """
        pass

    @abstractmethod
    def getMandatoryAttributesForStage(self, stage : int) -> List[str]:
        """
        Returns a list of tags of mandatory attributes required from defined stage
        """
        pass

    @abstractmethod
    def getMandatoryActivationAttributes(self) -> List[str]:
        """
        Returns a list of tags of mandatory attributes.
        """
        pass

    @abstractmethod
    def getMandatorySubmissionAttributes(self) -> List[str]:
        """
        Returns a list of tags of mandatory attributes.
        """
        pass

    @abstractmethod
    def update(self):
        """
        Triggers a reload of the database.
        """
        pass

    #@abstractmethod
    # def add(self):
   ##     """
    #     Triggers a reload of the database.
    #     """
    #     pass

    # @abstractmethod
    # def remove(self):
    #     """
    #     Triggers a reload of the database.
    ##    """
    #     pass


class MCDatabase(metaclass=SingletonABCMeta):
    """"""
    # Todo: Write documentation

    def __init__(self):  # ToDo: Check DataType Date
        """Singleton Constructor"""
        # Todo: Write documentation

        self._cached_datasets = OrderedDict()

        # otherTestiTestValue = 69
        # def doTestiTest():
        #     print(" >>> doTestiTest() !!!")
        #     return otherTestiTestValue
        # self.testitest = ExpiringValue[int](expireTime=timedelta(seconds = 5),
        #                                     value=42,
        #                                     updateProcess = doTestiTest)

    def clearCachedDatasets(self):
        """
        Clears the cached of (memory) stored datasets.
        """
        # Todo: Write documentation
        self._cached_datasets.clear()

    @abstractmethod
    def doesLabelExists(self, dataset_label : str) -> bool:
        """
        Returns true if the dataset label exists.
        """
        pass

    @abstractmethod
    @deprecated(reason="Will be remove. Please use classes related to MCAttribute in the future.")
    def getSampleAttributeJSON(self, grouping_json: Dict = {}) -> Dict:
        """"""
        # Todo: Write documentation
        pass

    def getDataset(self, label: str) -> MCDataset:
        """
        Returns a dataset object with the defined label. If it is cached, take it from memory, otherwise read it from the long-term database. Raises an InvalidDatasetLabelError exception if the dataset (label) is not found.
        """
        dataset = None

        if label in self._cached_datasets.keys():
            dataset = self._cached_datasets[label]
            self._cached_datasets.move_to_end(label, last=True)
        else:
            # if DB_SETTINGS.db_handler == "postgresql":
            #     from lib.data.dataset.PostgreSQLDataset import PostgreSQLDataset
            #     dataset = PostgreSQLDataset(label=label, loadFromDatabase=True)
            # elif DB_SETTINGS.db_handler == "pandafiles":
            if DB_SETTINGS.db_handler == "pandafiles":
                from lib.data.dataset.PandaDataset import PandaFileDataset
                dataset = PandaFileDataset(label=label, loadFromDatabase=True)
            else:
                raise Exception("Invalid MitoCubeDatabase configuration. Only 'postgresql' and 'pandafiles' are supported.")

            if len(self._cached_datasets) > int(100):
                self._cached_datasets.popitem(last=False)

            self._cached_datasets[label] = dataset

        return dataset

    @abstractmethod
    def getJSONDatasets(self, labels: List[str] = []) -> Dict[str, DatasetSubmissionModel]:
        """"""
        # Todo: Write documentation
        pass

    def getDatasets(self, labels: List[str] = []) -> Dict[str, MCDataset]:
        """
        Returns a dictionary of the datasets defined in labels. 
        Uses the database labels as keys. Labels with no matching label in the database will be silently ignored.

        Parameters
        ----------
        labels : List[str], default []
            The dataset labels to be returned. If a label is missing, it will be ignored. 

        Returns
        -------
        Dict[str, MCDataset]
            The datasets as a dictionary with labels as keys. Any missing label will not exists in the output.
        """
        # Todo: Write documentation
        datasets = {}

        if len(labels) < 1:
            labels = self.getDataLabels()

        for label in labels:
            if label in self._cached_datasets.keys():
                datasets[label] = self._cached_datasets[label]
            elif self.doesLabelExists(label): # otherwise it will return None which we would then have again to check for.
                datasets[label] = self.getDataset(label)

        return datasets

    @abstractmethod
    @deprecated(reason="Will be remove. Please use classes related to MCAttribute in the future.")
    def getDatasetAttributeJSON(self, tag: str = "") -> Dict:
        """"""
        # Todo: Write documentation
        pass

    @abstractmethod
    def getDataLabels(self, sort_createdOn_desc: bool = False) -> List[str]:
        """
        Equivalent to getAllDataIDs() but returns a list of database string labels instead of numerical ids.
        """
        # Todo: Write documentation
        pass

    @abstractmethod
    def getDatasetsWithLabels(self,
                              n_limit: int = 42,
                              n_offset: int = 0,
                              sort_createdOn_desc: bool = False) -> List[str]:
        """"""
        # Todo: Write documentation
        pass

    @staticmethod
    def getDatabase() -> MCDatabase:
        """
        Returns a (singleton) database object depending on the settings. Either A PandaFileDatabase or PostgreSQLDatabase.
        """
        if DB_SETTINGS.db_handler == "postgresql":
            from lib.data.database.ProstgreSQLDatabase import PostgreSQLDatabase
            return PostgreSQLDatabase()
        elif DB_SETTINGS.db_handler == "pandafiles":
            from lib.data.database.FileDatabase import PandaFileDatabase
            return PandaFileDatabase()
        else:
            raise Exception("Invalid MitoCubeDatabase configuration. Only 'postgresql' and 'pandafiles' are supported.")

    @staticmethod
    def getDatasetObject() -> MCDataset:
        if DB_SETTINGS.db_handler == "postgresql":
            from lib.data.dataset.PostgreSQLDataset import PostgreSQLDataset
            return PostgreSQLDataset
        elif DB_SETTINGS.db_handler == "pandafiles":
            from lib.data.dataset.PandaDataset import PandaFileDataset
            return PandaFileDataset
        else:
            raise Exception("Invalid MitoCubeDatabase configuration. Only 'postgresql' and 'pandafiles' are supported.")



    @abstractmethod
    @deprecated(reason="Will be remove. Please use classes related to MCAttribute in the future.")
    def getMandatorySubmissionAttributes(self) -> List[AttributeModel]:
        """
        Returns a list of mandatory attributes.
        """
        pass

    @abstractmethod
    def getNumberOfDatasets(self) -> int:
        """
        Returns numbers of datasets saved in the database.
        """
        # Todo: Write documentation
        pass

    @abstractmethod
    def getDatasetsWithFeature(self, feature_key : str) -> List:
        """
        Returns all datasets that contain a specific feature as List.

        Parameters
        ----------

        feature_key : str 
            The feature key (e.g. Uniprot ID)
        """
        pass

    @abstractmethod
    def getSize(self) -> int:
        """
        Returns used size for data in bytes.
        """
        # Todo: Write documentation
        pass

    def insert_meta(self, obj: MCDataset,  meta : DatasetSubmissionModel, update : bool = False):
        """Inserts metadata in the database. 
        It is mandatory to call this before you can insert a 
        dataset when using the panda file database.

        Parameters
        ----------
        meta : DatasetSubmissionModel
            _description_
        """
        obj.write_json(meta=meta, update=update)

    def insert(self, obj: MCDataset):
        """
        Adds/Writes new MCDataset to the database.
        """
        # Todo: Write documentation
        obj.write()
