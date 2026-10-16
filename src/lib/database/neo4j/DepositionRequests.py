from typing import List, Literal, Optional

from neo4j import Driver, Result

from lib.database.abstract.DepositionRequests import DepositionRequestsABC
from config.models.requests import DepositionRequestModel, DepositionRequestInsertModel


class Neo4JDepositionRequests(DepositionRequestsABC):
    """Stores deposition requests as DepositionRequest nodes.

    The accession identifier, url and optional login token are stored as
    properties on the node when a curator completes the request. The
    node is linked to the submission and the requesting user.
    """

    def __init__(self, driver: Driver, submissions) -> None:
        self._driver = driver
        self.submissions = submissions

    def _submission_exists(self, submission_tag: str) -> bool:
        return self.submissions.exists(tag=submission_tag) if self.submissions is not None else False

    def insert(self, request: DepositionRequestInsertModel, user_tag: str) -> str:
        if not self._submission_exists(request.submission_tag):
            raise ValueError(f"Submission with tag '{request.submission_tag}' does not exist.")
        if self.get(submission_tag=request.submission_tag, status="pending", limit=1):
            raise ValueError("A pending deposition request for this submission exists already.")
        model = DepositionRequestModel(
            submission_tag=request.submission_tag,
            user_tag=user_tag,
            comment=request.comment,
        )
        query = (
            "MERGE (r:DepositionRequest {tag: $tag}) "
            "ON CREATE SET r.created_at = timestamp(), r.status = 'pending' "
            "SET r.submission_tag = $submission_tag, r.user_tag = $user_tag, "
            "r.comment = $comment, r.database = $database "
            "WITH r "
            "MERGE (s:Submission {tag: $submission_tag}) "
            "MERGE (r)-[:FOR_SUBMISSION]->(s) "
            "RETURN r.tag"
        )
        self._driver.execute_query(
            query,
            routing_="w",
            tag=model.tag,
            submission_tag=request.submission_tag,
            user_tag=user_tag,
            comment=request.comment,
            database=request.database,
            result_transformer_=Result.value,
        )
        return model.tag

    def exists(self, tag: str) -> bool:
        query = "RETURN EXISTS { (r:DepositionRequest {tag: $tag}) }"
        r = self._driver.execute_query(query, tag=tag, result_transformer_=Result.value)
        return r[0]

    _RETURN = ("r.tag as tag, r.submission_tag as submission_tag, r.status as status, "
               "r.user_tag as user_tag, r.comment as comment, r.created_at as created_at, "
               "r.database as database, r.identifier as identifier, r.url as url, "
               "r.token as token, r.reviewer_tag as reviewer_tag, r.reviewed_at as reviewed_at, "
               "r.review_comment as review_comment")

    def _to_model(self, row: dict) -> DepositionRequestModel:
        return DepositionRequestModel(
            tag=row["tag"],
            submission_tag=row["submission_tag"],
            status=row["status"],
            user_tag=row["user_tag"],
            comment=row["comment"],
            created_at=row["created_at"],
            database=row["database"],
            identifier=row["identifier"],
            url=row["url"],
            token=row["token"],
            reviewer_tag=row["reviewer_tag"],
            reviewed_at=row["reviewed_at"],
            review_comment=row["review_comment"],
        )

    def get(self, tags: List[str] = None,
            status: Literal["pending", "deposited", "rejected"] = None,
            submission_tag: str = None,
            user_tag: str = None,
            limit: int = 50) -> List[DepositionRequestModel]:
        query = "MATCH (r:DepositionRequest) "
        params = {"limit": limit}
        where = []
        if status is not None:
            where.append("r.status = $status")
            params["status"] = status
        if tags is not None:
            where.append("r.tag IN $tags")
            params["tags"] = tags
        if submission_tag is not None:
            where.append("r.submission_tag = $submission_tag")
            params["submission_tag"] = submission_tag
        if user_tag is not None:
            where.append("r.user_tag = $user_tag")
            params["user_tag"] = user_tag
        if where:
            query += "WHERE " + " AND ".join(where) + " "
        query += (
            f"RETURN {self._RETURN} "
            "ORDER BY r.created_at DESC LIMIT $limit"
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, **params)
        return [self._to_model(row) for row in r]

    def get_pending(self, limit: int = 50) -> List[DepositionRequestModel]:
        return self.get(status="pending", limit=limit)

    def get_for_submission(self, submission_tag: str, limit: int = 10) -> List[DepositionRequestModel]:
        return self.get(submission_tag=submission_tag, limit=limit)

    def _get_node(self, tag: str) -> dict:
        query = f"MATCH (r:DepositionRequest {{tag: $tag}}) RETURN {self._RETURN}"
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.data)
        if not r:
            raise ValueError(f"Deposition request with tag '{tag}' not found.")
        return r[0]

    def complete(self, tag: str, reviewer_tag: str, identifier: str, url: str = None,
                 token: str = None, comment: str = None) -> DepositionRequestModel:
        row = self._get_node(tag)
        if row["status"] != "pending":
            raise ValueError(f"Deposition request with tag '{tag}' is not pending.")
        if identifier is None or len(identifier.strip()) == 0:
            raise ValueError("The deposition identifier is required.")
        query = (
            "MATCH (r:DepositionRequest {tag: $tag}) "
            "SET r.status = 'deposited', r.identifier = $identifier, r.url = $url, "
            "r.token = $token, r.reviewer_tag = $reviewer_tag, "
            "r.reviewed_at = timestamp(), r.review_comment = $comment "
            f"RETURN {self._RETURN}"
        )
        r = self._driver.execute_query(
            query,
            routing_="w",
            tag=tag,
            identifier=identifier,
            url=url,
            token=token,
            reviewer_tag=reviewer_tag,
            comment=comment,
            result_transformer_=Result.data,
        )
        return self._to_model(r[0])

    def reject(self, tag: str, reviewer_tag: str, comment: str = None) -> DepositionRequestModel:
        row = self._get_node(tag)
        if row["status"] != "pending":
            raise ValueError(f"Deposition request with tag '{tag}' is not pending.")
        query = (
            "MATCH (r:DepositionRequest {tag: $tag}) "
            "SET r.status = 'rejected', r.reviewer_tag = $reviewer_tag, "
            "r.reviewed_at = timestamp(), r.review_comment = $comment "
            f"RETURN {self._RETURN}"
        )
        r = self._driver.execute_query(
            query,
            routing_="w",
            tag=tag,
            reviewer_tag=reviewer_tag,
            comment=comment,
            result_transformer_=Result.data,
        )
        return self._to_model(r[0])
