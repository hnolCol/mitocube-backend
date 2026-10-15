from typing import Dict, List, Optional

from neo4j import Driver, Result

from lib.database.abstract.Collaborations import CollaborationsABC
from config.models.collaborations import (
    CollaborationRequestInput,
    CollaborationRequestModel,
    SubmissionExploreModel,
)
from services.random_generators import get_random_string
from lib.cache.scope_cache import invalidate_cached_scope
from config.settings.general import get_general_settings


class Neo4JCollaborations(CollaborationsABC):

    def __init__(self, driver : Driver) -> None:
        self._driver = driver

    def _is_head_of_requester(self, user_tag : str, request : "CollaborationRequestModel") -> bool:
        """Checks if the user is a head (PI) of a research group of the user that
        created the collaboration request."""
        query = (
            "MATCH (requester:User {tag : $requester_tag})-[:MEMBER_OF]->(rg:ResearchGroup) "
            "RETURN EXISTS { (pi:User {tag : $user_tag})-[:HEAD_OF]->(rg) } "
        )
        r = self._driver.execute_query(query, requester_tag = request.requested_by, user_tag = user_tag,
                                       result_transformer_=Result.value)
        return bool(r[0]) if len(r) > 0 else False

    def _submission_exists(self, submission_tag : str) -> bool:
        query = "RETURN EXISTS { (s:Submission {tag : $submission_tag})} "
        r = self._driver.execute_query(query, submission_tag = submission_tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False

    def create_collaboration_request(self, submission_tag : str, requested_by : str, input : CollaborationRequestInput) -> Optional[str]:
        """Creates a pending collaboration request for a submission. The request
        is created by a user and can request collaboration for the user itself
        or for one of their research groups (all members become collaborators)."""
        if not self._submission_exists(submission_tag):
            raise ValueError(f"Submission with tag {submission_tag} does not exist.")

        target_user_tag = input.requested_for_user_tag
        target_group_tag = input.requested_for_group_tag
        if target_user_tag is None and target_group_tag is None:
            target_user_tag = requested_by

        # guard against requests for other users that are not the requesting user
        if target_user_tag is not None and target_user_tag != requested_by:
            raise ValueError("A collaboration request can only be created for the requesting user or one of their research groups.")

        if target_group_tag is not None:
            query_check_group = (
                "MATCH (rg:ResearchGroup {tag : $group_tag})<-[:MEMBER_OF]-(u:User {tag : $user_tag}) "
                "RETURN count(u) "
            )
            r = self._driver.execute_query(query_check_group, group_tag = target_group_tag, user_tag = requested_by,
                                           result_transformer_=Result.value)
            if r[0] == 0:
                raise ValueError("A group collaboration request can only be created for a research group the user is a member of.")

        if self.has_pending_collaboration_request_for(submission_tag, target_user_tag, target_group_tag):
            return None

        request_tag = get_random_string(N = 12)
        query = (
            "MATCH (s:Submission {tag : $submission_tag}) "
            "MATCH (u:User {tag : $requested_by}) "
            "MERGE (cr:CollaborationRequest {tag : $request_tag}) "
            "ON CREATE SET cr.created_at = timestamp(), cr.status = 'pending', "
            "cr.requested_by = $requested_by, cr.message = $message, "
            "cr.requested_for_user_tag = $requested_for_user_tag, "
            "cr.requested_for_group_tag = $requested_for_group_tag "
            "MERGE (cr)-[:FOR_SUBMISSION]->(s) "
            "MERGE (u)-[:REQUESTED]->(cr) "
            "RETURN cr.tag "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       request_tag = request_tag,
                                       submission_tag = submission_tag,
                                       requested_by = requested_by,
                                       message = input.message,
                                       requested_for_user_tag = target_user_tag,
                                       requested_for_group_tag = target_group_tag,
                                       result_transformer_=Result.value)
        if len(r) == 0:
            return None
        return request_tag

    def _row_to_request_model(self, row : Dict) -> CollaborationRequestModel:
        return CollaborationRequestModel(
            tag = row["tag"],
            submission_tag = row["submission_tag"],
            requested_by = row["requested_by"],
            created_at = row["created_at"],
            requested_for_user_tag = row.get("requested_for_user_tag"),
            requested_for_group_tag = row.get("requested_for_group_tag"),
            message = row.get("message"),
            status = row.get("status", "pending"),
        )

    def get_collaboration_request(self, request_tag : str) -> Optional[CollaborationRequestModel]:
        query = (
            "MATCH (cr:CollaborationRequest {tag : $request_tag})-[:FOR_SUBMISSION]->(s:Submission) "
            "RETURN cr.tag AS tag, s.tag AS submission_tag, cr.requested_by AS requested_by, "
            "cr.created_at AS created_at, cr.requested_for_user_tag AS requested_for_user_tag, "
            "cr.requested_for_group_tag AS requested_for_group_tag, cr.message AS message, "
            "cr.status AS status "
        )
        r = self._driver.execute_query(query, request_tag = request_tag, result_transformer_=Result.data)
        if len(r) == 0: return None
        return self._row_to_request_model(r[0])

    def has_pending_collaboration_request(self, submission_tag : str, requested_by : str) -> bool:
        query = (
            "MATCH (cr:CollaborationRequest)-[:FOR_SUBMISSION]->(s:Submission {tag : $submission_tag}) "
            "WHERE cr.requested_by = $requested_by AND cr.status = 'pending' "
            "RETURN count(cr) "
        )
        r = self._driver.execute_query(query, submission_tag = submission_tag, requested_by = requested_by,
                                       result_transformer_=Result.value)
        return r[0] > 0 if len(r) > 0 else False

    def has_pending_collaboration_request_for(self, submission_tag : str, requested_for_user_tag : str, requested_for_group_tag : str) -> bool:
        query = (
            "MATCH (cr:CollaborationRequest)-[:FOR_SUBMISSION]->(s:Submission {tag : $submission_tag}) "
            "WHERE cr.status = 'pending' "
            "AND ( (cr.requested_for_user_tag = $requested_for_user_tag AND $requested_for_user_tag IS NOT NULL) "
            "   OR (cr.requested_for_group_tag = $requested_for_group_tag AND $requested_for_group_tag IS NOT NULL) ) "
            "RETURN count(cr) "
        )
        r = self._driver.execute_query(query, submission_tag = submission_tag,
                                       requested_for_user_tag = requested_for_user_tag,
                                       requested_for_group_tag = requested_for_group_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0 if len(r) > 0 else False

    def has_approved_collaboration_request(self, submission_tag : str, user_tag : str) -> bool:
        query = (
            "MATCH (cr:CollaborationRequest)-[:FOR_SUBMISSION]->(s:Submission {tag : $submission_tag}) "
            "WHERE (cr.requested_for_user_tag = $user_tag OR cr.requested_by = $user_tag) AND cr.status = 'approved' "
            "RETURN count(cr) "
        )
        r = self._driver.execute_query(query, submission_tag = submission_tag, user_tag = user_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0 if len(r) > 0 else False

    def approve_collaboration_request(self, request_tag : str, approved_by : str) -> bool:
        """Approves a pending collaboration request. The requested user or all
        members of the requested research group are added as collaborators of
        the submission and the request status is set to approved.
        If require_pi_approval_for_collaboration_requests is enabled, the request
        needs the approval of the head (PI) of the requesting users research group
        IN ADDITION to the approval of the submission owner: the first approval is
        recorded (owner_approved or pi_approved) and only when both are present the
        request is granted."""
        request = self.get_collaboration_request(request_tag)
        if request is None or request.status != "pending":
            return False

        require_pi = get_general_settings().require_pi_approval_for_collaboration_requests
        is_owner_side = self._is_owner_or_head_of_owner(approved_by, request)
        is_pi_of_requester = self._is_head_of_requester(approved_by, request)

        if require_pi:
            # track both approvals; grant only when both sides have approved
            if is_owner_side and not is_pi_of_requester:
                status_query = (
                    "MATCH (cr:CollaborationRequest {tag : $request_tag}) "
                    "WHERE cr.status = 'pending' AND coalesce(cr.pi_approved, false) = true "
                    "SET cr.status = 'approved', cr.approved_by = $approved_by, cr.approved_at = timestamp() "
                    "RETURN cr.status AS status "
                )
                r = self._driver.execute_query(status_query, routing_="w", request_tag = request_tag,
                                                approved_by = approved_by, result_transformer_=Result.value)
                if len(r) > 0:
                    self._grant_collaborators(request_tag, request)
                    return True
                mark_query = (
                    "MATCH (cr:CollaborationRequest {tag : $request_tag}) "
                    "SET cr.owner_approved = true, cr.owner_approved_by = $approved_by, "
                    "cr.owner_approved_at = timestamp() "
                    "RETURN cr.tag "
                )
                self._driver.execute_query(mark_query, routing_="w", request_tag = request_tag,
                                            approved_by = approved_by, result_transformer_=Result.value)
                return True
            if is_pi_of_requester and not is_owner_side:
                status_query = (
                    "MATCH (cr:CollaborationRequest {tag : $request_tag}) "
                    "WHERE cr.status = 'pending' AND coalesce(cr.owner_approved, false) = true "
                    "SET cr.status = 'approved', cr.approved_by = $approved_by, cr.approved_at = timestamp() "
                    "RETURN cr.status AS status "
                )
                r = self._driver.execute_query(status_query, routing_="w", request_tag = request_tag,
                                                approved_by = approved_by, result_transformer_=Result.value)
                if len(r) > 0:
                    self._grant_collaborators(request_tag, request)
                    return True
                mark_query = (
                    "MATCH (cr:CollaborationRequest {tag : $request_tag}) "
                    "SET cr.pi_approved = true, cr.pi_approved_by = $approved_by, "
                    "cr.pi_approved_at = timestamp() "
                    "RETURN cr.tag "
                )
                self._driver.execute_query(mark_query, routing_="w", request_tag = request_tag,
                                            approved_by = approved_by, result_transformer_=Result.value)
                return True
            if not is_owner_side and not is_pi_of_requester:
                return False
            # a user that is both owner-side and PI of the requester approves both at once
            status_query = (
                "MATCH (cr:CollaborationRequest {tag : $request_tag}) "
                "WHERE cr.status = 'pending' "
                "SET cr.status = 'approved', cr.approved_by = $approved_by, cr.approved_at = timestamp() "
                "RETURN cr.status AS status "
            )
            self._driver.execute_query(status_query, routing_="w", request_tag = request_tag,
                                       approved_by = approved_by, result_transformer_=Result.value)
            self._grant_collaborators(request_tag, request)
            return True

        if not is_owner_side:
            return False
        status_query = (
            "MATCH (cr:CollaborationRequest {tag : $request_tag}) "
            "WHERE cr.status = 'pending' "
            "SET cr.status = 'approved', cr.approved_by = $approved_by, cr.approved_at = timestamp() "
            "RETURN cr.status AS status "
        )
        self._driver.execute_query(status_query, routing_="w", request_tag = request_tag,
                                   approved_by = approved_by, result_transformer_=Result.value)
        self._grant_collaborators(request_tag, request)
        return True

    def _is_owner_or_head_of_owner(self, user_tag : str, request : "CollaborationRequestModel") -> bool:
        """Checks if the user is the owner (creator) of the requested submission or
        a head (PI) of one of the owners research groups."""
        creator_tag = self._get_submission_creator(request.submission_tag)
        if creator_tag is not None and user_tag == creator_tag:
            return True
        return self._is_head_of_submission_owner(user_tag, request.submission_tag)

    def _get_submission_creator(self, submission_tag : str) -> Optional[str]:
        query = "MATCH (u:User)-[:CREATED]->(s:Submission {tag : $submission_tag}) RETURN u.tag "
        r = self._driver.execute_query(query, submission_tag = submission_tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else None

    def _is_head_of_submission_owner(self, user_tag : str, submission_tag : str) -> bool:
        query = (
            "MATCH (owner:User)-[:CREATED]->(s:Submission {tag : $submission_tag}) "
            "RETURN EXISTS { (pi:User {tag : $user_tag})-[:HEAD_OF]->(:ResearchGroup)<-[:MEMBER_OF]-(owner) } "
        )
        r = self._driver.execute_query(query, user_tag = user_tag, submission_tag = submission_tag,
                                       result_transformer_=Result.value)
        return bool(r[0]) if len(r) > 0 else False

    def _grant_collaborators(self, request_tag : str, request : "CollaborationRequestModel") -> None:
        """Adds the requested user or all members of the requested research group
        as collaborators of the submission."""
        submission_tag = request.submission_tag
        collaborator_tags : List[str] = []
        if request.requested_for_group_tag:
            group_query = (
                "MATCH (rg:ResearchGroup {tag : $group_tag})<-[:MEMBER_OF]-(u:User) "
                "RETURN collect(u.tag) "
            )
            gr = self._driver.execute_query(group_query, group_tag = request.requested_for_group_tag,
                                            result_transformer_=Result.value)
            collaborator_tags = gr[0] if len(gr) > 0 and gr[0] else []
        elif request.requested_for_user_tag:
            collaborator_tags = [request.requested_for_user_tag]
        else:
            collaborator_tags = [request.requested_by]
        if not collaborator_tags:
            return
        add_query = (
            "MATCH (s:Submission {tag : $submission_tag}) "
            "UNWIND $collaborator_tags as collaborator_tag "
            "MATCH (u:User {tag : collaborator_tag}) "
            "MERGE (u)-[r:COLLABORATES]->(s) "
            "ON CREATE SET r.created_at = timestamp(), r.via_collaboration_request = true "
            "RETURN count(r) "
        )
        self._driver.execute_query(add_query, routing_="w",
                                   submission_tag = submission_tag,
                                   collaborator_tags = collaborator_tags,
                                   result_transformer_=Result.value)
        for collaborator_tag in collaborator_tags:
            invalidate_cached_scope(collaborator_tag)

    def deny_collaboration_request(self, request_tag : str) -> bool:
        query = (
            "MATCH (cr:CollaborationRequest {tag : $request_tag}) "
            "WHERE cr.status = 'pending' "
            "SET cr.status = 'denied', cr.denied_at = timestamp() "
            "RETURN count(cr) "
        )
        r = self._driver.execute_query(query, routing_="w", request_tag = request_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0 if len(r) > 0 else False

    def get_collaboration_requests_for_submission(self, submission_tag : str) -> List[CollaborationRequestModel]:
        query = (
            "MATCH (cr:CollaborationRequest)-[:FOR_SUBMISSION]->(s:Submission {tag : $submission_tag}) "
            "RETURN cr.tag AS tag, s.tag AS submission_tag, cr.requested_by AS requested_by, "
            "cr.created_at AS created_at, cr.requested_for_user_tag AS requested_for_user_with, "
            "cr.requested_for_group_tag AS requested_for_group_tag, cr.message AS message, cr.status AS status "
        )
        r = self._driver.execute_query(query, submission_tag = submission_tag, result_transformer_=Result.data)
        return [self._row_to_request_model(row) for row in r]

    def get_pending_collaboration_requests_for_head(self, user_tag : str) -> List[CollaborationRequestModel]:
        """Returns the pending collaboration requests the given research group head
        (PI) can approve: requests of members of the groups they lead and requests
        for submissions created by members of their groups."""
        query = (
            "MATCH (pi:User {tag : $user_tag})-[:HEAD_OF]->(rg:ResearchGroup)<-[:MEMBER_OF]-(requester:User) "
            "MATCH (requester)-[:REQUESTED]->(cr:CollaborationRequest)-[:FOR_SUBMISSION]->(s:Submission) "
            "WHERE cr.status = 'pending' "
            "RETURN DISTINCT cr.tag AS tag, s.tag AS submission_tag, cr.requested_by AS requested_by, "
            "cr.created_at AS created_at, cr.requested_for_user_tag AS requested_for_user_tag, "
            "cr.requested_for_group_tag AS requested_for_group_tag, cr.message AS message, cr.status AS status "
            "UNION "
            "MATCH (pi:User {tag : $user_tag})-[:HEAD_OF]->(rg:ResearchGroup)<-[:MEMBER_OF]-(owner:User) "
            "MATCH (owner)-[:CREATED]->(s:Submission)<-[:FOR_SUBMISSION]-(cr:CollaborationRequest) "
            "WHERE cr.status = 'pending' "
            "RETURN DISTINCT cr.tag AS tag, s.tag AS submission_tag, cr.requested_by AS requested_by, "
            "cr.created_at AS created_at, cr.requested_for_user_tag AS requested_for_user_tag, "
            "cr.requested_for_group_tag AS requested_for_group_tag, cr.message AS message, cr.status AS status "
        )
        r = self._driver.execute_query(query, user_tag = user_tag, result_transformer_=Result.data)
        return [self._row_to_request_model(row) for row in r]

    def get_pending_collaboration_requests_for_user(self, user_tag : str) -> List[CollaborationRequestModel]:
        query = (
            "MATCH (u:User {tag : $user_tag})-[:REQUESTED]->(cr:CollaborationRequest)-[:FOR_SUBMISSION]->(s:Submission) "
            "WHERE cr.status = 'pending' "
            "RETURN cr.tag AS tag, s.tag AS submission_tag, cr.requested_by AS requested_by, "
            "cr.created_at AS created_at, cr.requested_for_user_tag AS requested_for_user_tag, "
            "cr.requested_for_group_tag AS requested_for_group_tag, cr.message AS message, cr.status AS status "
        )
        r = self._driver.execute_query(query, user_tag = user_tag, result_transformer_=Result.data)
        return [self._row_to_request_model(row) for row in r]

    def explore(self, search_string : str = None, ca_tags : Optional[List[str]] = None,
                user_tags : Optional[List[str]] = None, limit : int = 40) -> List[SubmissionExploreModel]:
        """Returns minimal metadata of all submissions matching the search string
        and having ALL the given condition application and user tags (AND
        semantics, combined with the title search via AND as well).
        This is a discovery endpoint: it returns only the title, owner, research
        group, state and which filter tags matched, never any sensitive data."""
        ca_tags = [t for t in (ca_tags or []) if t]
        user_tags = [t for t in (user_tags or []) if t]
        query = (
            "MATCH (s:Submission) "
            "WHERE s.title IS NOT NULL "
        )
        params = {"limit" : limit, "ca_tags" : ca_tags, "user_tags" : user_tags}
        if search_string is not None:
            query += "AND toLower(s.title) CONTAINS toLower($search_string) "
            params["search_string"] = search_string
        if ca_tags:
            query += (
                "AND ALL(ca_tag IN $ca_tags WHERE EXISTS { "
                "MATCH (s)-[:HAS_APPLICATION]->(ca:ConditionApplication {tag : ca_tag}) "
                "OR EXISTS { MATCH (s)-[:HAS_SAMPLE]->(:Sample)-[:HAS_APPLICATION]->(ca:ConditionApplication {tag : ca_tag}) } }) "
            )
        if user_tags:
            query += (
                "AND ALL(user_tag IN $user_tags WHERE EXISTS { "
                "MATCH (u:User {tag : user_tag})-[:CREATED|COLLABORATES]->(s) }) "
            )
        query += (
            "OPTIONAL MATCH (owner:User)-[:CREATED]->(s) "
            "OPTIONAL MATCH (owner)-[:MEMBER_OF]->(rg:ResearchGroup) "
            "WITH s, owner, collect(DISTINCT rg) AS rgs "
            "OPTIONAL MATCH (s)-[st:IN_STATE]->(state:State) "
            "WITH s, owner, rgs, state ORDER BY st.created_at DESC "
            "WITH s, owner, rgs, head(collect(state)) AS latest_state "
            "WITH s, owner, rgs, latest_state LIMIT $limit "
            "OPTIONAL MATCH (s)<-[:FOR_SUBMISSION]-(cr:CollaborationRequest {status : 'pending'}) "
            "WITH s, owner, rgs, latest_state, count(cr) > 0 AS has_open_request "
            "WITH s, owner, rgs, latest_state, has_open_request, "
            "[ca_tag IN $ca_tags WHERE EXISTS { MATCH (s)-[:HAS_APPLICATION]->(:ConditionApplication {tag : ca_tag}) } "
            "OR EXISTS { MATCH (s)-[:HAS_SAMPLE]->(:Sample)-[:HAS_APPLICATION]->(:ConditionApplication {tag : ca_tag}) }] AS matched_ca_tags, "
            "[user_tag IN $user_tags WHERE EXISTS { MATCH (:User {tag : user_tag})-[:CREATED|COLLABORATES]->(s) }] AS matched_user_tags "
            "RETURN s.tag AS tag, s.title AS title, s.created_at AS created_at, "
            "owner.tag AS owner_tag, owner.firstname AS owner_firstname, owner.lastname AS owner_lastname, "
            "owner.institute AS owner_institute, "
            "[rg IN rgs WHERE rg IS NOT NULL | rg.tag][0] AS research_group_tag, "
            "[rg IN rgs WHERE rg IS NOT NULL | rg.text][0] AS research_group_text, "
            "[rg IN rgs WHERE rg IS NOT NULL | rg.institute][0] AS research_group_institute, "
            "latest_state.tag AS state_tag, has_open_request AS has_open_collaboration_request, "
            "matched_ca_tags, matched_user_tags "
        )
        rows = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, **params)
        results : List[SubmissionExploreModel] = []
        for row in rows:
            state_tag = row.get("state_tag")
            try:
                state_int = int(state_tag) if state_tag is not None else None
            except (TypeError, ValueError):
                state_int = None
            results.append(SubmissionExploreModel(
                tag = row["tag"],
                title = row["title"],
                state = state_int,
                created_at = row.get("created_at"),
                owner_tag = row.get("owner_tag"),
                owner_firstname = row.get("owner_firstname"),
                owner_lastname = row.get("owner_lastname"),
                owner_institute = row.get("owner_institute"),
                research_group_tag = row.get("research_group_tag"),
                research_group_text = row.get("research_group_text"),
                research_group_institute = row.get("research_group_institute"),
                has_open_collaboration_request = bool(row.get("has_open_collaboration_request")),
                matched_condition_application_tags = row.get("matched_ca_tags") or None,
                matched_user_tags = row.get("matched_user_tags") or None,
            ))
        return results
