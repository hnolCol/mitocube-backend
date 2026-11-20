from typing import List, Tuple, Literal, Dict              
from neo4j import Driver, Result
import pandas as pd 
from services.encryption import create_hierarchical_hash
from lib.database.abstract.ResearchGroup import ResearchGroupABC
from config.models.researchgroup import ResearchGroupInput, ResearchGroupModel
from lib.cache.scope_cache import invalidate_cached_scope, invalidate_all_cached_scopes

class Neo4JResearchGroup(ResearchGroupABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
    
    def _utils_insert_from_file(self, file_path : str, *args, **kwargs) -> pd.DataFrame:
        """Inserts research groups from a txt file and returns a DataFrame with the generated tags."""
        tags = []
        df = pd.read_csv(file_path, *args, **kwargs)
        research_groups = [ResearchGroupInput(**row) for row in df.to_dict(orient="records")]
        for rg in research_groups:
            tag = create_hierarchical_hash(rg.model_dump())
            tags.append(tag)
            if self.exists(tag):
                print("Research group already exists: ", tag, rg.text)
                continue
            self.insert(tag, rg)
            print("Research group inserted: ", tag, rg.text)
        df.loc[:,"tag"] = tags 
        return df 
    
    def insert_users(self, tag : str, user_tags : List[str]):
        ""
        if not self.exists(tag): raise ValueError("Research group with tag {tag} does not exist.")
        
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag}) "
            "UNWIND $user_tags as user_tag "
            "MATCH (u:User {tag : user_tag}) "
            "MERGE (rg)<-[r:MEMBER_OF]-(u) "
            "ON CREATE "
            "SET r.created_at = timestamp() "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag, user_tags = user_tags)
        
        for user_tag in user_tags:
            invalidate_cached_scope(user_tag)
    def delete(self, tag: str) -> bool:
        return super().delete(tag)
       
    def exists(self, tag: str) -> bool:
        ""
        query = (
            "WITH EXISTS {(rg:ResearchGroup {tag : $tag})} as rg_exists "
            "RETURN rg_exists "
            )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]

    def find(self, search_string: str = None, user_tags: List[str] = None, submission_tags: List[str] = None, limit: int = 40) -> List[str]:
        """Finds research group tags that match the search string, user tags, or submission tags."""
        
        if user_tags is not None:
            query = (
                "MATCH (rg:ResearchGroup)<-[:MEMBER_OF]-(u:User) "
                "WHERE u.tag IN $user_tags "
            )
            if submission_tags is not None:
                query += "AND EXISTS {(rg)<-[:MEMBER_OF]-(su:User)-[:CREATED|COLLABORATES]->(s:Submission) WHERE s.tag IN $submission_tags} "
        elif submission_tags is not None:
            query = (
                "MATCH (rg:ResearchGroup)<-[:MEMBER_OF]-(u:User)-[:CREATED|COLLABORATES]->(s:Submission) "
                "WHERE s.tag IN $submission_tags "
            )
        else:
            query = (
                "MATCH (rg:ResearchGroup) "
                "WHERE true "
            )
        
        if search_string is not None and search_string != "":
            query += "AND (toLower(rg.text) CONTAINS $search_string OR toLower(rg.abbreviation) CONTAINS $search_string OR toLower(rg.tag) CONTAINS $search_string) "
        
        query += "RETURN DISTINCT rg.tag as tag "
        
        if limit is not None:
            query += "LIMIT $limit"
        
        r = self._driver.execute_query(
            query,
            routing_="r",
            result_transformer_=Result.value,
            search_string=search_string.lower() if search_string is not None else None,
            user_tags=user_tags,
            submission_tags=submission_tags,
            limit=limit
        )
        return r
        
    
    def get(self, tag : str) -> ResearchGroupModel:
        
        query = (
            "MATCH (rg:ResearchGroup) "
            "WHERE rg.tag = $tag "
            "RETURN properties(rg) "
        )

        r = self._driver.execute_query(query, routing_="r",result_transformer_=Result.value, tag = tag)

        return ResearchGroupModel(**r[0]) if len(r) > 0 else None
    
    def count(self) -> int:
        "Returns the number of research groups in the database"
        query = (
            "MATCH (rg:ResearchGroup) "
            "RETURN count(rg) "
        )
        
        r = self._driver.execute_query(query, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return 0
        return r[0]
    
    def get_submissions_count(self, tag : str) -> int:
        "Returns the number of submissions associated with the research group"
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[:MEMBER_OF]-(u:User)-[:CREATED|COLLABORATES]->(s:Submission) "
            "RETURN count(DISTINCT s) "
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return 0
        return r[0]
    
    
    def get_submission_tags(self, tags : List[str]) -> List[str]:
        "Returns the submission tags associated with the research groups"
        query = (
            "MATCH (rg:ResearchGroup) <-[:MEMBER_OF]-(u:User)-[:CREATED]->(s:Submission) "
            "WHERE rg.tag IN $tags "
            "RETURN s.tag order by s.created_at desc "
        )
        
        r = self._driver.execute_query(query, tags = tags, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return []
        return r
    
    def get_samples_count(self, tag : str) -> int:
        "Returns the number of samples associated with the research group"
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[:MEMBER_OF]-(u:User)-[:CREATED]->(s:Submission)-[:HAS_SAMPLE]->(sa:Sample) "
            "RETURN count(DISTINCT sa) "
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return 0
        return r[0]

    def get_tags(self, limit : int = 40) -> List[str]:
        "Returns the tags of the research groups, ordered by creation date"
        
        query = (
            "MATCH (rg:ResearchGroup) "
            "RETURN rg.tag ORDER BY rg.created_at DESC LIMIT $limit"
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, limit=limit)
        return r 
    
    def get_users(self, tag : str) -> List[str]:
        "Returns the user tags that are part of the research group"
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[r:MEMBER_OF]-(u:User) "
            "RETURN collect(u.tag) "
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return []
        return r[0]
        
        
    def get_users_count(self, tag : str) -> int:
        "Returns the number of users that are part of the research group"
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[r:MEMBER_OF]-(u:User) "
            "RETURN count(u) "
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return 0
        return r[0]
    
    def insert(self, tag : str, research_group : ResearchGroupInput):
        "" 
        if self.exists(tag): raise ValueError("Tag exists already. Delete first or use the update function.")
        
        query = (
            "MERGE (rg:ResearchGroup {tag : $tag}) "
            "ON CREATE "
            "SET rg.created_at = timestamp(), rg.text =  $research_group.text, rg.abbreviation =  $research_group.abbreviation, "
            "rg.address =  $research_group.address, rg.email =  $research_group.email, rg.institute =  $research_group.institute, rg.url =  $research_group.url, "   
            "rg.profile_text =  $research_group.profile_text "
            "ON MATCH "
            "SET rg.modified_at = timestamp(), rg.text =  $research_group.text, rg.abbreviation =  $research_group.abbreviation, "
            "rg.address =  $research_group.address, rg.email =  $research_group.email, rg.institute =  $research_group.institute, rg.url =  $research_group.url, "   
            "rg.profile_text =  $research_group.profile_text "
            "RETURN rg.tag"
        )
        
        r = self._driver.execute_query(query, routing_="w", tag = tag, research_group = research_group.model_dump(exclude_none=True), result_transformer_=Result.value)
        return True if len(r) > 0 else False
        
    def remove_users(self, tag : str, user_tags): 

        if not self.exists(tag): raise ValueError("Research group with tag {tag} does not exist.")
        
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag}) "
            "UNWIND $user_tags as user_tag "
            "MATCH (u:User {tag : user_tag}) "
            "MATCH (rg)<-[r:MEMBER_OF]-(u) "
            "OPTIONAL MATCH (u)-[h:HEAD_OF]->(rg) "
            "DELETE r, h"
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag, user_tags = user_tags)
        
        for user_tag in user_tags:
            invalidate_cached_scope(user_tag)
        
        
        
    def update(self, tag : str, research_group : ResearchGroupInput) -> bool:
        """Updates the properties of the research group with the given tag."""
        if not self.exists(tag): raise ValueError(f"Research group with tag {tag} does not exist.")
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag}) "
            "SET rg.modified_at = timestamp(), rg.text = $research_group.text, rg.abbreviation = $research_group.abbreviation, "
            "rg.address = $research_group.address, rg.email = $research_group.email, rg.institute = $research_group.institute, "
            "rg.url = $research_group.url, rg.profile_text = $research_group.profile_text "
            "RETURN rg.tag"
        )
        r = self._driver.execute_query(query, routing_="w", tag = tag, research_group = research_group.model_dump(exclude_none=True), result_transformer_=Result.value)
        return True if len(r) > 0 else False


    def get_heads(self, tag : str) -> List[str]:
        """Returns the user tags of the research group heads (PIs) of the given research group"""
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[r:HEAD_OF]-(u:User) "
            "RETURN u.tag ORDER BY u.tag "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return r

    def is_head(self, user_tag : str, group_tag : str = None) -> bool:
        """Checks if the user is a head (PI) of the given research group. If no group tag is given,
        checks if the user is a head of any research group."""
        if group_tag is not None:
            query = (
                "WITH EXISTS {(u:User {tag : $user_tag})-[:HEAD_OF]->(rg:ResearchGroup {tag : $group_tag})} as is_head "
                "RETURN is_head "
            )
            r = self._driver.execute_query(query, user_tag = user_tag, group_tag = group_tag, result_transformer_=Result.value)
        else:
            query = (
                "WITH EXISTS {(u:User {tag : $user_tag})-[:HEAD_OF]->(:ResearchGroup)} as is_head "
                "RETURN is_head "
            )
            r = self._driver.execute_query(query, user_tag = user_tag, result_transformer_=Result.value)
        return r[0]
    
    def get_headed_group_tags(self, user_tag : str) -> List[str]:
        """Returns the tags of the research groups the user is a head (PI) of"""
        query = (
            "MATCH (u:User {tag : $user_tag})-[:HEAD_OF]->(rg:ResearchGroup) "
            "RETURN rg.tag ORDER BY rg.tag "
        )
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag, result_transformer_=Result.value)
        return r

    def get_shared_submissions_overview(self, user_tag : str) -> List[Dict]:
        """Returns the sharing overview for the head (PI): one entry per submission created by
        the user or by a member of a group they head, with the submission and owner tags, the
        consortiums the submission is shared with (approved and pending) and the collaborating
        users (via approved collaboration requests, excluding the owner)."""
        query = (
            "MATCH (owner:User)-[:CREATED]->(s:Submission) "
            "WHERE owner.tag = $user_tag "
            "   OR EXISTS { MATCH (owner)-[:MEMBER_OF]->(:ResearchGroup)<-[:HEAD_OF]-(:User {tag : $user_tag}) } "
            "OPTIONAL MATCH (s)-[sh:SHARED_WITH]->(c:Consortium) "
            "WITH s, owner, "
            "     [x IN collect(DISTINCT CASE WHEN sh.status = 'approved' THEN c.tag END) WHERE x IS NOT NULL] AS consortium_tags, "
            "     [x IN collect(DISTINCT CASE WHEN sh.status = 'pending' THEN c.tag END) WHERE x IS NOT NULL] AS pending_consortium_tags "
            "OPTIONAL MATCH (collaborator:User)-[:COLLABORATES]->(s) "
            "WITH s, owner, consortium_tags, pending_consortium_tags, collect(DISTINCT collaborator.tag) AS all_collaborators "
            "RETURN s.tag AS submission_tag, owner.tag AS owner_tag, consortium_tags, "
            "       pending_consortium_tags, "
            "       [x IN all_collaborators WHERE x <> owner.tag] AS collaborator_tags "
            "ORDER BY s.tag "
        )
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag, result_transformer_=Result.data)
        return r

    def set_head(self, group_tag : str, user_tag : str):
        """Makes the user a head (PI) of the research group. The user must be a member of the research group."""
        if not self.exists(group_tag): raise ValueError(f"Research group with tag {group_tag} does not exist.")
        if user_tag not in self.get_users(group_tag):
            raise ValueError(f"User with tag {user_tag} is not a member of the research group with tag {group_tag}.")

        query = (
            "MATCH (rg:ResearchGroup {tag : $group_tag}) "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (u)-[r:HEAD_OF]->(rg) "
            "ON CREATE "
            "SET r.created_at = timestamp() "
        )
        self._driver.execute_query(query, routing_="w", group_tag = group_tag, user_tag = user_tag)

    def remove_head(self, group_tag : str, user_tag : str):
        """Removes the user as head (PI) of the research group"""
        if not self.exists(group_tag): raise ValueError(f"Research group with tag {group_tag} does not exist.")

        query = (
            "MATCH (rg:ResearchGroup {tag : $group_tag})<-[r:HEAD_OF]-(u:User {tag : $user_tag}) "
            "DELETE r"
        )
        self._driver.execute_query(query, routing_="w", group_tag = group_tag, user_tag = user_tag)
    
    def get_explore_disabled(self, tag : str) -> bool:
        """Returns whether the explore visibility of the groups submissions is disabled.
        Disabled is the default, e.g. for new research groups"""
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag}) "
            "RETURN coalesce(rg.explore_disabled, true) "
        )
        r = self._driver.execute_query(query, tag = tag, routing_ = "r", result_transformer_ = Result.value)
        if len(r) == 0: return True
        return bool(r[0])

    def set_explore_disabled(self, tag : str, disabled : bool) -> bool:
        """Sets whether the head (PI) of the research group disabled the explore
        visibility of the groups submissions. Requires the head (PI) of the group or a curator (router enforced).
        When disabling, all collaboration access (COLLABORATES) of the groups submissions is revoked and
        pending collaboration requests for them are deleted, mirroring disagreeing to consortium terms
        revoking the consortium shares."""
        if not self.exists(tag): raise ValueError(f"Research group with tag {tag} does not exist.")
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag}) "
            "SET rg.explore_disabled = $disabled "
            "RETURN rg.tag "
        )
        r = self._driver.execute_query(query, tag = tag, disabled = bool(disabled), routing_ = "w", result_transformer_ = Result.value)
        if disabled and len(r) > 0:
            revoke_query = (
                "MATCH (rg:ResearchGroup {tag : $tag})<-[:MEMBER_OF]-(:User)-[:CREATED]->(s:Submission) "
                "OPTIONAL MATCH (u:User)-[collab:COLLABORATES]->(s) "
                "DELETE collab "
                "WITH DISTINCT s "
                "OPTIONAL MATCH (cr:CollaborationRequest)-[:FOR_SUBMISSION]->(s) "
                "WHERE cr.status = 'pending' "
                "DELETE cr "
                "RETURN true "
            )
            self._driver.execute_query(revoke_query, routing_ = "w", tag = tag)
            invalidate_all_cached_scopes()
        return len(r) > 0

    def get_explore_disabled_group_tags(self) -> List[str]:
        "Returns the tags of all research groups whose explore visibility is disabled (the default for new groups)"
        query = (
            "MATCH (rg:ResearchGroup) "
            "WHERE coalesce(rg.explore_disabled, true) "
            "RETURN rg.tag ORDER BY rg.tag "
        )
        return self._driver.execute_query(query, routing_ = "r", result_transformer_ = Result.value)

    def set_subgroup(self, parent_tag : str, child_tag : str):
        "Defines a parent-child relationship between two research groups, where the child group is a subgroup of the parent group."
        if not self.exists(parent_tag): raise ValueError(f"Parent research group with tag {parent_tag} does not exist.")
        if not self.exists(child_tag): raise ValueError(f"Child research group with tag {child_tag} does not exist.")
        
        query = (
            "MATCH (parent:ResearchGroup {tag : $parent_tag}) "
            "MATCH (child:ResearchGroup {tag : $child_tag}) "
            "MERGE (child)-[:SUBGROUP_OF]->(parent) "
        )
        
        self._driver.execute_query(query, routing_="w", parent_tag = parent_tag, child_tag = child_tag)
        
    def remove_subgroup(self, parent_tag : str, child_tag : str):
        "Removes the parent-child relationship between two research groups."
        if not self.exists(parent_tag): raise ValueError(f"Parent research group with tag {parent_tag} does not exist.")
        if not self.exists(child_tag): raise ValueError(f"Child research group with tag {child_tag} does not exist.")
        
        query = (
            "MATCH (parent:ResearchGroup {tag : $parent_tag})<-[r:SUBGROUP_OF]-(child:ResearchGroup {tag : $child_tag}) "
            "DELETE r"
        )
        
        self._driver.execute_query(query, routing_="w", parent_tag = parent_tag, child_tag = child_tag)



    def get_sharing_overview(self) -> List[Dict]:
        """Returns the platform-wide sharing overview for admins and curators: one entry per
        submission shared in any way, with the submission and owner tags, the owners research
        groups, the approved and pending consortium shares, the collaborating users (explore
        view shares) and the pending collaboration requests"""
        query = (
            "MATCH (owner:User)-[:CREATED]->(s:Submission) "
            "OPTIONAL MATCH (s)-[sh:SHARED_WITH]->(c:Consortium) "
            "OPTIONAL MATCH (owner)-[:MEMBER_OF]->(og:ResearchGroup) "
            "WITH s, owner, "
            "     [x IN collect(DISTINCT CASE WHEN sh.status = 'approved' THEN c.tag END) WHERE x IS NOT NULL] AS consortium_tags, "
            "     [x IN collect(DISTINCT CASE WHEN sh.status = 'pending' THEN c.tag END) WHERE x IS NOT NULL] AS pending_consortium_tags, "
            "     [x IN collect(DISTINCT og.tag) WHERE x IS NOT NULL] AS owner_group_tags "
            "OPTIONAL MATCH (collaborator:User)-[:COLLABORATES]->(s) "
            "WITH s, owner, consortium_tags, pending_consortium_tags, owner_group_tags, "
            "     [x IN collect(DISTINCT CASE WHEN collaborator.tag IS NOT NULL AND collaborator.tag <> owner.tag THEN collaborator.tag END) WHERE x IS NOT NULL] AS collaborator_tags "
            "OPTIONAL MATCH (cr:CollaborationRequest)-[:FOR_SUBMISSION]->(s) "
            "WHERE cr.status = 'pending' "
            "WITH s, owner, consortium_tags, pending_consortium_tags, owner_group_tags, collaborator_tags, "
            "     collect(DISTINCT {requested_by: cr.requested_by, requested_for_user_tag: cr.requested_for_user_tag, requested_for_group_tag: cr.requested_for_group_tag, created_at: cr.created_at}) AS requests "
            "WITH s, owner, consortium_tags, pending_consortium_tags, owner_group_tags, collaborator_tags, "
            "     [r IN requests WHERE r.requested_by IS NOT NULL] AS pending_collaboration_requests "
            "WHERE size(consortium_tags) > 0 OR size(pending_consortium_tags) > 0 OR size(collaborator_tags) > 0 OR size(pending_collaboration_requests) > 0 "
            "RETURN s.tag AS submission_tag, owner.tag AS owner_tag, owner_group_tags, consortium_tags, "
            "       pending_consortium_tags, collaborator_tags, pending_collaboration_requests "
            "ORDER BY s.tag "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data)
        return r