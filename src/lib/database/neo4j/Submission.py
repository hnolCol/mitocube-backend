from typing import Literal, List , Dict, Optional
from unittest import result
from neo4j import Driver, Result 
import uuid
import pandas as pd 
import datetime
from config.models.searches import FulltextSearchResult
from config.models.submissions.comments import SubmissionCommentModel
from config.models.submissions.runs import RunListModel, AnalyticRunModel
from lib.data.runs.runs import RunListCreator
from lib.database.abstract.Submission import SubmissionFilterABC, SubmissionsABC, SubmissionSummaryABC
from lib.database.abstract.Meta import MetaABC
from lib.database.abstract.Attributes import AttributesABC
from lib.database.abstract.Proteomes import ProteomesABC
from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from lib.database.Neo4JDatabase import Neo4JFactory
from config.enums.states import SubmissionStatesEnums
from config.models.submissions.submissions import AttributeTree,  NewSubmissionModel
from config.models.submissions.quantifications import ProteinGroupQuantificationModel, PrecursorQuantificationModel
from config.exceptions.Proteome import ProteomeNotFoundError
from config.models.conditions_applications import ConditionApplicationAttributeModel, ConditionApplicationTreeModel
from config.models.submissions.metatexts import MetaTextInsertModel
from services.encryption import create_hierarchical_hash
from services.random_generators import get_random_string
import os 
from lib.data.ranking.FeatureRanking import FeatureRanking
import numpy as np
from collections import defaultdict
from itertools import islice
import math

def chunk_dict(d, size):
    it = iter(d.items())
    while True:
        chunk = dict(islice(it, size))
        if not chunk:
            break
        yield chunk
class Neo4JSubmissions(SubmissionsABC):

    def __init__(self, driver : Driver, meta : MetaABC, proteomes : ProteomesABC, condition_applications : ConditionApplicationABC) -> None:
        self._meta = meta
        self._driver = driver
        self._proteomes = proteomes
        self._condition_applications = condition_applications

     


    def _m_insert_timeline(self, tag :str, timeline : List[Dict]):
        """_summary_

        Parameters
        ----------
        tag : str
            _description_
        timeline : List[Dict]
            {
                "state" : state_tag,
                "timestamp" : timestamp,
                'user_tag' : user_tag
            }
        """
        if self.exists(tag) is False:
            raise ValueError("Submission with this tag does not exist. Please create the submission first.")


        # query = (   
        #     "MATCH (submission:Submission {tag : $tag}) "   
        #     "UNWIND $timeline as entry "
        #     "MATCH (s:State {tag : entry.state}) "
        #     "MERGE (submission)-[r:IN_STATE]->(s) "
        #     "SET r.created_at = entry.timestamp "
        # )

        # self._driver.execute_query(query, routing_="w", tag = tag, timeline = timeline)

        # return True


    
    def count(self, state : SubmissionStatesEnums = None) -> int:
        """Counts the total number of submissions in the database

        Parameters
        ----------
        state : SubmissionStatesEnums, optional
            Submission state. If provided, the number of submissions in the 
            given state is returned, by default None

        Returns
        -------
        int
            The number of submission. 
        """
        query = (
            "MATCH (submission:Submission) "
        )
        
        if state is not None:
            query += " WHERE EXISTS {(submission)-[:IN_STATE]->(state:State {tag : $state})} "
        
        query += "RETURN count(submission)"
         
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, state = state)
        
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
            "RETURN sample.tag ORDER BY sample.sample_index "
            
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag=tag)
        return r
    
    def get_states(self) -> List[int]:
        "Returns the available submission states in the database." #this should be moved to SubmissionStateDB class 
        
        query = (
            "MATCH (state:State) "
            "RETURN state.tag "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return r 
    
    
    def get_research_aim(self, tag: str) -> str:
        """
        This function is designed to retrieve the research aim based on a specified tag.
        
        :param tag: A tag is a keyword or label that helps categorize or identify a specific topic or
        area of interest. In the context of your function `get_research_aim`, the tag parameter likely
        refers to a specific tag or keyword related to a research aim or objective. This parameter is
        used to retrieve the
        :type tag: str
        """
        "Returns the research aim of the submission."
        query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_AIM]->(aim:ResearchAim) "
            "RETURN aim.text "
        )
        r =  self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else None
    
    def get_state(self, tag: str) -> SubmissionStatesEnums:
        "This returns the current state of the submission. To see all states of the submission use history"
        
        query = (
            "MATCH (submission:Submission)-[r:IN_STATE]->(s:State) "
            "WHERE submission.tag = $tag "
            "RETURN s.tag ORDER BY r.created_at DESC LIMIT 1 "
        )
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        if len(r) == 0: raise ValueError("No state found or submission does not exist.")
        return r[0]
    
    def get_title(self, tag : str) -> str:
        ""
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "RETURN submission.title "
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag)
        if len(r) == 0: raise ValueError("No submission found for this tag or no title given..")
        return r[0]
    
    def set_title(self, tag : str, title : str)-> bool:
        "Sets the title of the submission."
    
        query = ("MATCH (submission:Submission {tag : $tag}) "
                 "SET submission.title = $title, submission.updated_at = timestamp() "
                 "RETURN true")
        r = self._driver.execute_query(query, routing_="w", result_transformer_=Result.value, tag = tag, title = title)
        return r[0] if len(r) > 0 else False


    def get_created_at(self, tag : str ) -> float:
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "RETURN submission.created_at "
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag)
        if len(r) == 0: raise ValueError("No submission found for this tag or no created_at given..")
        return r[0]
    
    def get_creator(self, tag : str) -> str| None:
        """
        Returns the user tag of the creator of the submission.
        Parameters
        ----------
        tag : str 
            The tag of the submission.  
            
        Returns     
        ------- 
        str   the user tag of the creator of the submission.
        """
        
        query = "MATCH (submission:Submission {tag : $tag})-[:CREATED]-(user:User) RETURN user.tag" 
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else None


    def get_conditions_applications(self, tag : str, attribute_tags : List[str] = None, group_by_attribute : bool = False) -> List[str]|List[ConditionApplicationAttributeModel]: #TODO: make Dict a pydanitc model
        """Returns the condition application tag for the submission by its tag. """
        
        query =  "MATCH (submission:Submission {tag : $tag})-[:HAS_APPLICATION]->(condition:ConditionApplication)" 
        if attribute_tags and len(attribute_tags) > 0:
            query += "WHERE EXISTS {(condition)-[:OF_ATTRIBUTE]->(aa:Attribute) WHERE aa.tag IN $attribute_tags} "
        if group_by_attribute:
            query += "MATCH (condition)-[:OF_ATTRIBUTE]->(a:Attribute) RETURN a.tag, collect(condition.tag) "
        else:
            query += "RETURN collect(condition.tag) "
        r = self._driver.execute_query(query, routing_="r", tag = tag, attribute_tags = attribute_tags, result_transformer_=Result.values if group_by_attribute else Result.value)
        if group_by_attribute:
            return [{"attribute_tag" : ri[0], "condition_application_tags" : ri[1]} for ri in r]
        return r[0] if len(r) > 0 else []




    def condition_application_data(self, tag : str) -> List[ConditionApplicationTreeModel]:
        """Gets the condition application data associated with the genotype.

        Parameters
        ----------
        tag : str
            The submission tag.

        Returns
        -------
        List[ConditionApplicationTreeModel]
            A list of condition application tree models associated with the submission.
        """

        query = (
            "MATCH (s:Submission)-[:HAS_APPLICATION]->(ca:ConditionApplication) "
            "WHERE s.tag = $tag "
            "RETURN ca"
        )

        ca_tags = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return [self._condition_applications.get_tree(tag=ca_tag) for ca_tag in ca_tags]

    def get_users(self, tag : str) -> List[str]: 
        """Returns the users that are associated with the submission.
        Parameters 
        ----------
        tag : str
            The tag of the submission.  
        Returns     
        -------     
        List[str]   A list of user tags that are associated with the submission.
        """
        
        query = (
            "MATCH (submission:Submission {tag : $tag})<-[:COLLABORATES|CREATED]-(user:User) " #COLLABORATES|
            "RETURN collect(user.tag) " ) 
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value) 
        return r[0] if len(r) > 0 else []
    
    def get_unique_tag(self) -> str:
        """Generates a unique tag for a submission.""" 
        tag = get_random_string(N=10)
        while self.exists(tag):
            tag = get_random_string(N=10)
        return tag


    def get_durations_between_states(self, state_01 : SubmissionStatesEnums, state_02 : SubmissionStatesEnums) -> List[Dict]:
        """Returns the duration between states for all submissions that have been in both states."""
        query = (
            "MATCH (s2:State {tag : $state_02})<-[r2:IN_STATE]-(submission:Submission)-[r1:IN_STATE]->(s1:State {tag : $state_01}) "
            "WITH submission, (r2.created_at - r1.created_at) AS duration, r2, r1 "
            "ORDER BY submission.tag, duration DESC "
            "WITH submission, collect(duration) AS durations "
            "RETURN {submission_tag: submission.tag, duration: durations[0]} "
        )
        r = self._driver.execute_query(query, routing_="r", state_01 = state_01, state_02 = state_02, result_transformer_=Result.value)
        return r

    def has_genotypes(self, tag : str) -> bool:
        """Checks if the submission has genotypes associated with it."""
        query = (
            "WITH EXISTS {(sub:Submission {tag : $tag})-[:HAS_SAMPLE]->(s:Sample)-[:HAS_GENOTYPE]->(g:Genotype)} as genotype_exists "
            "RETURN genotype_exists "
        )
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]


    def insert(self, tag : str, title : str, user_tag : str, collaborators : List[str] = None) -> bool:
        ""
        if self.exists(tag):
            raise ValueError("Submission with this tag already exists. Use the update function to update the submission.")
        query = (
            "MERGE (submission:Submission {tag : $tag}) "
            "SET submission.title = $title, submission.created_at = timestamp(), submission.user_tag = $user_tag "
            "WITH submission "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (u)-[:CREATED]->(submission) "
            "WITH submission "
            "UNWIND $collaborators as collaborator_tag "
            "MATCH (c:User {tag : collaborator_tag}) "
            "MERGE (submission)<-[:COLLABORATES]-(c) "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag, title = title, user_tag = user_tag, collaborators = collaborators)
        
    def insert_view(self, tag : str, user_tag : str) -> bool:
        "Inserts a view for a submission."
        
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "MERGE (vc:ViewCounter {submission_tag: $tag}) "
            "SET vc.count = coalesce(vc.count, 0) + 1 "
            "WITH submission, vc "
            "MERGE (submission)-[:HAS_VIEW_COUNTER]->(vc) "
            "WITH submission "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (u)-[r:VIEWED]->(submission) "
            "ON CREATE SET r.created_at = timestamp() "
            "WITH submission, r "
            "MATCH (u)-[v:VIEWED]->(s:Submission {tag : $tag}) "
            "WITH v ORDER BY v.created_at DESC SKIP 20 " #make this a property to be defined. 
            "DELETE v "
            "RETURN true "
        )

        self._driver.execute_query(query, routing_="w", tag = tag, user_tag = user_tag)
        return True
    
     
    def insert_research_aim(self, tag : str, research_aim : str, user_tag : str) -> bool:
        """Inserts a research aim for a given submission.

        Parameters
        ----------
        tag : str
            The submission tag
        research_aim : str
            The research aim to insert
        user_tag : str
            The user tag of the user inserting the research aim

        Returns
        -------
        bool
            True if the research aim was inserted successfully, False otherwise
        """
        
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "OPTIONAL MATCH (submission)-[:HAS_AIM]->(aim:ResearchAim) "
            "DETACH DELETE aim "
            "WITH submission "
            "CREATE (aim:ResearchAim {tag : randomUUID(), text : $research_aim}) "
            "MERGE (submission)-[:HAS_AIM]->(aim) "
            "WITH submission, aim "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (u)-[r:CREATED]->(aim) "
            "SET r.created_at = timestamp() "
            "RETURN true "
        )

        self._driver.execute_query(query, routing_="w", tag=tag, research_aim=research_aim, user_tag=user_tag)
        return True
    
    # def insert_protein_quantifications(self, tag : str, quantifications : List[ProteinGroupQuantificationModel]) -> int:   
    #     """
    #     Inserts protein quantifications for a given submission.

    #     Parameters
    #     ----------
    #     tag : str
    #         The tag of the submission.
    #     quantifications : List[Dict]
    #         List of protein quantifications to insert.

    #     Returns
    #     -------
    #     int
    #         Number of inserted protein quantifications.
    #     """
    #     query = (
    #         "MATCH (submission:Submission {tag : $tag}) "
    #         "UNWIND $quantifications as quantification "
    #         "MATCH (pg:ProteinGroup {tag : quantification.tag}) "
    #         "MATCH (sample:Sample {tag : quantification.sample_tag})<-[:HAS_SAMPLE]-(submission) "
    #         "MERGE (sample)-[q:QUANTIFIED]->(pg) "
    #         "SET q.value = quantification.value, q.score = quantification.score, q.submission_tag = $tag, q.created_at = timestamp() "
    #         "RETURN count(q) "
    #     )
    #     r = self._driver.execute_query(query, routing_="w", tag=tag, quantifications=quantifications, result_transformer_=Result.value)
    #     print(r[0] if len(r) > 0 else 0)
    #     return r[0] if len(r) > 0 else 0
    
    def insert_protein_quantifications(
        self,
        tag: str,
        quantifications: List[ProteinGroupQuantificationModel],
        batch_size: int = 1000
        ) -> int:

        quantifications_data = [x.model_dump() for x in quantifications]

        # ---- 2. group by sample_tag ----
        grouped = defaultdict(list)

        for q in quantifications_data:
            grouped[q["sample_tag"]].append(q)

        # ---- 3. batch grouped data ----
        total = 0

        query = """
        CALL () {
            WITH $batch AS batch, $tag AS tag
            UNWIND keys(batch) AS sample_tag

            MATCH (submission:Submission {tag: tag})
            MATCH (sample:Sample {tag: sample_tag})<-[:HAS_SAMPLE]-(submission)

            WITH sample, batch[sample_tag] AS quantifications, tag

            UNWIND quantifications AS q

            MATCH (pg:ProteinGroup {tag: q.tag})

            CREATE (sample)-[r:QUANTIFIED]->(pg)
            SET r.value = q.value,
                r.score = q.score,
                r.submission_tag = tag,
                r.created_at = timestamp()

            RETURN count(r) AS created
        } IN TRANSACTIONS OF 200 ROWS
        RETURN sum(created) AS total
        """

        for batch in chunk_dict(grouped, batch_size):
            result = self._driver.session().run(
                query,
                tag=tag,
                batch=batch
            )

            record = result.single()
            total += record["total"] if record else 0

        return total

        # result = self._driver.execute_query(
        #     query,
        #     routing_="w",
        #     tag=tag,
        #     quantifications=quantifications_data,
        #     result_transformer_=Result.value
        # )

        # return result[0] if result else 0


    def transform_quantification_to_zscore_along_samples(self,tag : str) -> bool:
        """
        Transforms the quantification values for a given sample in a submission to z-scores.
        """
        
        
        query = (
            "MATCH (submission:Submission {tag: $tag})-[:HAS_SAMPLE]->(sample:Sample)-[q:QUANTIFIED]->(pg:ProteinGroup) "
            "WITH sample, collect(q.value) AS values "
            "WITH sample, apoc.coll.avg(values) AS mean, apoc.coll.stdev(values) AS stdev "
            "MATCH (sample)-[q:QUANTIFIED]->(pg:ProteinGroup) "
            "SET q.z_score_sample = (q.value - mean) / stdev "
            "RETURN count(q) "
        )

        r = self._driver.execute_query(
            query,
            routing_="w",
            tag=tag,
            result_transformer_=Result.value
        )
        return r[0] if len(r) > 0 else 0


    def transform_quantification_to_zscore_along_protein_groups(self,tag : str) -> bool:
        """
        Transforms the quantification values for a given submission to z-scores.
        """
        
        query = (
            "MATCH (submission:Submission {tag: $tag})-[:HAS_SAMPLE]->(sample:Sample)-[q:QUANTIFIED]->(pg:ProteinGroup) "
            "WITH pg, collect(q.value) AS values "
            "WITH pg, apoc.coll.avg(values) AS mean, apoc.coll.stdev(values) AS stdev WHERE stdev > 0 " #to avoid division by zero, if stdev is zero, z-score will be set to zero as well.
            "MATCH (sample)-[q:QUANTIFIED]->(pg) "
            "SET q.z_score_protein_group = (q.value - mean) / stdev "
            "RETURN count(q) "
        )   
        r = self._driver.execute_query(
            query,
            routing_="w",
            tag=tag,
            result_transformer_=Result.value
        )
        return r[0] if len(r) > 0 else 0



    def insert_precursor_quantifications(self, tag : str, quantifications : List[PrecursorQuantificationModel]) -> int:   
        ""
        print("not implemented yet")
    
    def get_views(self, tag : str) -> int:
        
        query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_VIEW_COUNTER]->(vc:ViewCounter) "
            "RETURN vc.count "
        )

        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else 0


    
    def insert_attributes(self, tag, traits : List[AttributeTree]) -> bool:
        """Inserts the dataset attributes for a submission. """
        
        if not self.exists(tag):  
            raise ValueError("Submission with this tag does not exist. Please create the submission first.")
        for attribute_tree in traits:
            for c in attribute_tree.children:
                #separate on first level children
                updated_tree = AttributeTree(tag = attribute_tree.tag, type = attribute_tree.type, value = attribute_tree.value, children = [c])
                
                self.insert_condition_application(tag = tag, attribute_tree = updated_tree) 
    
    def insert_condition_application(self, tag : str, attribute_tree : AttributeTree):
        """ Inserts a condition procedure into the database connect to a submission This indicates that all samples
        of the submission are affected by this condition. There are also ConditionApplication nodes that are connected to the samples via the 
        HAS_APPLICATION relationship and are manage by the Samples DB class. These are then specific for a given sample"""

        if not self.exists(tag):  
            raise ValueError("Submission with this tag does not exist. Please create the submission first.")
        submission_tag = tag        
        tag = self._condition_applications.insert(condition_application=attribute_tree) 
        if tag is None:
            raise ValueError("Condition application could not be inserted.") 
        
        query = (
            "MATCH (submission:Submission {tag : $submission_tag}) "
            "MATCH (ca:ConditionApplication {tag : $tag}) "
            "MERGE (submission)-[r:HAS_APPLICATION]->(ca) "
            "SET r.created_at = timestamp() "
        )
        self._driver.execute_query(query, submission_tag = submission_tag, tag = tag)

    def edit_condition_applications(self, tag: str, attribute_trees: List[AttributeTree]) -> bool:
        query = (
            "MATCH (submission:Submission {tag: $tag})-[r:HAS_APPLICATION]->(ca:ConditionApplication) "
            "DELETE r"
        )
        self._driver.execute_query(query, routing_="w", tag=tag)
        for attribute_tree in attribute_trees:
            for c in attribute_tree.children:
                #separate on first level children
                updated_tree = AttributeTree(tag = attribute_tree.tag, type = attribute_tree.type, value = attribute_tree.value, children = [c])
                self.insert_condition_application(tag = tag, attribute_tree = updated_tree) 
                
        return True

    def insert_comment(self, tag : str, comment : SubmissionCommentModel):
        ""         
        query = (
            "MATCH (submission:Submission {tag: $tag}) "
            "MATCH (user:User {tag: $user_tag}) "
            "CREATE (comment:Comment {tag: $comment_tag, content: $content, created_at: timestamp()}) "
            "MERGE (submission)-[:HAS]->(comment) "
            "MERGE (user)-[:CREATED]->(comment) "
        )
        self._driver.execute_query(
            query, routing_="w",
            tag=tag, user_tag=comment.user_tag, comment_tag=comment.tag, content=comment.content
        )
        
        if comment.response_to:
            reply_query = (
                "MATCH (child:Comment {tag: $child_tag}) "
                "MATCH (parent:Comment {tag: $parent_tag}) "
                "MERGE (child)-[:RESPONSE_TO]->(parent) "
            )
            self._driver.execute_query(reply_query, routing_="w", child_tag=comment.tag, parent_tag=comment.response_to)

    def get_comments(self, tag: str) -> List[SubmissionCommentModel]:
        "Returns the available comments for a given submission tag."
        query = (
            "MATCH (submission:Submission {tag: $tag})-[:HAS]->(comment:Comment)<-[:CREATED]-(u:User) "
            "OPTIONAL MATCH (comment)-[:RESPONSE_TO]->(parent:Comment) "
            "RETURN {user_tag: u.tag, created_at: comment.created_at, content: comment.content, tag: comment.tag, response_to: parent.tag} "
            "ORDER BY comment.created_at ASC"
        )
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return [SubmissionCommentModel(**c) for c in r ]
        
    def get(self, tag: str):
        return super().get(tag)

    
    def update_state(self, tag: str, new_state: SubmissionStatesEnums, user_tag : str) -> bool:
        "Updates the state of a submission."
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "MATCH (newState:State {tag : $new_state}) "
            "CREATE (submission)-[r:IN_STATE]->(newState) "
            "SET r.created_at = timestamp(), r.user_tag = $user_tag "

        )
        
        try: 
            self._driver.execute_query(query, tag = tag, new_state = new_state, user_tag = user_tag)
        except Exception as e:
            print(e)
            return False 
        return True 
    
    def insert_state_history(self,tag : str, state_history : List[Dict]):
        """Inserts the state history for a submission. This is used to keep track of the state changes of a submission. This can be used for auditing purposes. This should be called when a state change occurs. The state history is a list of dictionaries with the following keys:
        - state: the state of the submission
        - created_at: the timestamp of the state change
        - user_tag: the user tag of the user who made the state change

        Parameters
        ----------
        tag : str
            The submission tag.
        state_history : List[Dict]
            The state history to insert.
        """
        
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "UNWIND $state_history as state_change "
            "MATCH (s:State {tag : state_change.state}) "
            "MERGE (submission)-[r:IN_STATE]->(s) "
            "SET r.created_at = state_change.created_at, r.user_tag = state_change.user_tag "
        )
        try: 
            self._driver.execute_query(query, tag = tag, state_history = state_history)
        except Exception as e:
            print(e)
            return False 
        return True 
    
    def set_state(self, tag: str, state: SubmissionStatesEnums, user_tag : str) -> bool:
        """Sets the state of a submission. If the state already exists, it is updated. 
        If the state does not exist, it is skipped and nothing happens.

        Parameters
        ----------
        tag : str
            The submission tag.
        state : SubmissionStatesEnums
            The new state of the submission.
        user_tag : str
            The user tag of the user who sets the state.

        Returns
        -------
        bool
            True if the state was set successfully, False otherwise.
        """
        return self.update_state(tag=tag, new_state=state, user_tag=user_tag)
    
    
    # def get_correlated_features(self, tags : List[str], 
    #                             feature_tag : str, 
    #                             filter_tag : str = None,  
    #                             direction : Literal["positive","negative","both"] = "both", 
    #                             limit : int = 20, 
    #                             min_data_points : int = 20):
    #     """Correlates a feature to all other features 
    #     by its feature_tag in the submissions given by 'tags' . 

    #     Parameters
    #     ----------
    #     tags : List[stt] - List of submissions 
    #     feature_tag : str
    #         the feature tag. 

    #     Returns
    #     -------
    #     pd.DataFrame
    #         Correlation analysis with the following columns
    #             - tag (str) - feature_tag that the given tag was correlated to 
    #             - pearson (float) - the pearson correlation coefficient 
    #             - N (int) - The number of data points used to calculate the statistics 
    #             - t (float) - The t-value
    #     """
    #     ## extend to multiple submission tags ? MATCH (submission:Submission )-[:HAS_SAMPLE]-(s:Sample) WHERE submission.tag in $submission_tags 
    #     query = (
    #         "MATCH (submission:Submission )-[:HAS_SAMPLE]-(s:Sample) WHERE submission.tag in $submission_tags "
    #         "MATCH (p_target:Protein {tag : $feature_tag})<-[rp1:QUANTIFIED]-(s:Sample)-[rp2:QUANTIFIED]->(p:Protein) "
    #     )
    #     if filter_tag is not None:
    #         query += "WHERE EXISTS {(p)-[:PART_OF]->(f:Filter {tag : $filter_tag})} "
    #     query += (
    #         "WITH collect(rp2.value) as x, collect(rp1.value) as y, p "
    #         "WITH apoc.coll.zip(x, y) AS pairs, apoc.coll.avg(x) AS meanX, apoc.coll.avg(y) AS meanY, x ,y, p "
    #         "WHERE size(x) > $min_data_points AND size(y) > $min_data_points "
    #         "WITH "
    #         "   [p IN pairs | (p[0] - meanX) * (p[1] - meanY)] AS products, "
    #         "   [v IN x | (v - meanX)^2] AS xSquaredDiffs, "
    #         "   [v IN y | (v - meanY)^2] AS ySquaredDiffs, p, size(pairs) as N "
    #         "WITH "
    #         "    apoc.coll.sum(products) / "
    #         "   (SQRT(apoc.coll.sum(xSquaredDiffs)) * SQRT(apoc.coll.sum(ySquaredDiffs))) AS pearson, p, N "
    #         "RETURN p.tag as tag, round(pearson,2) as pearson, N as N,  pearson * SQRT(N-2) / SQRT(1-pearson^2) as t " 
    #     )
    #     if direction == "both": 
    #         query += "ORDER BY abs(pearson) DESC LIMIT $limit "
    #     elif direction == "negative":
    #         query += "ORDER BY pearson ASC LIMIT $limit "
    #     elif direction == "positive":
    #         query += "ORDER BY pearson DESC LIMIT $limit "    
                
    #     r = self._driver.execute_query(query, 
    #                                    routing_="r", 
    #                                    result_transformer_=Result.to_df, 
    #                                    min_data_points = min_data_points, 
    #                                    filter_tag = filter_tag, 
    #                                    limit = limit, 
    #                                    feature_tag = feature_tag, 
    #                                    submission_tags = tags)
    #     return r 
    
    def quantification_exists(self, tag : str, type : Literal["proteins","protein_groups","precursors","any"]) -> bool:
        """Checks if samples have quantification data for a given submission."""
        if type in ["proteins","protein_groups"]:
            query = (
                "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(s:Sample)-[q:QUANTIFIED]->(p:Protein|ProteinGroup) "
                "RETURN count(q) > 0 "
            )
        elif type == "precursors":
            query = (
                "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(s:Sample)-[q:QUANTIFIED]->(p:Precursor) "
                "RETURN count(q) > 0 "
            )
        elif type == "any":
            query = (
                "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(s:Sample)-[q:QUANTIFIED]->(p:ProteinGroup|Precursor|Protein) "
                "RETURN count(q) > 0 "
            )
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False
    
    def get_proteins_in_submission(self, tag: str) -> List[str]:
        """Returns a list of all protein tags that are quantified in the submission."""
        query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(s:Sample)-[q:QUANTIFIED]->(p:Protein) "
            "RETURN DISTINCT p.tag "
        )
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        return r
    
    
    
    def get_protein_group_quantification_count(self) -> pd.DataFrame:
        """Returns the number of protein group quantifications for each submission. 
        Neo4J implementation.  

        Returns
        -------
        pd.DataFrame
             A data frame with the following columns:
            ```
                - 'submission_tag' (str) : The submission tag
                - 'protein_group_quantification_count' (int) : The number of protein group quantifications for the submission
                - 'user_tag' (str) : The user tag of the creator of the submission
                - 'created_at' (float) : The creation date of the submission
            ```
            A dictionary with submission tags as keys and the number of protein group quantifications as values.
        """
        query = (
            "MATCH (u:User)-[:CREATED]->(submission:Submission)-[:HAS_SAMPLE]->(s:Sample)-[q:QUANTIFIED]->(p:ProteinGroup) "
            "RETURN submission.tag as submission_tag, count(DISTINCT p) as count, u.tag as user_tag, submission.created_at as created_at "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df)

        return r
    
    def calculate_multiple_comparison_metrices(self, tag : str, batch_size : int = 300) -> bool:
        
        
        query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(s:Sample)-[q:QUANTIFIED]->(p:ProteinGroup) "
            "MATCH (s)-[:HAS_APPLICATION]->(ca:ConditionApplication)-[:OF_ATTRIBUTE]->(a:Attribute) "
            "WITH p, q, a, collect(ca.tag) as ca_tags, s "
            "RETURN p.tag as protein_group_tag, q.value as value, a.tag as attribute_tag, apoc.text.join(apoc.coll.sort(ca_tags), ',') as ca_tags, s.tag as sample_tag "
            
        )
        r_ca = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df, tag = tag)
        
        if self.has_genotypes(tag = tag):
              
            query = (
                "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(s:Sample)-[q:QUANTIFIED]->(p:ProteinGroup) "
                "MATCH (s)-[:HAS_GENOTYPE]->(g:Genotype) "
                "WITH p, q, collect(g.tag) as ca_tags, s "
                "RETURN p.tag as protein_group_tag, q.value as value, 'att_genotype' as attribute_tag, apoc.text.join(apoc.coll.sort(ca_tags), ',') as ca_tags, s.tag as sample_tag "
            )
        
        
            r_g = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df, tag = tag)
            r_ca = pd.concat([r_ca, r_g], ignore_index=True)
        
        df = FeatureRanking().compute_metrics(df = r_ca)
        rows = df.to_dict("records")
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            query = (
                "UNWIND $batch as row "
                "MATCH (p:ProteinGroup {tag : row.protein_group_tag}) "
                "MATCH (submission:Submission {tag : $tag}) "
                "MATCH (a:Attribute {tag : row.attribute_tag}) "
                "MERGE (stats:Statistics {tag : 'stats_' + row.protein_group_tag + '_' + row.attribute_tag + '_' + $tag}) "
                "SET stats.F = row.F,"
                "stats.created_at = timestamp(),"
                "stats.p_value = row.p_value,"
                "stats.eta_squared = row.eta_squared,"
                "stats.cohen_f = row.cohen_f,"
                "stats.max_fc = row.max_fc,"
                "stats.FDR = row.FDR,"
                "stats.rank = row.rank,"
                "stats.std_means = row.std_means,"
                "stats.missingness = row.missingness,"
                "stats.n_groups = row.n_groups,"
                "stats.exclusively_ca_tags = row.exclusively_ca_tags, "
                "stats.score = row.score, "
                "stats.mean = row.mean, "
                "stats.quantified_in_samples = row.quantified_in_samples, "
                "stats.exclusively = row.exclusively "
                "WITH submission, stats, p, a, row "
                "MERGE (submission)-[:HAS_STATS]->(stats)-[:FOR_PROTEIN_GROUP]->(p) "
                "WITH p, row, a, stats "
                "MERGE (stats)-[:OF_ATTRIBUTE]->(a) "
                
            )
            r = self._driver.execute_query(query, routing_="w", batch = batch, tag = tag)
        
        
        return True
        
        
    def remove_multiple_comparison_metrices(self, tag : str) -> bool:
        """Removes the multiple comparison statistics for a given submission tag. This can be used to remove the statistics before recalculating them. Neo4J implementation. 

        Parameters
        ----------
        tag : str
            The submission tag.

        Returns
        -------
        bool
            True if the statistics were removed successfully, False otherwise.
        """
        
        query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_STATS]->(stats:Statistics) "
            "DETACH DELETE stats "
        )
        
        try: 
            self._driver.execute_query(query, routing_="w", tag = tag)
        except Exception as e:
            print(e)
            return False 
        return True
    
    def get_mutli_comp_stats(self, tag : str, attribute_tag : str = None) -> pd.DataFrame:
        """Returns the multiple comparison statistics for a given submission tag. Neo4J implementation. 

        Parameters
        ----------
        tag : str
            The submission tag.

        Returns
        -------
        pd.DataFrame
            A data frame with the following columns:
            ```
                - 'protein_group_tag' (str) : The protein group tag
                - 'attribute_tag' (str) : The attribute tag
                - 'F' (float) : The F-value of the ANOVA test
                - 'p_value' (float) : The p-value of the ANOVA test
                - 'eta_squared' (float) : The eta squared value of the ANOVA test
                - 'cohen_f' (float) : The Cohen's f value of the ANOVA test
                - 'max_fc' (float) : The maximum fold change between groups
                - 'std_means' (float) : The standard deviation of the group means
                - 'missingness' (float) : The percentage of missing values for the protein group across all samples
                - 'n_groups' (int) : The number of groups compared in the ANOVA test
                - 'score' (float) : A combined score based on the other metrics for ranking purposes
                - 'mean' (float) : The mean quantification value across all samples for the protein group
                - 'quantified_in_samples' (int) : The number of samples in which the protein group is quantified
                - 'exclusively' (bool) : Whether the protein group is exclusively quantified in one group or not 
            ```
        """
        
        query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_STATS]->(stats:Statistics)-[:FOR_PROTEIN_GROUP]->(p:ProteinGroup) "
            "MATCH (stats)-[:OF_ATTRIBUTE]->(a:Attribute) "
        )
        if attribute_tag is not None:
            query += "WHERE a.tag = $attribute_tag "
            
        query += ("RETURN p.tag as protein_group_tag, a.tag as attribute_tag,  stats.F as F, stats.p_value as p_value, stats.eta_squared as eta_squared, stats.cohen_f as cohen_f, stats.rank as rank, stats.FDR as FDR, "
                "stats.quantified_in_samples as quantified_in_samples, stats.max_fc as max_fc, stats.std_means as std_means, stats.missingness as missingness, stats.n_groups as n_groups, stats.score as score, stats.mean as mean, stats.exclusively as exclusively ")

        
        r = self._driver.execute_query(query, routing_="r", tag = tag, attribute_tag = attribute_tag, result_transformer_=Result.to_df)
        return r
    
    

    def insert_runlist(self, submission_tag: str, runlist: RunListModel, user_tag: str) -> bool:
        rl_tag = get_random_string(N=10)
        
        # Build the Cypher query based on whether an instrument relationship should be created or not
        if runlist.instrument_tag is not None:
            # Query WITH instrument relationship
            query = (
                "MATCH (submission:Submission {tag: $submission_tag}) "
                "WITH submission "
                "MATCH (u:User {tag: $user_tag}) "
                "MATCH (inst:Trait {tag: $instrument_tag}) "
                "CREATE (rl:RunList {tag: $rl_tag, created_at: timestamp(), "
                "   dataset_label: $dataset_label, n_runs: $n_runs, n_plates: $n_plates, "
                "   scrambled: $scrambled, scrambled_across_plates: $scrambled_across_plates, "
                "   fractionated: $fractionated, n_fractions: $n_fractions, "
                "   aggregated_on: $aggregated_on, user_tag: $user_tag}) "
                "MERGE (submission)-[:HAS_RUNLIST]->(rl) "
                "MERGE (u)-[:CREATED]->(rl) "
                "MERGE (rl)-[:MEASURED_BY]->(inst) "
                "WITH rl "
                "UNWIND $runs AS run "
                "CREATE (r:Run {tag: randomUUID(), text: run.name, "
                "   index: run.index, measurement_index: run.measurement_index, "
                "   plate_index: run.plate_index, row_index: run.row_index, "
                "   column_index: run.column_index, position_label: run.position_label, "
                "   sample_index: run.index}) "
                "MERGE (rl)-[:HAS_RUN]->(r) "
            )
            params = {
                "submission_tag": submission_tag,
                "user_tag": user_tag,
                "rl_tag": rl_tag,
                "instrument_tag": runlist.instrument_tag,
                "dataset_label": runlist.dataset_label,
                "n_runs": runlist.n_runs,
                "n_plates": runlist.n_plates,
                "scrambled": runlist.scrambled,
                "scrambled_across_plates": runlist.scrambled_across_plates,
                "fractionated": runlist.fractionated,
                "n_fractions": runlist.n_fractions,
                "aggregated_on": runlist.aggregated_on,
                "runs": [r.model_dump() for r in runlist.runs]
            }
        else:
            # Query WITHOUT instrument relationship
            query = (
                "MATCH (submission:Submission {tag: $submission_tag}) "
                "WITH submission "
                "MATCH (u:User {tag: $user_tag}) "
                "CREATE (rl:RunList {tag: $rl_tag, created_at: timestamp(), "
                "   dataset_label: $dataset_label, n_runs: $n_runs, n_plates: $n_plates, "
                "   scrambled: $scrambled, scrambled_across_plates: $scrambled_across_plates, "
                "   fractionated: $fractionated, n_fractions: $n_fractions, "
                "   aggregated_on: $aggregated_on, user_tag: $user_tag}) "
                "MERGE (submission)-[:HAS_RUNLIST]->(rl) "
                "MERGE (u)-[:CREATED]->(rl) "
                "WITH rl "
                "UNWIND $runs AS run "
                "CREATE (r:Run {tag: randomUUID(), text: run.name, "
                "   index: run.index, measurement_index: run.measurement_index, "
                "   plate_index: run.plate_index, row_index: run.row_index, "
                "   column_index: run.column_index, position_label: run.position_label, "
                "   sample_index: run.index}) "
                "MERGE (rl)-[:HAS_RUN]->(r) "
            )
            params = {
                "submission_tag": submission_tag,
                "user_tag": user_tag,
                "rl_tag": rl_tag,
                "dataset_label": runlist.dataset_label,
                "n_runs": runlist.n_runs,
                "n_plates": runlist.n_plates,
                "scrambled": runlist.scrambled,
                "scrambled_across_plates": runlist.scrambled_across_plates,
                "fractionated": runlist.fractionated,
                "n_fractions": runlist.n_fractions,
                "aggregated_on": runlist.aggregated_on,
                "runs": [r.model_dump() for r in runlist.runs]
            }
        
        self._driver.execute_query(query, routing_="w", **params)
        
        # Link each Run to its Sample via sample_index
        query_measures = (
            "MATCH (submission:Submission {tag: $submission_tag})-[:HAS_RUNLIST]->(rl:RunList {tag: $rl_tag}) "
            "MATCH (rl)-[:HAS_RUN]->(r:Run) "
            "MATCH (submission)-[:HAS_SAMPLE]->(s:Sample {sample_index: r.sample_index}) "
            "MERGE (r)-[:MEASURES]->(s) "
        )
        self._driver.execute_query(
            query_measures, routing_="w",
            submission_tag=submission_tag,
            rl_tag=rl_tag
        )

        # For pooled runs, also link aggregated samples
        pooled_runs = [r for r in runlist.runs if len(r.aggregated_samples) > 0]
        if pooled_runs:
            query_pooled = (
                "MATCH (submission:Submission {tag: $submission_tag})-[:HAS_RUNLIST]->(rl:RunList {tag: $rl_tag}) "
                "MATCH (rl)-[:HAS_RUN]->(r:Run {index: $run_index}) "
                "UNWIND $sample_indices AS sample_index "
                "MATCH (submission)-[:HAS_SAMPLE]->(s:Sample {sample_index: sample_index}) "
                "MERGE (r)-[:MEASURES]->(s) "
            )
            for run in pooled_runs:
                self._driver.execute_query(
                    query_pooled, routing_="w",
                    submission_tag=submission_tag,
                    rl_tag=rl_tag,
                    run_index=run.index,
                    sample_indices=run.aggregated_samples
                )

        return True

    def get_runlist(self, submission_tag: str) -> Optional[RunListModel]:
        query = (
            "MATCH (:Submission {tag: $tag})-[:HAS_RUNLIST]->(rl:RunList) "
            "MATCH (rl)-[:HAS_RUN]->(r:Run) "
            "OPTIONAL MATCH (u:User)-[:CREATED]->(rl) "
            "OPTIONAL MATCH (rl)-[:MEASURED_BY]->(inst:Trait) "
            "RETURN rl{.*, user_tag: u.tag, instrument_tag: inst.tag} as rl, collect(r{.*}) as runs "
        )
        r = self._driver.execute_query(query, tag=submission_tag, result_transformer_=Result.data)
        if not r:
            return None
        row = r[0]
        runs = sorted(
            [AnalyticRunModel(**{**dict(run), "name": run.get("text") or run.get("name")}, aggregated_samples=[]) for run in row["runs"]],
            key=lambda x: x.measurement_index
        )
        return RunListModel(**row["rl"], runs=runs)
    
    def delete_runlist(self, submission_tag: str) -> bool:
        query = (
            "MATCH (:Submission {tag: $tag})-[:HAS_RUNLIST]->(rl:RunList) "
            "DETACH DELETE rl "
        )
        try:
            self._driver.execute_query(query, routing_="w", tag=submission_tag)
            return True
        except Exception as e:
            print(e)
            return False

class Neo4JSubmissionFilter(SubmissionFilterABC):
    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver
        self._factory = Neo4JFactory(driver=driver)
        
        
    def _add_limit(self, query : str, limit : int = None):
        ""
        if limit is not None : query += "LIMIT $limit "
        return query 
        
    
    def get_all_tags(self, limit : int = None, ordered : bool = True)->List[str]:
        """Returns all submission tags in the database.
        
        Parameters
        ----------
        limit : int, optional
            The maximum number of tags to return, by default None
        ordered : bool, optional
            If True, the tags are ordered by the creation date of the submission, by default True

        Returns
        -------
        List[str]
            A list of submission tags.
        """ 
        query = (
                "MATCH (submission:Submission) "
                "RETURN submission.tag "
            )
        if ordered:
            query += "ORDER BY submission.created_at DESC "
        
        query = self._add_limit(query,limit)
        r = self._driver.execute_query(query, routing_="r",limit=limit, result_transformer_=Result.value)
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
                     "MATCH (n)-[:CREATED]->(submission:Submission) ")
        elif by == "state":
            query = ("MATCH (n:State) "
                     "MATCH (n)<-[:IN_STATE]-(submission:Submission) ")
        elif by == "attribute":
            query = ("MATCH (n:Attribute) "
                     "MATCH (n)<-[:HAS_VALUES_FOR_ATTRIBUTE]-(submission:Submission) ")
        elif by == "attribute_value":
            query = ("MATCH (n:Trait) "
                     "MATCH (n)<-[:HAS_TRAIT]-(submission:Submission) ")
        if tags is not None:
            query += "WHERE submission.tag in $tags "
            
        query += "RETURN n.tag as tag, count(submission) as count, collect(submission.tag) as tags "
        
        submission_counts = self._driver.execute_query(query, tags = tags, routing_="r",database_="neo4j",result_transformer_=Result.to_df)
        return submission_counts.set_index("tag")
    
    
    def group_by_state(self, tags : List[str] = None) -> Dict[str|int, List[str]]:
        """Groups the submissions by their state and returns the counts of each state.

        Parameters
        ----------
        tags : List[str]
            The submission tags to use. If None, all tags in the database are used.
            If tags is an empty list, an empty dictionary is returned.

        Returns
        -------
        Dict[str, List[str]]
            A dictionary with the state tag as key and a list of submission tags as value.
            The keys are the state tags and the values are lists of submission tags.
            If no submissions are found, an empty dictionary is returned.
            
        Raises
        ------
        TypeError
            If the tags parameter is not a list of strings or None.
        """
        
        if tags is not None and not isinstance(tags, list):
            raise TypeError("The tags parameter must be a list of strings or None.")
        elif len(tags) == 0:
            return {}
        
        query = "MATCH (submission:Submission) "
        
        if tags is not None:
            query += "WHERE submission.tag in $tags "
        
        query += (
            "MATCH (submission)-[r:IN_STATE]->(state:State) WHERE r.created_at IS NOT NULL "
            "WITH submission, "
            "     state, "
            "     r "
            "ORDER BY r.created_at DESC "
            "WITH submission, "
            "    collect({state: state.tag, r: r}) AS rels "
            "WITH submission, head(rels) AS latest "
            "RETURN latest.state AS state_tag, collect(submission.tag) AS submission_tags "
        )

        r = self._driver.execute_query(query, tags = tags, routing_="r", database_="neo4j", result_transformer_=Result.data)
        return dict((ri.get("state_tag"),ri.get("submission_tags")) for ri in r)
    


    def filter_by_trait_tags(self, trait_tags : List[str], submission_tags : List[str] = None, limit : int = None, ordered : bool = True) -> List[str]:
        ""
        query = (
            "MATCH (submission:Submission)-[:HAS_TRAIT]->(t:Trait) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "WITH submission, COLLECT(DISTINCT t.tag) AS trait_tags "
            "WHERE ALL(trait_tag IN $trait_tags WHERE trait_tag in trait_tags) "
            "RETURN DISTINCT submission.tag "
        )
        query = self._add_limit(query,limit)
        if ordered:
            query += "ORDER BY submission.created_at DESC "
        r = self._driver.execute_query(query, trait_tags = trait_tags, submission_tags = submission_tags, limit = limit, result_transformer_=Result.value)

        return r


    def filter_by_attribute_tags(self, attribute_tag : List[str], submission_tags : List[str] = None, limit : int = None, ordered : bool = True) -> List[str]:
        ""
        query = (
            "MATCH (submission:Submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(av:Attribute) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "WITH submission, COLLECT(DISTINCT av.tag) AS value_tags "
            "WHERE ALL(value_tag in $attribute_tags WHERE value_tag in value_tags) "
            "RETURN DISTINCT submission.tag "
        )
        query = self._add_limit(query,limit)
        if ordered:
            query += "ORDER BY submission.created_at DESC "
        r,_,_ = self._driver.execute_query(query, attribute_tags=attribute_tag, submission_tags = submission_tags, limit = limit)
        
        return [ri.value() for ri in r] 
    
    def filter_by_genotype_tags(self, genotype_tag : List[str], submission_tags : List[str] = None, limit : int = None, ordered : bool = True) -> List[str]:
        ""
        query = (
            "MATCH (g:Genotype) "
            "WHERE g.tag in $genotype_tags "
            "MATCH (g)<-[:HAS_GENOTYPE]-(submission:Submission) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "RETURN DISTINCT submission.tag "
        )
        if ordered:
            query += "ORDER BY submission.created_at DESC "
        query = self._add_limit(query,limit)
        
        r,_,_ = self._driver.execute_query(query, genotype_tags = genotype_tag, submission_tags = submission_tags, limit = limit)
        return [ri.value() for ri in r] 

    def filter_by_user(self, user_tags : List[str], submission_tags : List[str] = None, limit : int = None, ordered : bool = True) -> List[str]:
        ""
        query = (
            "MATCH (submission:Submission) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "MATCH (u:User) "
            "WHERE u.tag in $user_tags AND (u)-[:CREATED]->(submission) " #filter_by_user
            "RETURN submission.tag "
        )
        if ordered:
            query += "ORDER BY submission.created_at DESC "
        query = self._add_limit(query,limit)

        r = self._driver.execute_query(query, user_tags=user_tags, submission_tags = submission_tags, limit = limit, result_transformer_=Result.value)
  
        return r
    
    def filter_by_quantified_protein(self, protein_tag : List[str], submission_tags : List[str] = None, limit : int = None, ordered : bool = True) -> List[str]:
        ""
        query = (
            "MATCH (p:Protein ) "
            "WHERE p.tag in $protein_tags "
            "MATCH (p)-[:QUANTIFIED_IN]->(submission:Submission) "
            f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            "RETURN DISTINCT submission.tag "
        )
        if ordered:
            query += "ORDER BY submission.created_at DESC "
        query = self._add_limit(query,limit)
        
        r,_,_ = self._driver.execute_query(query, protein_tags = protein_tag, submission_tags = submission_tags, limit = limit)
        return [ri.value() for ri in r] 
        
        
    def filter_by_state(self, states : List[int], submission_tags : List[str] = None, limit : int = None, ordered : bool = True) -> List[str]:
        ""
        query = (
            # "MATCH (state:State ) "
            # "WHERE state.tag in $state "
            # "MATCH (state)<-[:IN_STATE]-(submission:Submission) "
            # f"{'WHERE submission.tag in $submission_tags' if submission_tags is not None else ''} " 
            # "RETURN DISTINCT submission.tag "

            "MATCH (submission:Submission)-[r:IN_STATE]->(state:State) WHERE r.created_at IS NOT NULL "
            "WITH submission, r, state "
            "ORDER BY r.created_at DESC "
            "WITH submission, collect({rel: r, state: state.tag}) AS rels "
            #// Get the latest relationship and state per submission
            "WITH submission, rels[0] AS latest "
            #"// Filter submissions whose latest IN_STATE relationship points to the state you want
            "WHERE latest.state IN $states "
            "RETURN submission.tag "
            )
        
        if ordered:
            query += "ORDER BY submission.created_at DESC "
        query = self._add_limit(query,limit)
        r = self._driver.execute_query(query, states = states, submission_tags = submission_tags, limit = limit, result_transformer_=Result.value)
        return r
    
    def filter_by_search_string(self, search_string : str, limit : int, ordered : bool = True) -> List[str]:
        ""        
        query = (
            "MATCH (submission:Submission) "
            "WHERE toLower(submission.title) CONTAINS $search_string "
            "RETURN submission.tag "
        )
        if ordered:
            query += "ORDER BY submission.created_at DESC "
        query = self._add_limit(query,limit)
        
        tags = self._driver.execute_query(query, routing_="r", result_transformer_= Result.value, search_string = search_string.lower(), limit = limit)
 
        return tags 
    
    def find(self, 
            search_string : str = None,
            state : List[int] = None, 
            trait_tags : List[str] = None, 
            attribute_tag : List[str]= None, 
            user_tags : List[str] = None, 
            protein_tag : List[str] = None, 
            genotype_tag : List[str] = None,
            ordered : bool = True,
            limit : int = 10) -> List[str]:
        """Returns a list of submission tags that match the given filters."""

        tags = None
        filter_defined = not all(attr is None for attr in [search_string, state, trait_tags, attribute_tag, user_tags, protein_tag, genotype_tag])
        
        if search_string is not None:
            
            limit_ = limit if all(attr is None for attr in [state,trait_tags,attribute_tag,user_tags,protein_tag,genotype_tag]) else None #add limit only if all others are
            tags = self.filter_by_search_string(search_string=search_string, limit=limit, ordered=ordered)
        
        if state is not None:
            limit_ = limit if all(attr is None for attr in [trait_tags,attribute_tag,user_tags,protein_tag,genotype_tag]) else None #add limit only if all others are
            tags = self.filter_by_state(states=state, submission_tags=tags, limit=limit_, ordered=ordered)

        if genotype_tag is not None:
            limit_ = limit if all(attr is None for attr in [trait_tags,attribute_tag,user_tags,protein_tag]) else None
            tags = self.filter_by_genotype_tags(genotype_tag,submission_tags = tags, limit = limit_, ordered=ordered)

        if trait_tags is not None:
            limit_ = limit if all(attr is None for attr in [attribute_tag,user_tags,protein_tag]) else None
            tags = self.filter_by_attribute_value_tags(trait_tags,submission_tags=tags,limit=limit_, ordered=ordered)

        if attribute_tag is not None:
            limit_ = limit if all(attr is None for attr in [user_tags,protein_tag]) else None
            tags = self.filter_by_attribute_tags(attribute_tag,submission_tags=tags,limit=limit_, ordered=ordered)

        if user_tags is not None:
            limit_ = limit if protein_tag is None else None
            tags = self.filter_by_user(user_tags,submission_tags=tags,limit=limit_, ordered=ordered)

        if protein_tag is not None:
            tags = self.filter_by_quantified_protein(protein_tag,submission_tags=tags,limit=limit_, ordered=ordered)
            
        if not filter_defined: #none defined, then just return all. 
            
            return self.get_all_tags(limit=limit, ordered= ordered)
        
        if tags is None: return []
        
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
