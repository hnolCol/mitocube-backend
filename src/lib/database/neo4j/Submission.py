from typing import Literal, List , Dict
from neo4j import Driver, Result 
import uuid
import pandas as pd 
import datetime
from config.models.searches import FulltextSearchResult
from config.models.submissions.comments import SubmissionCommentModel
from lib.database.abstract.Submission import SubmissionFilterABC, SubmissionsABC, SubmissionSummaryABC
from lib.database.abstract.Meta import MetaABC
from lib.database.abstract.Attributes import AttributesABC
from lib.database.abstract.Proteomes import ProteomesABC
from lib.database.Neo4JDatabase import Neo4JFactory
from config.enums.states import SubmissionStatesEnums
from config.models.submissions.submissions import AttributeTree, DatasetSubmissionModel
from config.models.submissions.quantifications import ProteinQuantificationModel, PrecursorQuantificationModel
from config.exceptions.Proteome import ProteomeNotFoundError
from config.models.conditions_applications import ConditionApplicationAttributeModel 

from services.encryption import create_hierarchical_hash
from services.random_generators import get_random_string

class Neo4JSubmissions(SubmissionsABC):
    
    def __init__(self, driver : Driver, meta : MetaABC, proteomes : ProteomesABC) -> None:
        self._meta = meta 
        self._driver = driver
        self._proteomes = proteomes
        
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

    def condition_application_exists(self, tag : str) -> bool:
        "Check if a condition application exists for the given tag."

        query = (
            "WITH EXISTS {(ca:ConditionApplication {tag : $tag})} as exists "
            "RETURN exists"
        )

        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag)
        return r[0]
    
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


    def get_conditions_applications(self, tag : str, group_by_attribute : bool = False) -> List[str]|List[ConditionApplicationAttributeModel]: #TODO: make Dict a pydanitc model
        """Returns the condition application tag for the submission by its tag. """
        
        query =  "MATCH (submission:Submission {tag : $tag})-[:HAS_APPLICATION]->(condition:ConditionApplication)" 
        if group_by_attribute:
            query += "MATCH (condition)-[:OF_ATTRIBUTE]->(a:Attribute) RETURN a.tag, collect(condition.tag) "
        else:
            query += "RETURN collect(condition.tag) "
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.values if group_by_attribute else Result.value)
        if group_by_attribute:
            return [{"attribute_tag" : ri[0], "condition_application_tags" : ri[1]} for ri in r]
        return r[0] if len(r) > 0 else []

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

    def insert(self, tag : str, title : str, user_tag : str, collaborators : List[str] = None, submission: DatasetSubmissionModel = None) -> bool:
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
            "MERGE (submission)-[:COLLABORATES]->(c) "
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
    
    def insert_protein_quantifications(self, tag : str, quantifications : List[ProteinQuantificationModel]) -> int:   
        """
        Inserts protein quantifications for a given submission.

        Parameters
        ----------
        tag : str
            The tag of the submission.
        quantifications : List[Dict]
            List of protein quantifications to insert.

        Returns
        -------
        int
            Number of inserted protein quantifications.
        """
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "UNWIND $quantifications as quantification "
            "MATCH (protein:Protein {tag : quantification.tag}) "
            "MATCH (sample:Sample {tag : quantification.sample_tag})<-[:HAS_SAMPLE]-(submission) "
            "MERGE (sample)-[q:QUANTIFIED]->(protein) "
            "SET q.value = quantification.value, q.score = quantification.score, q.submission_tag = $tag, q.created_at = timestamp() "
            "RETURN count(q) "
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, quantifications=quantifications)
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
        print(r, "viewss")
        return r[0] if len(r) > 0 else 0


        # dataset_attribute_input = submission.dataset_attribute_input
        # genotypes_added = 0 
        # sample_attributes_added = 0 
        
        # dataset_props = {
        #     "title" : submission.title, 
        #     "n_samples" : submission.n_samples, 
        #     "created_at" : submission.created_on,
        #     "state" : submission.state, 
        #     "n_replicates" : len(set(submission.replicates))
        #     }
        # #get the state tag 
        # #state_tag =  SubmissionStatesEnums(submission.state).name
        # if "att_proteome" not in submission.dataset_attributes:
        #     raise ProteomeNotFoundError("The proteome dataset attribute was not found.")
        
        # for proteome_tag in submission.dataset_attributes["att_proteome"]:
        #     if not self._proteomes.exist(proteome_tag):
        #         raise ProteomeNotFoundError(f"The proteome {proteome_tag} was not found in the database. Please add it before inserting the submission.")
        
        # samples = [{"tag" : sample_name, "props" : {"index" : idx, "replicate" : submission.replicates[idx], "text" : sample_name}} for idx,sample_name in enumerate(sample_names)]
        # dataset_attributes =  [tag for tag in submission.dataset_attributes.keys()]

                
        # dataset_attribute_values = [{"attribute_value_tag" : tag, #remove!! att_ is history 
        #                              "attribute_tag" : attribute_tag, 
        #                              "trait_value" : extract_user_input(dataset_attribute_input[attribute_tag][tag]) if attribute_tag in dataset_attribute_input and dataset_attribute_input[attribute_tag][tag] else []} 
        #                             for attribute_tag,tags in submission.dataset_attributes.items() for tag in tags]
        
        # dataset_attributes_units = [x for x in dataset_attribute_values if isinstance(x["trait_value"],list) and len(x["trait_value"]) > 0]
        
        # query = (
        #     "MERGE (submission:Submission {tag : $submission_tag}) "
        #     "SET submission += $dataset_props "
        #     "WITH submission "
        #     "MATCH (state:State {tag : $state_tag}) "
        #     "MERGE (submission)-[r_in_state:IN_STATE]->(state) "
        #     "SET r_in_state.created_at = timestamp(), r_in_state.user_tag = $user_tag "
        #     "WITH submission "
        #     "UNWIND $samples as sample_name "
        #     "MERGE (s:Sample {tag : sample_name.tag}) "
        #     "SET s += sample_name.props "
        #     "SET s.created_at = timestamp() "
        #     "WITH s, submission "
        #     "MERGE (s)<-[:HAS_SAMPLE]-(submission) "   
        #     "WITH submission "
        #     "UNWIND $dataset_attributes as attribute_tag "
        #     "MATCH (a:Attribute {tag : attribute_tag}) "
        #     "MERGE (submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a) "
        #     "WITH submission "
        #     "UNWIND $dataset_attribute_values as attribute_value "
        #     "MATCH (av:AttributeValue {tag : attribute_value.attribute_value_tag}) "
        #     "MATCH (a:Attribute {tag : attribute_value.attribute_tag}) "
        #     "MERGE (submission)-[r:HAS_ATTRIBUTE_VALUE]->(av) "
        #     "SET r.created_at = timestamp(), r.attribute_tag = a.tag "
        #     "MERGE (av)-[:HAS_VALUE]-(a) "

        #     ""
        # )
    
        # self._driver.execute_query(query, routing_="w", 
        #                            samples = samples, 
        #                            user_tag = submission.user_tag,
        #                            submission_tag = submission_tag, 
        #                            dataset_attributes  = dataset_attributes, 
        #                            state_tag = submission.state, 
        #                            dataset_props = dataset_props, 
        #                            dataset_attribute_values = dataset_attribute_values)
        
        
        # #add units 
        # if len(dataset_attributes_units) > 0:
        #     query = (
        #         "MATCH (submission:Submission {tag : $submission_tag}) "
        #         "UNWIND $dataset_attribute_values AS attribute_value "
        #         "UNWIND attribute_value.trait_value AS trait "
        #         "WITH attribute_value, trait "
        #         "MATCH (av:AttributeValue {tag: attribute_value.attribute_value_tag}) "
        #         "MATCH (unit:Unit {tag: trait.unit_tag}) "
        #         "MERGE (av)-[r:HAS_VALUE_OF_UNIT]-(unit) "
        #         "SET r.value = trait.value, r.submission_tag = $submission_tag, r.unittype_tag = trait.unittype_tag "
        #         "RETURN av, unit, r "
        #     )
        #     r = self._driver.execute_query(query,routing_="w",submission_tag = submission_tag, dataset_attribute_values = dataset_attributes_units, result_transformer_=Result.value)
        
        # try:
        #     self._meta.add_samples_attributes(meta_data=submission)
        #     sample_attributes_added = 1 
        # except Exception as e:
        #     print(e) 
        #     print("No sample attributes added ")
        # try:
        #     self._meta.add_samples_genotypes(meta_data=submission)
        #     genotypes_added = 1 
        # except:
        #     print("No genotypes found")
            
        # if genotypes_added == 0 and sample_attributes_added == 0: raise ValueError("Neither genotypes nor sample attributes could be defined for this project. ")
        
        # self._meta.add_owner(tag=submission_tag, user_tag=submission.user_tag)
        # self._meta.add_collaborators(tag=submission_tag, user_tags=submission.collaborators)
        
        # print(submission.metatext)
        
        # self._meta.add_metatext(tag=submission_tag, user_tag= submission.user_tag, meta_texts=submission.metatext)
        
    
    def insert_attributes(self, tag, traits : List[AttributeTree]) -> bool:
        """Inserts the dataset attributes for a submission. 
        """
         
         
        if not self.exists(tag):  
            raise ValueError("Submission with this tag does not exist. Please create the submission first.")
        for attribute_tree in traits:
            self.insert_condition_application(tag = tag,
                                        trait_data = [attribute_tree.model_dump()]) 
        
    def handle_children(self, submission_tag, trait_node, parent_tag):
        
        for attribute_node in trait_node["children"]:
            if attribute_node.get("type") != "attribute":
                raise ValueError("The child node is not an Attribute node. Attribute and Trait nodes must always be used as children of a ConditionApplication node in alternating order.")
            attribute_tag = attribute_node["tag"]
            trait_nodes = attribute_node["children"]
            if len(trait_nodes) > 0:
                for trait_node in trait_nodes:
                    if trait_node.get("type") != "trait":
                        raise ValueError("The child node is not a Trait node.")
                    parent_tag_2 = self.add_condition_value(
                                                            attribute_tag=attribute_tag, 
                                                            value = trait_node.get("value"),
                                                            trait_tag= trait_node["tag"], 
                                                            parent_tag=parent_tag)
                    
                    if len(trait_node.get("children",[])) > 0:
                        self.handle_children(submission_tag, trait_node=trait_node, parent_tag=parent_tag_2)
    
    def add_condition_value(self, parent_tag : str, attribute_tag : str, trait_tag : str, value : str|float|int = None ):
        """Adds a condition value to a submission. This is used to add conditions to the submission that are not specific to a sample but to the whole submission.

        Parameters
        ----------
        submission_tag : str
            The submission tag to which the condition value should be added.
        parent_tag : str
            The parent tag of the condition value.
        attribute_tag : str
            The attribute tag of the condition value.
        trait_tag : str
            The trait tag of the condition value.
        value : str | float | int, optional
            The value of the condition. This is usually a concentration or a temperature (very likely to be numeric). , by default None

        Returns
        -------
        _type_
            _description_
        """
        cv_tag = uuid.uuid4().hex
        query = (
            "MATCH (ca:ConditionApplication|ConditionValue {tag : $parent_tag}) " #maybe a ConditionValue or a ConditionApplication
            "MERGE (cv:ConditionValue {tag : $cv_tag, text : $cv_tag}) "
        )
        if value is not None:
            query += "SET cv.value = $value "
            
        query += (
                "WITH ca,cv "
                "MATCH (a:Attribute {tag : $attribute_tag})-[:PART_OF]->(ag:AttributeGroup {tag : 'dataset'}) " #only dataset attributes are allowed here
                "MATCH (t:Trait {tag : $trait_tag}) "
                "WITH ca,cv,a,t "
                "MERGE (cv)-[:OF_ATTRIBUTE]-(a) "
                "MERGE (cv)-[:HAS_TRAIT]-(t) "
                "MERGE (ca)-[r:HAS_VALUE]->(cv) "
                "SET r.created_at = timestamp(), r.attribute_tag = $attribute_tag, r.trait_tag = $trait_tag "
            )
        
        self._driver.execute_query(query, value = value, trait_tag = trait_tag, cv_tag = cv_tag, attribute_tag = attribute_tag, parent_tag = parent_tag)
        return cv_tag 
    
    def insert_condition_application(self, tag : str, attribute_tag : str = None,  trait_tag : str = None, trait_data : List[dict] = None):
        """ Inserts a condition procedure into the database connect to a submission This indicates that all samples
        of the submission are affected by this condition. There are also ConditionApplication nodes that are connected to the samples via the 
        HAS_APPLICATION relationship and are manage by the Samples DB class. These are then specific for a given sample"""

        submission_tag = tag
        print(trait_data, "trait data")
        if trait_tag is not None and trait_data is None or len(trait_data) == 0:

            trait_data = [
                {"type" : "attribute", "tag" : "att_compound", 
                 "children" : [
                     {"type": "trait", "tag": trait_tag, "children": []}
                 ]}
           ]    

        ca_tag = create_hierarchical_hash(trait_data)
        if self.condition_application_exists(tag = ca_tag):
            ##if exists, then just connect to the submission
            query = (
                "MATCH (ca:ConditionApplication {tag : $ca_tag}) "
                "MATCH (s:Submission {tag : $submission_tag}) "
                "MERGE (s)-[:HAS_APPLICATION]->(ca) "
            )

            self._driver.execute_query(query, routing_="w", ca_tag = ca_tag, submission_tag = submission_tag)

        else:
            
            for condition_application in trait_data:
                attribute_tag = condition_application["tag"]
                for trait_node in condition_application["children"]:
                    trait_tag = trait_node["tag"]
                    query = (
                        "MERGE (s:Submission {tag : $submission_tag}) "
                        "MERGE (ca:ConditionApplication {tag : $ca_tag}) "
                        "WITH ca, s "
                        "MERGE (a:Attribute {tag : $attribute_tag}) "
                        "MERGE (t:Trait {tag : $trait_tag}) "
                        #connect to submission 
                        "MERGE (s)-[:HAS_APPLICATION]->(ca) "
                        "MERGE (ca)-[:OF_ATTRIBUTE]->(a) "
                        "MERGE (ca)-[:INSTANCE_OF]-(t) "
                    )
                    
                    self._driver.execute_query(query, routing_= "w", ca_tag = ca_tag, submission_tag = submission_tag, trait_tag = trait_tag, attribute_tag = attribute_tag)        
                    
                    if len(trait_node.get("children",[])) > 0:
                        # for child in trait_node["children"]:
                        print("has children!! ", trait_node["children"])
                        self.handle_children(submission_tag, trait_node=trait_node, parent_tag=ca_tag)
                
    
    
    


    def insert_comment(self, tag : str, comment : SubmissionCommentModel):
        ""         
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "MATCH (user:User) "
            "WHERE user.tag = $comment.user_tag "
            "MERGE (comment: Comment {tag : $comment.tag}) "
            "SET comment.content = $comment.content, comment.created_at = timestamp(), comment.user_tag = comment.user_tag "
            "MERGE (submission)-[:HAS]->(comment) "
            "MERGE (user)-[r:CREATED]->(comment) "
            "SET r.created_at = timestamp() "
        )
        try: 
            self._driver.execute_query(query, tag = tag, comment = comment.model_dump(exclude_none=True))
        except Exception as e:
            print(e)
            return False 
        
    
    def get_comments(self, tag : str) -> List[SubmissionCommentModel]:
        "Returns the available comments for a given submission tag."
        
        query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS]-(comment:Comment)-[r:CREATED]-(u:User) "
            "RETURN {user_tag : u.tag, created_at : r.created_at, content : comment.content, tag : comment.tag} "
            
        )
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return [SubmissionCommentModel(**c) for c in r ]
        
    def get(self, tag: str) -> DatasetSubmissionModel:
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
    
    
    def get_correlated_features(self, tags : List[str], 
                                feature_tag : str, 
                                filter_tag : str = None,  
                                direction : Literal["positive","negative","both"] = "both", 
                                limit : int = 20, 
                                min_data_points : int = 20):
        """Correlates a feature to all other features 
        by its feature_tag in the submissions given by 'tags' . 

        Parameters
        ----------
        tags : List[stt] - List of submissions 
        feature_tag : str
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
        print(r)
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
        print(states)
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
        print(r)
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
        