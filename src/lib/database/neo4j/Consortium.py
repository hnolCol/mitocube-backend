from typing import List, Dict
from neo4j import Driver, Result

from lib.database.abstract.Consortium import ConsortiumABC
from lib.cache.scope_cache import invalidate_all_cached_scopes
from config.models.consortium import ConsortiumInput, ConsortiumModel


class Neo4JConsortium(ConsortiumABC):

    def __init__(self, driver : Driver) -> None:
        self._driver = driver

    def exists(self, tag : str) -> bool:
        query = (
            "WITH EXISTS {(c:Consortium {tag : $tag})} as consortium_exists "
            "RETURN consortium_exists "
        )
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]

    def insert(self, tag : str, consortium : ConsortiumInput) -> bool:
        """Creates or updates a consortium. The tag is expected to be a unique hash of the content."""
        query = (
            "MERGE (c:Consortium {tag : $tag}) "
            "ON CREATE "
            "SET c.created_at = timestamp(), c.text = $consortium.text, c.abbreviation = $consortium.abbreviation, "
            "c.email = $consortium.email, c.profile_text = $consortium.profile_text, c.url = $consortium.url "
            "ON MATCH "
            "SET c.modified_at = timestamp(), c.text = $consortium.text, c.abbreviation = $consortium.abbreviation, "
            "c.email = $consortium.email, c.profile_text = $consortium.profile_text, c.url = $consortium.url "
            "RETURN c.tag"
        )
        r = self._driver.execute_query(query, routing_="w", tag = tag,
                                       consortium = consortium.model_dump(exclude_none=True),
                                       result_transformer_=Result.value)
        return True if len(r) > 0 else False

    def get(self, tag : str) -> ConsortiumModel:
        query = (
            "MATCH (c:Consortium) "
            "WHERE c.tag = $tag "
            "RETURN properties(c) "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag)
        return ConsortiumModel(**r[0]) if len(r) > 0 else None

    def count(self) -> int:
        """Returns the number of consortiums"""
        query = (
            "MATCH (c:Consortium) "
            "RETURN count(c) "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return r[0] if len(r) > 0 else 0

    def delete(self, tag : str) -> bool:
        """Deletes a consortium together with its membership and sharing relations."""
        query = (
            "MATCH (c:Consortium {tag : $tag}) "
            "DETACH DELETE c "
            "RETURN count(c) "
        )
        r = self._driver.execute_query(query, routing_="w", tag = tag, result_transformer_=Result.value)
        return r[0] > 0

    def find(self, search_string : str = None, group_tags : List[str] = None, user_tags : List[str] = None, limit : int = 40) -> List[str]:
        """Finds consortium tags that match the search string, contain the given research groups (eligibility)
        or that the given users are direct members of."""
        if user_tags is not None:
            query = (
                "MATCH (c:Consortium)<-[:MEMBER_OF]-(u:User) "
                "WHERE u.tag IN $user_tags "
            )
            if group_tags is not None:
                query += "AND EXISTS { (c)<-[:MEMBER_OF]-(rg:ResearchGroup) WHERE rg.tag IN $group_tags } "
        elif group_tags is not None:
            query = (
                "MATCH (c:Consortium)<-[:MEMBER_OF]-(rg:ResearchGroup) "
                "WHERE rg.tag IN $group_tags "
            )
        else:
            query = (
                "MATCH (c:Consortium) "
                "WHERE true "
            )

        if search_string is not None and search_string != "":
            query += "AND (toLower(c.text) CONTAINS $search_string OR toLower(c.abbreviation) CONTAINS $search_string OR toLower(c.tag) CONTAINS $search_string) "

        query += "RETURN DISTINCT c.tag as tag "

        if limit is not None:
            query += "LIMIT $limit"

        r = self._driver.execute_query(
            query,
            routing_="r",
            result_transformer_=Result.value,
            search_string=search_string.lower() if search_string is not None else None,
            group_tags=group_tags,
            user_tags=user_tags,
            limit=limit
        )
        return r

    def get_tags(self, limit : int = 40) -> List[str]:
        """Returns the tags of all consortiums, ordered by creation date"""
        query = (
            "MATCH (c:Consortium) "
            "RETURN c.tag ORDER BY c.created_at DESC LIMIT $limit"
        )
        r = self._driver.execute_query(query, routing_="r", limit=limit, result_transformer_=Result.value)
        return r

    def get_groups(self, tag : str) -> List[str]:
        """Returns the research group tags that are members of the consortium"""
        query = (
            "MATCH (c:Consortium {tag : $tag})<-[r:MEMBER_OF]-(rg:ResearchGroup) "
            "RETURN collect(rg.tag) "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return r[0] if len(r) > 0 else []

    def get_user_tags(self, tag : str) -> List[str]:
        """Returns the user tags of all users that are direct members of the consortium"""
        query = (
            "MATCH (c:Consortium {tag : $tag})<-[:MEMBER_OF]-(u:User) "
            "RETURN DISTINCT u.tag ORDER BY u.tag "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return r

    def get_eligible_user_tags(self, tag : str) -> List[str]:
        """Returns the user tags of all users that are members of the consortiums eligible research groups"""
        query = (
            "MATCH (c:Consortium {tag : $tag})<-[:MEMBER_OF]-(rg:ResearchGroup)<-[:MEMBER_OF]-(u:User) "
            "RETURN DISTINCT u.tag ORDER BY u.tag "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return r

    def find_by_user(self, user_tag : str, limit : int = 40) -> List[str]:
        """Returns the tags of all consortiums the user is a direct member of"""
        query = (
            "MATCH (u:User {tag : $user_tag})-[:MEMBER_OF]->(c:Consortium) "
            "RETURN DISTINCT c.tag, c.created_at ORDER BY c.created_at DESC "
        )
        if limit is not None:
            query += "LIMIT $limit"
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag, limit = limit, result_transformer_=Result.values)
        return [tag for tag, _ in r]

    def find_by_user_with_terms(self, user_tag : str, limit : int = 40) -> List[str]:
        """Returns the tags of all consortiums the user is a direct member of and where the
        head (PI) of at least one of the users research groups agreed to the consortium terms.
        Consortiums without an agreement of the users groups are excluded: their submissions
        are neither visible nor shareable for the user."""
        query = (
            "MATCH (u:User {tag : $user_tag})-[:MEMBER_OF]->(c:Consortium) "
            "WHERE EXISTS { MATCH (u)-[:MEMBER_OF]->(rg:ResearchGroup)-[:CONSORTIUM_TERMS]->(c) } "
            "RETURN DISTINCT c.tag, c.created_at ORDER BY c.created_at DESC "
        )
        if limit is not None:
            query += "LIMIT $limit"
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag, limit = limit, result_transformer_=Result.values)
        return [tag for tag, _ in r]

    def get_terms_group_tags(self, consortium_tag : str) -> List[str]:
        """Returns the tags of the eligible research groups whose head (PI) agreed to the
        consortium terms"""
        query = (
            "MATCH (c:Consortium {tag : $consortium_tag})<-[t:CONSORTIUM_TERMS]-(rg:ResearchGroup) "
            "RETURN rg.tag ORDER BY rg.tag "
        )
        r = self._driver.execute_query(query, routing_="r", consortium_tag = consortium_tag, result_transformer_=Result.value)
        return r

    def agree_terms(self, consortium_tag : str, group_tag : str, user_tag : str) -> bool:
        """Records that the head (PI) of the research group agreed to the consortium terms.
        Only after this agreement the users of the group can share into and see the submissions
        of the consortium."""
        if not self.exists(consortium_tag): raise ValueError(f"Consortium with tag {consortium_tag} does not exist.")

        query = (
            "MATCH (c:Consortium {tag : $consortium_tag}), (rg:ResearchGroup {tag : $group_tag}) "
            "MERGE (rg)-[t:CONSORTIUM_TERMS]->(c) "
            "ON CREATE "
            "SET t.created_at = timestamp(), t.agreed_by = $user_tag "
            "ON MATCH "
            "SET t.modified_at = timestamp(), t.agreed_by = $user_tag "
            "RETURN count(t) "
        )
        r = self._driver.execute_query(query, routing_="w", consortium_tag = consortium_tag,
                                       group_tag = group_tag, user_tag = user_tag, result_transformer_=Result.value)
        invalidate_all_cached_scopes()  # the agreement affects the scope of all group users
        return r[0] > 0

    def revoke_terms(self, consortium_tag : str, group_tag : str) -> bool:
        """Revokes the research groups agreement to the consortium terms. The users of the
        group can then neither share into nor see the submissions of the consortium."""
        query = (
            "MATCH (rg:ResearchGroup {tag : $group_tag})-[t:CONSORTIUM_TERMS]->(c:Consortium {tag : $consortium_tag}) "
            "DELETE t "
            "RETURN count(t) "
        )
        r = self._driver.execute_query(query, routing_="w", consortium_tag = consortium_tag,
                                       group_tag = group_tag, result_transformer_=Result.value)
        invalidate_all_cached_scopes()  # the revocation affects the scope of all group users
        return r[0] > 0

    def user_has_terms(self, consortium_tag : str, user_tag : str) -> bool:
        """Checks if the head (PI) of at least one of the users research groups agreed to the
        consortium terms"""
        query = (
            "MATCH (u:User {tag : $user_tag}), (c:Consortium {tag : $consortium_tag}) "
            "RETURN EXISTS { MATCH (u)-[:MEMBER_OF]->(rg:ResearchGroup)-[:CONSORTIUM_TERMS]->(c) } "
        )
        r = self._driver.execute_query(query, routing_="r", consortium_tag = consortium_tag,
                                       user_tag = user_tag, result_transformer_=Result.value)
        return bool(r[0]) if len(r) > 0 else False

    def find_pending_terms_for_head(self, user_tag : str) -> List[Dict]:
        """Returns the consortiums where the given user leads (as head/PI) an eligible research
        group that has not yet agreed to the consortium terms"""
        query = (
            "MATCH (pi:User {tag : $user_tag})-[:HEAD_OF]->(rg:ResearchGroup)-[:MEMBER_OF]->(c:Consortium) "
            "WHERE NOT EXISTS { (rg)-[:CONSORTIUM_TERMS]->(c) } "
            "RETURN rg.tag AS group_tag, c.tag AS consortium_tag ORDER BY c.created_at DESC "
        )
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag, result_transformer_=Result.data)
        return list(r) if r else []

    def find_consortiums_with_pending_terms_for_user(self, user_tag : str) -> List[str]:
        """Returns the tags of the consortiums the user is a direct member of where the head (PI)
        of none of the users research groups agreed to the terms yet"""
        query = (
            "MATCH (u:User {tag : $user_tag})-[:MEMBER_OF]->(c:Consortium) "
            "WHERE NOT EXISTS { MATCH (u)-[:MEMBER_OF]->(rg:ResearchGroup)-[:CONSORTIUM_TERMS]->(c) } "
            "RETURN DISTINCT c.tag ORDER BY c.tag "
        )
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag, result_transformer_=Result.value)
        return r

    def insert_groups(self, tag : str, group_tags : List[str], user_tag : str = None):
        """Adds research groups to the consortium as eligible groups. The heads (PIs) of the groups
        automatically become direct members of the consortium."""
        if not self.exists(tag): raise ValueError(f"Consortium with tag {tag} does not exist.")

        query = (
            "MATCH (c:Consortium {tag : $tag}) "
            "UNWIND $group_tags as group_tag "
            "MATCH (rg:ResearchGroup {tag : group_tag}) "
            "MERGE (c)<-[r:MEMBER_OF]-(rg) "
            "ON CREATE "
            "SET r.created_at = timestamp() "
            "WITH DISTINCT c, rg "
            "MATCH (head:User)-[:HEAD_OF]->(rg) "
            "MERGE (head)-[m:MEMBER_OF]->(c) "
            "ON CREATE "
            "SET m.created_at = timestamp(), m.origin = 'head', m.added_by = $user_tag "
        )
        self._driver.execute_query(query, routing_="w", tag = tag, group_tags = group_tags, user_tag = user_tag)
        invalidate_all_cached_scopes()  # memberships affect the scope of all consortium members

    def remove_groups(self, tag : str, group_tags : List[str]):
        """Removes research groups from the consortium. Fails if a non-head member of such a group
        has no other eligible group in the consortium. Head memberships of the removed groups are
        cleaned up unless the head still heads another eligible group."""
        if not self.exists(tag): raise ValueError(f"Consortium with tag {tag} does not exist.")

        for group_tag in group_tags:
            blocking_query = (
                "MATCH (rg:ResearchGroup {tag : $group_tag})-[:MEMBER_OF]->(c:Consortium {tag : $tag}) "
                "MATCH (d:User)-[:MEMBER_OF]->(rg) "
                "MATCH (d)-[dm:MEMBER_OF]->(c) "
                "WHERE NOT EXISTS { (d)-[:HEAD_OF]->(rg) } "
                "  AND NOT EXISTS { MATCH (d)-[:MEMBER_OF]->(other:ResearchGroup)-[:MEMBER_OF]->(c) WHERE other.tag <> $group_tag } "
                "RETURN DISTINCT d.tag"
            )
            blocking = self._driver.execute_query(blocking_query, routing_="r", tag = tag,
                                                  group_tag = group_tag, result_transformer_=Result.value)
            if blocking:
                raise ValueError(f"Research group {group_tag} cannot be removed from the consortium "
                                 f"while these members have no other eligible group: {', '.join(blocking)}")

            query = (
                "MATCH (rg:ResearchGroup {tag : $group_tag})-[r:MEMBER_OF]->(c:Consortium {tag : $tag}) "
                "DELETE r "
                "WITH c, rg "
                "MATCH (rg)-[t:CONSORTIUM_TERMS]->(c) "
                "DELETE t "
                "WITH c "
                "MATCH (h:User)-[m:MEMBER_OF]->(c) "
                "WHERE m.origin = 'head' "
                "  AND NOT EXISTS { MATCH (h)-[:HEAD_OF]->(:ResearchGroup)-[:MEMBER_OF]->(c) } "
                "DELETE m"
            )
            self._driver.execute_query(query, routing_="w", tag = tag, group_tag = group_tag)
        invalidate_all_cached_scopes()  # memberships affect the scope of all consortium members

    def _is_eligible_member(self, consortium_tag : str, user_tag : str) -> bool:
        """Checks if the user is a member of an eligible research group of the consortium
        whose head (PI) is a member of the consortium"""
        query = (
            "MATCH (u:User {tag : $user_tag}), (c:Consortium {tag : $consortium_tag}) "
            "RETURN EXISTS { "
            "  MATCH (u)-[:MEMBER_OF]->(rg:ResearchGroup)-[:MEMBER_OF]->(c) "
            "  MATCH (h:User)-[:HEAD_OF]->(rg) "
            "  MATCH (h)-[:MEMBER_OF]->(c) "
            "  RETURN true "
            "} "
        )
        r = self._driver.execute_query(query, routing_="r", consortium_tag = consortium_tag,
                                       user_tag = user_tag, result_transformer_=Result.value)
        return bool(r[0]) if len(r) > 0 else False

    def insert_users(self, tag : str, user_tags : List[str], user_tag : str = None):
        """Adds users as direct members of the consortium. A user can only be added if they are a
        member of an eligible research group whose head (PI) is a member of the consortium."""
        if not self.exists(tag): raise ValueError(f"Consortium with tag {tag} does not exist.")

        for member_tag in user_tags:
            if not self._is_eligible_member(consortium_tag = tag, user_tag = member_tag):
                raise ValueError(f"User {member_tag} cannot be added to the consortium: "
                                 f"they are not a member of an eligible research group whose head (PI) is in the consortium.")

        query = (
            "MATCH (c:Consortium {tag : $tag}) "
            "UNWIND $user_tags as member_tag "
            "MATCH (u:User {tag : member_tag}) "
            "MERGE (u)-[m:MEMBER_OF]->(c) "
            "ON CREATE "
            "SET m.created_at = timestamp(), m.origin = 'manual', m.added_by = $user_tag "
        )
        self._driver.execute_query(query, routing_="w", tag = tag, user_tags = user_tags, user_tag = user_tag)
        invalidate_all_cached_scopes()  # memberships affect the scope of all consortium members

    def remove_users(self, tag : str, user_tags : List[str]):
        """Removes direct user memberships from the consortium. Fails if a head (PI) is removed
        while other members depend on them (all their eligible groups are headed by that PI)."""
        if not self.exists(tag): raise ValueError(f"Consortium with tag {tag} does not exist.")

        for member_tag in user_tags:
            blocking_query = (
                "MATCH (h:User {tag : $member_tag})-[hm:MEMBER_OF]->(c:Consortium {tag : $tag}) "
                "MATCH (d:User)-[dm:MEMBER_OF]->(c) "
                "WHERE d.tag <> h.tag "
                "  AND EXISTS { MATCH (d)-[:MEMBER_OF]->(rg:ResearchGroup)-[:MEMBER_OF]->(c) MATCH (h)-[:HEAD_OF]->(rg) } "
                "  AND NOT EXISTS { MATCH (d)-[:MEMBER_OF]->(rg2:ResearchGroup)-[:MEMBER_OF]->(c) WHERE NOT EXISTS { (h)-[:HEAD_OF]->(rg2) } } "
                "RETURN DISTINCT d.tag"
            )
            blocking = self._driver.execute_query(blocking_query, routing_="r", tag = tag,
                                                  member_tag = member_tag, result_transformer_=Result.value)
            if blocking:
                raise ValueError(f"User {member_tag} cannot be removed from the consortium "
                                 f"while these members depend on them as head (PI): {', '.join(blocking)}")

        query = (
            "MATCH (c:Consortium {tag : $tag}) "
            "UNWIND $user_tags as member_tag "
            "MATCH (u:User {tag : member_tag})-[m:MEMBER_OF]->(c) "
            "DELETE m"
        )
        self._driver.execute_query(query, routing_="w", tag = tag, user_tags = user_tags)
        invalidate_all_cached_scopes()  # memberships affect the scope of all consortium members

    def is_head_of_user_in_consortium(self, head_tag : str, user_tag : str, consortium_tag : str) -> bool:
        """Checks if the user is a head (PI) of a research group the given user is a member of
        and that is an eligible group of the consortium"""
        query = (
            "MATCH (h:User {tag : $head_tag}), (u:User {tag : $user_tag}), (c:Consortium {tag : $consortium_tag}) "
            "RETURN EXISTS { "
            "  MATCH (h)-[:HEAD_OF]->(rg:ResearchGroup)<-[:MEMBER_OF]-(u) "
            "  MATCH (rg)-[:MEMBER_OF]->(c) "
            "  RETURN true "
            "} "
        )
        r = self._driver.execute_query(query, routing_="r", head_tag = head_tag, user_tag = user_tag,
                                       consortium_tag = consortium_tag, result_transformer_=Result.value)
        return bool(r[0]) if len(r) > 0 else False

    def insert_membership_request(self, consortium_tag : str, user_tag : str, kind : str, requested_by : str) -> bool:
        """Creates (or refreshes) a pending membership request of kind 'add' or 'remove' for the user."""
        if not self.exists(consortium_tag): raise ValueError(f"Consortium with tag {consortium_tag} does not exist.")
        if kind not in ("add", "remove"): raise ValueError(f"Invalid membership request kind {kind}.")

        query = (
            "MATCH (c:Consortium {tag : $consortium_tag}), (u:User {tag : $user_tag}) "
            "MERGE (u)-[r:MEMBERSHIP_REQUEST]->(c) "
            "ON CREATE "
            "SET r.created_at = timestamp(), r.status = 'pending', r.kind = $kind, r.requested_by = $requested_by "
            "ON MATCH "
            "SET r.modified_at = timestamp(), r.status = 'pending', r.kind = $kind, r.requested_by = $requested_by "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w", consortium_tag = consortium_tag, user_tag = user_tag,
                                       kind = kind, requested_by = requested_by, result_transformer_=Result.value)
        return r[0] > 0

    def get_pending_membership_requests(self, consortium_tag : str = None) -> List[Dict]:
        """Returns all pending membership requests, optionally restricted to one consortium"""
        query = (
            "MATCH (u:User)-[r:MEMBERSHIP_REQUEST]->(c:Consortium) "
            "WHERE r.status = 'pending' "
        )
        if consortium_tag is not None:
            query += "AND c.tag = $consortium_tag "
        query += "RETURN u.tag AS user_tag, c.tag AS consortium_tag, r.kind AS kind, "
        query += "r.requested_by AS requested_by, r.created_at AS created_at ORDER BY r.created_at DESC "
        r = self._driver.execute_query(query, routing_="r", consortium_tag = consortium_tag, result_transformer_=Result.data)
        return list(r) if r else []

    def get_pending_membership_requests_for_head(self, user_tag : str) -> List[Dict]:
        """Returns the pending membership requests that concern users of the research groups
        the given user leads (as head/PI) or that the user filed themselves"""
        query = (
            "MATCH (pi:User {tag : $user_tag}) "
            "OPTIONAL MATCH (pi)-[:HEAD_OF]->(rg:ResearchGroup)<-[:MEMBER_OF]-(member:User) "
            "WITH pi, collect(DISTINCT member.tag) AS group_member_tags "
            "WITH pi, group_member_tags + [pi.tag] AS relevant_tags "
            "MATCH (u:User)-[r:MEMBERSHIP_REQUEST]->(c:Consortium) "
            "WHERE r.status = 'pending' AND (u.tag IN relevant_tags OR r.requested_by = pi.tag) "
            "RETURN u.tag AS user_tag, c.tag AS consortium_tag, r.kind AS kind, "
            "r.requested_by AS requested_by, r.created_at AS created_at ORDER BY r.created_at DESC "
        )
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag, result_transformer_=Result.data)
        return list(r) if r else []

    def approve_membership_request(self, consortium_tag : str, user_tag : str, decided_by : str) -> bool:
        """Approves a pending membership request. An 'add' request adds the user as a direct member
        (if still eligible), a 'remove' request removes their membership."""
        kind = self._get_pending_membership_request_kind(consortium_tag = consortium_tag, user_tag = user_tag)
        if kind is None: return False

        if kind == "add":
            if not self._is_eligible_member(consortium_tag = consortium_tag, user_tag = user_tag):
                raise ValueError(f"User {user_tag} is not eligible for the consortium anymore.")
            query = (
                "MATCH (c:Consortium {tag : $consortium_tag}), (u:User {tag : $user_tag}) "
                "MERGE (u)-[m:MEMBER_OF]->(c) "
                "ON CREATE "
                "SET m.created_at = timestamp(), m.origin = 'manual', m.added_by = $decided_by "
            )
        else:
            query = (
                "MATCH (u:User {tag : $user_tag})-[m:MEMBER_OF]->(c:Consortium {tag : $consortium_tag}) "
                "DELETE m "
            )
        query += (
            "WITH 1 as dummy "
            "MATCH (u2:User {tag : $user_tag})-[r:MEMBERSHIP_REQUEST]->(c2:Consortium {tag : $consortium_tag}) "
            "WHERE r.status = 'pending' "
            "DELETE r "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w", consortium_tag = consortium_tag, user_tag = user_tag,
                                       decided_by = decided_by, result_transformer_=Result.value)
        invalidate_all_cached_scopes()  # memberships affect the scope of all consortium members
        return r[0] > 0

    def deny_membership_request(self, consortium_tag : str, user_tag : str) -> bool:
        """Denies a pending membership request, removing the pending relation"""
        query = (
            "MATCH (u:User {tag : $user_tag})-[r:MEMBERSHIP_REQUEST]->(c:Consortium {tag : $consortium_tag}) "
            "WHERE r.status = 'pending' "
            "DELETE r "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w", consortium_tag = consortium_tag, user_tag = user_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0

    def _get_pending_membership_request_kind(self, consortium_tag : str, user_tag : str):
        """Returns the kind of the pending membership request, or None if there is none"""
        query = (
            "MATCH (u:User {tag : $user_tag})-[r:MEMBERSHIP_REQUEST]->(c:Consortium {tag : $consortium_tag}) "
            "WHERE r.status = 'pending' "
            "RETURN r.kind "
        )
        r = self._driver.execute_query(query, routing_="r", consortium_tag = consortium_tag, user_tag = user_tag,
                                       result_transformer_=Result.value)
        return r[0] if len(r) > 0 else None

    def get_submission_tags(self, tag : str) -> List[str]:
        """Returns the submission tags that are shared with the consortium"""
        query = (
            "MATCH (c:Consortium {tag : $tag})<-[r:SHARED_WITH]-(s:Submission) "
            "WHERE r.status = 'approved' "
            "RETURN s.tag ORDER BY s.created_at DESC "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return r

    def share_submission(self, consortium_tag : str, submission_tag : str, user_tag : str, approved : bool = False) -> bool:
        """Shares a submission with the consortium. If approved is False, the share request is
        created with status pending and requires the approval of a research group head (PI)."""
        if not self.exists(consortium_tag): raise ValueError(f"Consortium with tag {consortium_tag} does not exist.")

        status = "approved" if approved else "pending"
        query = (
            "MATCH (c:Consortium {tag : $consortium_tag}), (s:Submission {tag : $submission_tag}) "
            "MERGE (s)-[r:SHARED_WITH]->(c) "
            "ON CREATE "
            "SET r.created_at = timestamp(), r.status = $status, r.requested_by = $user_tag "
            "ON MATCH "
            "SET r.modified_at = timestamp() "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       consortium_tag = consortium_tag,
                                       submission_tag = submission_tag,
                                       status = status,
                                       user_tag = user_tag,
                                       result_transformer_=Result.value)
        invalidate_all_cached_scopes()  # shares affect the scope of all consortium member group users
        return r[0] > 0

    def get_pending_share_requests_for_head(self, user_tag : str) -> List[Dict]:
        """Returns the pending share requests that the given research group head (PI) can approve.
        A head sees the requests of the users that are members of the research groups they lead."""
        query = (
            "MATCH (pi:User {tag : $user_tag})-[:HEAD_OF]->(rg:ResearchGroup)<-[:MEMBER_OF]-(owner:User) "
            "MATCH (owner)-[:CREATED]->(s:Submission)-[r:SHARED_WITH]->(c:Consortium) "
            "WHERE r.status = 'pending' "
            "RETURN s.tag AS submission_tag, c.tag AS consortium_tag, r.requested_by AS requested_by, r.created_at AS created_at "
            "ORDER BY r.created_at DESC "
        )
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag, result_transformer_=Result.data)
        return list(r) if r else []

    def approve_share_request(self, consortium_tag : str, submission_tag : str, user_tag : str) -> bool:
        """Approves a pending share request, making the submission accessible to the consortium"""
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:SHARED_WITH]->(c:Consortium {tag : $consortium_tag}) "
            "WHERE r.status = 'pending' "
            "SET r.status = 'approved', r.approved_by = $user_tag, r.approved_at = timestamp() "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       consortium_tag = consortium_tag,
                                       submission_tag = submission_tag,
                                       user_tag = user_tag,
                                       result_transformer_=Result.value)
        invalidate_all_cached_scopes()  # shares affect the scope of all consortium member group users
        return r[0] > 0

    def is_head_of_submission_owner(self, user_tag : str, submission_tag : str) -> bool:
        """Checks if the user is a head (PI) of a research group the owner (creator) of the
        submission is a member of"""
        query = (
            "MATCH (owner:User)-[:CREATED]->(s:Submission {tag : $submission_tag}) "
            "RETURN EXISTS {(pi:User {tag : $user_tag})-[:HEAD_OF]->(:ResearchGroup)<-[:MEMBER_OF]-(owner)} "
        )
        r = self._driver.execute_query(query, routing_="r",
                                       user_tag = user_tag,
                                       submission_tag = submission_tag,
                                       result_transformer_=Result.value)
        return bool(r[0]) if len(r) > 0 else False

    def deny_share_request(self, consortium_tag : str, submission_tag : str) -> bool:
        """Denies a pending share request, removing the pending relation"""
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:SHARED_WITH]->(c:Consortium {tag : $consortium_tag}) "
            "WHERE r.status = 'pending' "
            "DELETE r "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       consortium_tag = consortium_tag,
                                       submission_tag = submission_tag,
                                       result_transformer_=Result.value)
        invalidate_all_cached_scopes()  # shares affect the scope of all consortium member group users
        return r[0] > 0

    def unshare_submission(self, consortium_tag : str, submission_tag : str) -> bool:
        """Removes a submission from the consortium"""
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:SHARED_WITH]->(c:Consortium {tag : $consortium_tag}) "
            "DELETE r "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       consortium_tag = consortium_tag,
                                       submission_tag = submission_tag,
                                       result_transformer_=Result.value)
        invalidate_all_cached_scopes()  # shares affect the scope of all consortium member group users
        return r[0] > 0

    def get_pending_consortium_tags(self, submission_tag : str) -> List[str]:
        """Returns the tags of consortiums with a pending share request for the submission"""
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:SHARED_WITH]->(c:Consortium) "
            "WHERE r.status = 'pending' "
            "RETURN c.tag "
        )
        return self._driver.execute_query(query, routing_="r", submission_tag = submission_tag, result_transformer_=Result.value)