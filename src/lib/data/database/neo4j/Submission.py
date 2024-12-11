from typing import Literal, List , Dict
from neo4j import Driver, Result 
import pandas as pd 
import datetime
from config.models.searches import FulltextSearchResult

from lib.data.database.abstract.Submission import SubmissionFilterABC, SubmissionABC, SubmissionSummaryABC
from lib.data.database.abstract.Meta import MetaABC
from lib.data.database.abstract.Attributes import AttributesABC
from lib.data.database.abstract.Proteomes import ProteomesABC
from lib.data.database.Neo4JDatabase import Neo4JFactory
from config.enums.states import SubmissionStatesEnums
from config.models.submissions.submissions import DatasetSubmissionModel
from config.exceptions.Proteome import ProteomeNotFoundError

from services.units import extract_user_input
class Neo4JSubmissions(SubmissionABC):
    def __init__(self, driver : Driver, meta : MetaABC, proteomes : ProteomesABC) -> None:
        self._meta = meta 
        self._driver = driver
        self._proteomes = proteomes
        
    def count(self) -> int:
        "Counts the total number of submissions in the database"
        
        query = (
            "MATCH (submission:Submission) "
            "RETURN count(submission)"
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value)
        if isinstance(r,list) and len(r) > 0:
            return r[0]
        return 0 
        
    def delete(self, tag: str) -> bool:
        return super().delete(tag)
    
    def exists(self, tag: str) -> bool:
        "Checks if the submission exists."
        query = (
            "WITH EXISTS {(submission:Submission {tag : $tag})} as submission_exists "
            "RETURN submission_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    
    def get_samples(self, tag : str) -> List[str]:
        "" 
        query = (
            "MATCH (submission:Submission)-[:HAS_SAMPLE]->(sample:Sample) "
            "WHERE submission.tag = $tag "
            "RETURN collect(properties(sample)) "
            
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag=tag)
        
        return r[0]
    
    
    def get_state(self, tag: str) -> SubmissionStatesEnums:
        
        query = (
            "MATCH (submission:Submission)-[:IN_STATE]->(s:State) "
            "WHERE submission.tag = $tag "
            "RETURN s.tag "
        )
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        print(r)
        if len(r) == 0: raise ValueError("No state found.")
        return r[0]
    
    def insert(self, submission: DatasetSubmissionModel) -> bool:
        ""
        
        submission_tag = submission.tag
        sample_names = submission.sample_names
        dataset_attribute_input = submission.dataset_attribute_input
        genotypes_added = 0 
        sample_attributes_added = 0 
        
        dataset_props = {
            "title" : submission.title, 
            "n_samples" : submission.n_samples, 
            "created_at" : submission.created_on,
            "state" : submission.state, 
            "n_replicates" : len(set(submission.replicates))
            }
        #get the state tag 
        #state_tag =  SubmissionStatesEnums(submission.state).name
        if "att_proteome" not in submission.dataset_attributes:
            raise ProteomeNotFoundError("The proteome dataset attribute was not found.")
        
        for proteome_tag in submission.dataset_attributes["att_proteome"]:
            if not self._proteomes.exist(proteome_tag):
                raise ProteomeNotFoundError(f"The proteome {proteome_tag} was not found in the database. Please add it before inserting the submission.")
        
        samples = [{"tag" : sample_name, "props" : {"index" : idx, "replicate" : submission.replicates[idx], "text" : sample_name}} for idx,sample_name in enumerate(sample_names)]
        dataset_attributes =  [tag for tag in submission.dataset_attributes.keys()]

                
        dataset_attribute_values = [{"attribute_value_tag" : tag, #remove!! att_ is history 
                                     "attribute_tag" : attribute_tag, 
                                     "trait_value" : extract_user_input(dataset_attribute_input[attribute_tag][tag]) if attribute_tag in dataset_attribute_input and dataset_attribute_input[attribute_tag][tag] else []} 
                                    for attribute_tag,tags in submission.dataset_attributes.items() for tag in tags]
        
        dataset_attributes_units = [x for x in dataset_attribute_values if isinstance(x["trait_value"],list) and len(x["trait_value"]) > 0]
        
        query = (
            "MERGE (submission:Submission {tag : $submission_tag}) "
            "SET submission += $dataset_props "
            "WITH submission "
            "MATCH (state:State {tag : $state_tag}) "
            "MERGE (submission)-[r_in_state:IN_STATE]->(state) "
            "SET r_in_state.created_at = timestamp(), r_in_state.user_tag = $user_tag "
            "WITH submission "
            "UNWIND $samples as sample_name "
            "MERGE (s:Sample {tag : sample_name.tag}) "
            "SET s += sample_name.props "
            "SET s.created_at = timestamp() "
            "WITH s, submission "
            "MERGE (s)<-[:HAS_SAMPLE]-(submission) "   
            "WITH submission "
            "UNWIND $dataset_attributes as attribute_tag "
            "MATCH (a:Attribute {tag : attribute_tag}) "
            "MERGE (submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a) "
            "WITH submission "
            "UNWIND $dataset_attribute_values as attribute_value "
            "MATCH (av:AttributeValue {tag : attribute_value.attribute_value_tag}) "
            "MATCH (a:Attribute {tag : attribute_value.attribute_tag}) "
            "MERGE (submission)-[r:HAS_ATTRIBUTE_VALUE]->(av) "
            "SET r.created_at = timestamp(), r.attribute_tag = a.tag "
            "MERGE (av)-[:HAS_VALUE]-(a) "

            ""
        )
    
        self._driver.execute_query(query, routing_="w", 
                                   samples = samples, 
                                   user_tag = submission.user_tag,
                                   submission_tag = submission_tag, 
                                   dataset_attributes  = dataset_attributes, 
                                   state_tag = submission.state, 
                                   dataset_props = dataset_props, 
                                   dataset_attribute_values = dataset_attribute_values)
        
        
        #add units 
        if len(dataset_attributes_units) > 0:
            query = (
                "MATCH (submission:Submission {tag : $submission_tag}) "
                "UNWIND $dataset_attribute_values AS attribute_value "
                "UNWIND attribute_value.trait_value AS trait "
                "WITH attribute_value, trait "
                "MATCH (av:AttributeValue {tag: attribute_value.attribute_value_tag}) "
                "MATCH (unit:Unit {tag: trait.unit_tag}) "
                "MERGE (av)-[r:HAS_VALUE_OF_UNIT]-(unit) "
                "SET r.value = trait.value, r.submission_tag = $submission_tag, r.unittype_tag = trait.unittype_tag "
                "RETURN av, unit, r "
            )
            r = self._driver.execute_query(query,routing_="w",submission_tag = submission_tag, dataset_attribute_values = dataset_attributes_units, result_transformer_=Result.value)
        
        try:
            self._meta.add_samples_attributes(meta_data=submission)
            sample_attributes_added = 1 
        except Exception as e:
            print(e) 
            print("No sample attributes added ")
        try:
            self._meta.add_samples_genotypes(meta_data=submission)
            genotypes_added = 1 
        except:
            print("No genotypes found")
            
        if genotypes_added == 0 and sample_attributes_added == 0: raise ValueError("Neither genotypes nor sample attributes could be defined for this project. ")
        
        self._meta.add_owner(tag=submission_tag, user_tag=submission.user_tag)
        self._meta.add_collaborators(tag=submission_tag, user_tags=submission.collaborators)
        
        print(submission.metatext)
        
        self._meta.add_metatext(tag=submission_tag, user_tag= submission.user_tag, meta_texts=submission.metatext)
        
        
    def get(self, tag: str) -> DatasetSubmissionModel:
        return super().get(tag)

    
    def update_state(self, tag: str, new_state: SubmissionStatesEnums, user_tag : str) -> bool:
        "Updates the state of a submission."
        query = (
            "MATCH (submission:Submission {tag : $tag})-[r_prev:IN_SATE]->(prevState:State) "
            "MATCH (newState:State {tag : $new_state}) "
            "CREATE (submission)-[r:IN_STATE]->(newState) "
            "SET r.created_at = timestamp(), r.user_tag = $user_tag "
            "WITH r_prev "
            "DELETE r_prev "
        )
        
        try: 
            self._driver.execute_query(query, tag = tag, new_state = new_state, user_tag = user_tag)
        except Exception as e:
            print(e)
            return False 
        return True 
    
    
    def get_correlated_features(self, tags : List[str], 
                                feature_tag : str = None, 
                                filter_tag : str = None,  
                                direction : Literal["positive","negative","both"] = "both", 
                                limit : int = 20, 
                                min_data_points : int = 20):
        """Correlates a feature to all other features 
        by its tag. 

        Parameters
        ----------
        tag : str
            the feature tag. 

        Returns
        -------
        pd.DataFrame
            Correlation analysis with the following columns
                - tag (str) - feature_tag that the given tag was correlated to 
                - pearson (float) - the pearson correlation coefficient 
                - N (int) - The number of data points used to calculate the statistics 
                - t (float) - The t-value
        """
        ## extend to multiple submission tags ? MATCH (submission:Submission )-[:HAS_SAMPLE]-(s:Sample) WHERE submission.tag in $submission_tags 
        query = (
            "MATCH (submission:Submission )-[:HAS_SAMPLE]-(s:Sample) WHERE submission.tag in $submission_tags "
            "MATCH (p_target:Protein {tag : $feature_tag})<-[rp1:QUANTIFIED]-(s:Sample)-[rp2:QUANTIFIED]->(p:Protein) "
        )
        if filter_tag is not None:
            query += "WHERE EXISTS {(p)-[:PART_OF]->(f:Filter {tag : $filter_tag})} "
        query += (
            "WITH collect(rp2.value) as x, collect(rp1.value) as y, p "
            "WITH apoc.coll.zip(x, y) AS pairs, apoc.coll.avg(x) AS meanX, apoc.coll.avg(y) AS meanY, x ,y, p "
            "WHERE size(x) > $min_data_points AND size(y) > $min_data_points "
            "WITH "
            "   [p IN pairs | (p[0] - meanX) * (p[1] - meanY)] AS products, "
            "   [v IN x | (v - meanX)^2] AS xSquaredDiffs, "
            "   [v IN y | (v - meanY)^2] AS ySquaredDiffs, p, size(pairs) as N "
            "WITH "
            "    apoc.coll.sum(products) / "
            "   (SQRT(apoc.coll.sum(xSquaredDiffs)) * SQRT(apoc.coll.sum(ySquaredDiffs))) AS pearson, p, N "
            "RETURN p.tag as tag, round(pearson,2) as pearson, N as N,  pearson * SQRT(N-2) / SQRT(1-pearson^2) as t " 
        )
        if direction == "both": 
            query += "ORDER BY abs(pearson) DESC LIMIT $limit "
        elif direction == "negative":
            query += "ORDER BY pearson ASC LIMIT $limit "
        elif direction == "positive":
            query += "ORDER BY pearson DESC LIMIT $limit "    
                
        r = self._driver.execute_query(query, 
                                       routing_="r", 
                                       result_transformer_=Result.to_df, 
                                       min_data_points = min_data_points, 
                                       filter_tag = filter_tag, 
                                       limit = limit, 
                                       feature_tag = feature_tag, 
                                       submission_tags = tags)
        return r 

class Neo4JSubmissionFilter(SubmissionFilterABC):
    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver
        self._factory = Neo4JFactory(driver=driver)
        
        
    def _add_limit(self, query : str, limit : int = None):
        ""
        if limit is not None : query += "LIMIT $limit"
        return query 
        
    
    def get_all_tags(self, limit : int = None)->List[str]:
        "" 
        query = (
                "MATCH (submission:Submission) "
                "RETURN DISTINCT submission.tag "
            )
        query = self._add_limit(query,limit)
        r = self._driver.execute_query(query, routing_="r",limit=limit,result_transformer_=Result.value)
        return r
    
    def get_counts(self, tags : List[str] = None, by : Literal["user","state","attribute","attribute_value"] = "state") -> pd.DataFrame:
        """Counts the submissions and groups them from the Neo4j database. 

        Parameters
        ----------
        tags : List[str], optional
            The submission tags to use, if None all tags in the database are used, by default None
        by : Literal[&quot;user&quot;,&quot;state&quot;,&quot;attribute&quot;,&quot;attribute_value&quot;], optional
            count the submissions by the given property, by default "state"

        Returns
        -------
        pd.DataFrame
            _description_
        """
        if by == "user":
            query = ("MATCH (n:User) "
                     "MATCH (n)-[:OWNS|IS_PART]->(submission:Submission) ")
        elif by == "state":
            query = ("MATCH (n:State) "
                     "MATCH (n)<-[:IN_STATE]-(submission:Submission) ")
        elif by == "attribute":
            query = ("MATCH (n:Attribute) "
                     "MATCH (n)<-[:HAS_VALUES_FOR_ATTRIBUTE]-(submission:Submission) ")
        elif by == "attribute_value":
            query = ("MATCH (n:AttributeValue) "
                     "MATCH (n)<-[:HAS_ATTRIBUTE_VALUE]-(submission:Submission) ")
        if tags is not None:
            query += "WHERE submission.tag in $tags "
            
        query += "RETURN n.tag as tag, count(submission) as count, collect(submission.tag) as tags "
        
        submission_counts = self._driver.execute_query(query, tags = tags, routing_="r",database_="neo4j",result_transformer_=Result.to_df)
        return submission_counts.set_index("tag")
    
    def filter_by_attribute_value_tags(self, attribute_value_tag : List[str], submission_tags : List[str] = None, limit : int = None)->List[str]:
        ""
        query = (
            "MATCH (submission:Submission)-[:HAS_ATTRIBUTE_VALUE]->(av:AttributeValue) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "WITH submission, COLLECT(DISTINCT av.tag) AS value_tags "
            "WHERE ALL(value_tag in $attribute_value_tags WHERE value_tag in value_tags) "
            "RETURN DISTINCT submission.tag "
        )
        query = self._add_limit(query,limit)
        r,_,_ = self._driver.execute_query(query, attribute_value_tags=attribute_value_tag, submission_tags = submission_tags, limit = limit)
        return [ri.value() for ri in r] 
    
            
    def filter_by_attribute_tags(self, attribute_tag : List[str], submission_tags : List[str] = None, limit : int = None)->List[str]:
        ""
        query = (
            "MATCH (submission:Submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(av:Attribute) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "WITH submission, COLLECT(DISTINCT av.tag) AS value_tags "
            "WHERE ALL(value_tag in $attribute_tags WHERE value_tag in value_tags) "
            "RETURN DISTINCT submission.tag "
        )
        query = self._add_limit(query,limit)
        r,_,_ = self._driver.execute_query(query, attribute_tags=attribute_tag, submission_tags = submission_tags, limit = limit)
        
        return [ri.value() for ri in r] 
    
    def filter_by_genotype_tags(self, genotype_tag : List[str], submission_tags : List[str] = None, limit : int = None) -> List[str]:
        ""
        query = (
            "MATCH (g:Genotype) "
            "WHERE g.tag in $genotype_tags "
            "MATCH (g)<-[:HAS_GENOTYPE]-(submission:Submission) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "RETURN DISTINCT submission.tag "
        )
        query = self._add_limit(query,limit)
        r,_,_ = self._driver.execute_query(query, genotype_tags = genotype_tag, submission_tags = submission_tags, limit = limit)
        return [ri.value() for ri in r] 
    
    def filter_by_user(self, user_tag : List[str], submission_tags : List[str] = None, limit : int = None) -> List[str]:
        ""
        query = (
            "MATCH (submission:Submission) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "MATCH (u:User) "
            "WHERE u.tag in $user_tags AND ((u)-[:OWNS]-(submission) OR (u)-[:IS_PART]->(submission)) "
            "RETURN DISTINCT submission.tag "
        )
        query = self._add_limit(query,limit)
        r,_,_ = self._driver.execute_query(query, user_tags=user_tag, submission_tags = submission_tags, limit = limit)
        return [ri.value() for ri in r] 
    
    def filter_by_quantified_protein(self, protein_tag : List[str], submission_tags : List[str] = None, limit : int = None) -> List[str]:
        ""
        query = (
            "MATCH (p:Protein ) "
            "WHERE p.tag in $protein_tags "
            "MATCH (p)-[:QUANTIFIED_IN]->(submission:Submission) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "RETURN DISTINCT submission.tag "
        )
        query = self._add_limit(query,limit)
        r,_,_ = self._driver.execute_query(query, protein_tags = protein_tag, submission_tags = submission_tags, limit = limit)
        return [ri.value() for ri in r] 
        
        
    def filter_by_state(self, state : List[int], submission_tags : List[str] = None, limit : int = None):
        ""
        query = (
            "MATCH (state:State ) "
            "WHERE state.tag in $state "
            "MATCH (state)<-[:IN_STATE]-(submission:Submission) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "RETURN DISTINCT submission.tag "
        )
        query = self._add_limit(query,limit)
        r = self._driver.execute_query(query, state = state, submission_tags = submission_tags, limit = limit, result_transformer_=Result.value)
        print(state)
        print("FILTER BY STATE", r)
        return [ri for ri in r] 
    
    def get(self, 
            state : List[int] = None, 
            attribute_value_tag : List[str] = None, 
            attribute_tag : List[str]= None, 
            user_tag : List[str] = None, 
            protein_tag : List[str] = None, 
            genotype_tag : List[str] = None,
            limit : int = 10) -> List[str]:
        ""
        
        tags = None 
        
        if state is not None:
            limit_ = limit if all(attr is None for attr in [attribute_value_tag,attribute_tag,user_tag,protein_tag,genotype_tag]) else None #add limit only if all others are
            tags = self.filter_by_state(state=state, submission_tags=tags, limit=limit_)
        
        if genotype_tag is not None:
            limit_ = limit if all(attr is None for attr in [attribute_value_tag,attribute_tag,user_tag,protein_tag]) else None
            tags = self.filter_by_genotype_tags(genotype_tag,submission_tags = tags, limit = limit_)
        
        if attribute_value_tag is not None:
            limit_ = limit if all(attr is None for attr in [attribute_tag,user_tag,protein_tag]) else None
            tags = self.filter_by_attribute_value_tags(attribute_value_tag,submission_tags=tags,limit=limit_)

        if attribute_tag is not None:
            limit_ = limit if all(attr is None for attr in [user_tag,protein_tag]) else None
            tags = self.filter_by_attribute_tags(attribute_tag,submission_tags=tags,limit=limit_)
        
        if user_tag is not None:
            limit_ = limit if protein_tag is None else None
            tags = self.filter_by_user(user_tag,submission_tags=tags,limit=limit_)
        
        if protein_tag is not None:
            tags = self.filter_by_quantified_protein(protein_tag,submission_tags=tags,limit=limit)
            
        if tags is None: #none defined, then just return all. 
            
            return self.get_all_tags(limit=limit)
        
        return tags 
        
        
    def title_full_text_search(self, query_string : str):
        ""
        
        
        r, _ , _ = self._factory.full_text_search("titleSearch",query_string)
        
        print(r)
        
        
    def meta_text_search(self, query_string : str):
        ""
        r, _ , _ = self._factory.full_text_search("metatextSearch",query_string)
        
        print(r)
        
    def full_dataset_text_search(self, search_string : str) -> List[FulltextSearchResult]:
        ""  
        
        r, _ , _ = self._factory.full_text_search("datasetSearch",search_string)
        return [ri.data() for ri in r]
        
        
        


class Neo4JSubmissionSummary(SubmissionSummaryABC):
    def __init__(self, driver : Driver, meta : MetaABC, attributes : AttributesABC) -> None:
        
        self._driver = driver
        self._meta = meta 
        self._attributes = attributes
        self._factory = Neo4JFactory(driver=driver)
         
         
         
    def get(self, tag: str, sep_string  = "\t") -> List[str]:        
        
        if not self._meta.exists(tag=tag): raise ValueError("The submission tag does not exist.")
        meta = self._meta.get(tags = [tag])
        if len(meta) == 0: raise ValueError("The submission tag does not have meta data.")
        submission_info = meta[0]
        users = self._meta.get_users(tag = tag)
        dataset_attributes = self._meta.get_dataset_attributes(tag = tag)
        _, sample_map = self._meta.get_sample_attributes_and_genotypes(tag=tag, as_sample_map=True)
       
        attributes = self._attributes.get_attributes_and_values_for_submission(submission_tag= tag) #TODO change methid to just return text ?
        attributes.attribute_values
        
        attributes_by_tag = dict([(a.tag, a) for a in attributes.attributes])
        attribute_values_by_tag = dict([(a.tag, a) for a in attributes.attribute_values])
        
        base_strings = [
            submission_info.title, 
            f"Researchers{sep_string}{', '.join([f'{u.firstname} {u.lastname}<{u.email}>' for u in users])}",
            f"Summary created at{sep_string}{datetime.datetime.now()}",
            f"WARNING: Be aware that meta data might be added during the project's life cycle.",
            f"Submission tag{sep_string}{submission_info.tag}",
            f"Samples{sep_string}{submission_info.n_samples}",
        ]
        
        for attribute_tag, attribute_value_tags in dataset_attributes.items():
            if attribute_tag in attributes_by_tag:
                attribute = attributes_by_tag[attribute_tag]
                
                for attribute_value_tag in attribute_value_tags:
                    if attribute_value_tag in attribute_values_by_tag:
                        attribute_value = attribute_values_by_tag[attribute_value_tag]
                        if attribute.has_features_value:
                            base_strings.append(f"{attribute.text}{sep_string}{attribute_value.gene_name}({attribute_value.tag})")
                        else:
                            base_strings.append(f"{attribute.text}{sep_string}{attribute_value.text}")
        base_strings.append(sample_map.to_csv(sep=sep_string))
        return base_strings
        