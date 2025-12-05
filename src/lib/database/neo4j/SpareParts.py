from neo4j import Driver, Result 
from typing import List
import pandas as pd 

from lib.database.abstract.SpareParts import SparePartsABC
from config.models.spareparts import SparepartModel, SparepartResponseModel, SparepartInsertModel, SparepartBaseModel

class Neo4jSpareParts(SparePartsABC):
    
    def __init__(self, driver : Driver):
        
        self._driver = driver 
    
    def _utils_insert_from_file(self, file_path : str = "", *args, **kwargs):
        ""

        spare_parts = pd.read_csv(file_path, *args, **kwargs)
        #creating the models here checks if all the types are correct. 
        spare_part_models = [SparepartModel(**s, s = [s["text"],s["description"]]).model_dump(exclude_none=True) for s in spare_parts.to_dict(orient="records")] 
        query = (
            "UNWIND $parts as sp_props "
            "MERGE (s:SparePart {tag : sp_props.tag}) "
            "ON CREATE "
            "SET s.created_at = timestamp(), s.description = sp_props.description, s.priority = sp_props.priority, s.s = sp_props.s, s.text = sp_props.text, s.company = sp_props.company, "
            "s.price = sp_props.price, s.product_id = sp_props.product_id, s.link = sp_props.link "
            "ON MATCH "
            "s.price = sp_props.price, s.product_id = sp_props.product_id, s.link = sp_props.link "
            "RETURN count(s) as count"
        )
    
        r = self._driver.execute_query(query, parts = spare_part_models, routing_="w", result_transformer_=Result.value)
        print(f"The database contains {r} spare parts")
        
    def exists(self, tag : str) -> bool:
        """
        Check if a spare part with the given tag exists.

         Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        bool
            True if the spare part exists, otherwise False.
        """
        
        query = ("WITH EXISTS {(s:SparePart {tag : $tag})} as sp_exists " 
                "RETURN sp_exists "
        )
        
        exists = self._driver.execute_query(query, tag = tag, routing_ = "r")    
        return exists[0]
        
    def find(self, search_string : str = None, limit : int = 20, is_active: bool = True) -> List[str]:
        """Find spare part by a search string. 

        Parameters
        ----------
        search_string : str, optional
            The query string, by default ""
        limit : int, optional
            The maximum number of spare parts to be returned., by default 20

        Returns
        -------
        List[str]
            The spare part tags. 
        """
        query = (
            "MATCH (s:SparePart) "
            "WHERE s.is_active = $is_active "
        )

        if search_string is not None and len(search_string) > 0:
            query += "AND s.s CONTAINS $search_string "

        query += "RETURN s.tag "

        if limit is not None:
            query += "LIMIT $limit"
               
        sp_tags = self._driver.execute_query(query, 
                                              search_string = search_string.lower(), 
                                              limit = limit,
                                              is_active=is_active, 
                                              routing_="r", 
                                              result_transformer_=Result.value)
        
        return sp_tags
    
    def get(self, tag : str) -> SparepartResponseModel:
        """
        Get the complete spare part model.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        SparepartResponseModel
            A model containing all spare part data.
        """

        
        if not self.exists(tag):
            raise ValueError("Tag not associated with a spare part.")
        
        query = (
            "MATCH (s:SparePart {tag : $tag}) "
            "return properties(s) "
        )
        
        spareparts = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_= Result.value)
        
        if len(spareparts) == 0: 
            raise ValueError("Even though the tag exists, the database returned none.")
        
        return SparepartResponseModel(**spareparts[0])
    
    def get_text(self, tag: str) -> str:
        """
        Gets the spare part text by its tag. 

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        str
            The text of the spare part.
        """


        query = (
            "MATCH (s:SparePart {tag: $tag}) "
            "RETURN s.text as text"
        )

        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]
    

    def get_description(self, tag: str) -> str:
        """
        Get the description of the spare part by its tag. 

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        str
            The description of the spare part.
        """

        query = (
            "MATCH (s:SparePart {tag: $tag}) "
            "RETURN s.description as description"
        )

        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]


    def get_company(self, tag: str) -> str:
        """
        Get the name of the company of the spare part by its tag.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        str
            The company of the spare part.
        """

        query = (
            "MATCH (s:SparePart {tag: $tag}) "
            "RETURN s.company as company"
        )
        
        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]
    

    def get_product_id(self, tag: str) -> str:
        """
        Get the product ID of the spare part by its tag.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        str
            The product ID.
        """

        query = (
            "MATCH (s:SparePart {tag: $tag}) "
            "RETURN s.product_id as product_id"
        )
        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]
    

    def get_price(self, tag: str) -> float | int:
        """
        Get the price of the spare part by its tag.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        float | int
            The price of the spare part.
        """

        query = (
            "MATCH (s:SparePart {tag: $tag}) "
            "RETURN s.price as price "
        )

        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]
    

    def get_link(self, tag: str) -> str:
        """
        Get the URL for the spare part.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        str
            A URL string pointing to a product page or resource.
        """

        query = (
            "MATCH (s:SparePart {tag: $tag}) "
            "RETURN s.link as link "
        )
        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]
    
    def insert(self, sparepart : SparepartInsertModel, user_tag : str, is_active : bool = True) -> bool:
        """
        Insert a new spare part into the database.

        Parameters
        ----------
        sparepart : SparepartInsertModel
            The model containing all required fields for creating a spare part.

        Returns
        -------
        bool
            True if the insertion was successful, otherwise False.
        """
  

        query = (
            "MATCH (u:User {tag: $user_tag}) "
            "MERGE (s:SparePart {tag: $tag}) "
            "ON CREATE SET s.is_active = $is_active, "
            "              s.created_at = timestamp(), "
            "              s.description = $description, "
            "              s.company = $company, "
            "              s.product_id = $product_id, "
            "              s.price = $price, "
            "              s.link = $link, "
            "              s.s = toLower($text) + ' ' + toLower($description), "
            "              s.text = $text "
            "ON MATCH SET  s.modified_at = timestamp(), "
            "              s.description = $description, "
            "              s.company = $company, "
            "              s.product_id = $product_id, "
            "              s.price = $price, "
            "              s.link = $link, "
            "              s.s = toLower($text) + ' ' + toLower($description), "
            "              s.text = $text "
            "WITH u, s "
            "CREATE (u)-[:CREATED {created_at: timestamp()}]->(s) "
            "CREATE (u)-[:MODIFIED {modified_at: timestamp()}]->(s) "
            "RETURN true AS ok "
    )

        ok = self._driver.execute_query(query,
                                        tag=sparepart.tag,
                                        user_tag=user_tag,
                                        is_active=is_active,
                                        description=sparepart.description,
                                        company=sparepart.company,
                                        product_id=sparepart.product_id,
                                        price=sparepart.price,
                                        link=str(sparepart.link) if sparepart.link is not None else "",
                                        text=sparepart.text,
                                        routing_="w",
                                        result_transformer_=Result.value
        )

        return ok[0]

    def update(self, sparepart: SparepartBaseModel, user_tag: str) -> bool:
        """
        Update an existing spare part.

        Parameters
        ----------
        tag : str
            Tag of the spare part to update.
        sparepart : SparepartModel
            The updated spare part fields.

        Returns
        -------
        bool
            True if the update was successful.
        """
        print(sparepart)
        if not self.exists(sparepart.tag):
            raise ValueError("Spare part does not exist and cannot be updated. Please use insert method.")

        

        query = (
                "MATCH (s:SparePart {tag: $tag}) "
                "SET "
                "   s.description = $description, "
                "   s.company     = $company, "
                "   s.product_id  = $product_id, "
                "   s.price       = $price, "
                "   s.link        = $link, "
                "   s.text        = $text, "
                "   s.modified_at = timestamp(), "
                "   s.s           = toLower($text) + ' ' + toLower($description) "
                "WITH s "
                "MATCH (u:User {tag: $user_tag}) "
                "CREATE (u)-[:MODIFIED {modified_at: timestamp()}]->(s) "
                "RETURN true AS ok"
        )

        ok = self._driver.execute_query(query,
                                        tag=sparepart.tag,
                                        user_tag=user_tag,
                                        description=sparepart.description,
                                        company=sparepart.company,
                                        product_id=sparepart.product_id,
                                        price=sparepart.price,
                                        link=str(sparepart.link) if sparepart.link is not None else "",
                                        text=sparepart.text,
                                        routing_="w",
                                        result_transformer_=Result.value
        )

        return ok[0]
    
    def delete(self, tag : str, is_active : bool = False) -> bool:
        """
        Delete a spare part from the database.

        Parameters
        ----------
        tag : str
            The tag of the spare part to delete.

        Returns
        -------
        bool
            True if the delete operation was successful.
        """
        
        query = (
            "MATCH (s:SparePart {tag: $tag}) "
            "SET s.is_active = $is_active "
            "RETURN true AS ok "
           
        )

        result = self._driver.execute_query(query,
                                            tag=tag,
                                            is_active=is_active,
                                            routing_="w",
                                            result_transformer_=Result.value
        )

        return True if result is not None else False

