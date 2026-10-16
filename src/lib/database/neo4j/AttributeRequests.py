from typing import List, Optional, Literal

from neo4j import Driver, Result

from lib.database.abstract.AttributeRequests import AttributeRequestsABC
from config.models.requests import AttributeRequestModel, AttributeRequestInsertModel
from config.models.attributes import InsertTraitModel


class Neo4JAttributeRequests(AttributeRequestsABC):
    """Stores attribute/trait requests as AttributeRequest nodes.

    The proposal payload is stored as a JSON string on the node, so no
    Attribute/Trait nodes are created before approval. On accept, the
    proposal is materialized through the regular attribute insert paths.
    """

    def __init__(self, driver: Driver, attributes) -> None:
        self._driver = driver
        self.attributes = attributes

    def _attribute_tag(self, text: str) -> str:
        return "att_" + text.replace(" ", "_").lower().encode("utf-8", "ignore").decode("utf-8")

    def insert(self, request: AttributeRequestInsertModel, user_tag: str) -> str:
        tag = AttributeRequestModel(
            kind=request.kind,
            user_tag=user_tag,
            comment=request.comment,
            attribute=request.attribute,
            trait=request.trait,
        ).tag
        query = (
            "MERGE (r:AttributeRequest {tag: $tag}) "
            "ON CREATE SET r.created_at = timestamp(), r.status = 'pending' "
            "SET r.kind = $kind, r.user_tag = $user_tag, "
            "r.comment = $comment, r.attribute = $attribute, r.trait = $trait "
            "RETURN r.tag"
        )
        self._driver.execute_query(
            query,
            routing_="w",
            tag=tag,
            kind=request.kind,
            user_tag=user_tag,
            comment=request.comment,
            attribute=request.attribute.model_dump() if request.attribute is not None else None,
            trait=request.trait.model_dump() if request.trait is not None else None,
            result_transformer_=Result.value,
        )
        return tag

    def exists(self, tag: str) -> bool:
        query = "RETURN EXISTS { (r:AttributeRequest {tag: $tag}) }"
        r = self._driver.execute_query(query, tag=tag, result_transformer_=Result.value)
        return r[0]

    def _to_model(self, row: dict) -> AttributeRequestModel:
        return AttributeRequestModel(
            tag=row["tag"],
            kind=row["kind"],
            status=row["status"],
            user_tag=row["user_tag"],
            comment=row["comment"],
            created_at=row["created_at"],
            attribute=row["attribute"],
            trait=row["trait"],
        )

    def get(self, tags: List[str] = None, status: Literal["pending", "accepted", "rejected"] = None, limit: int = 50) -> List[AttributeRequestModel]:
        query = "MATCH (r:AttributeRequest) "
        params = {"limit": limit}
        if status is not None:
            query += "WHERE r.status = $status "
            params["status"] = status
        if tags is not None:
            query += ("AND " if status is not None else "WHERE ") + "r.tag IN $tags "
            params["tags"] = tags
        query += (
            "RETURN r.tag as tag, r.kind as kind, r.status as status, r.user_tag as user_tag, "
            "r.comment as comment, r.created_at as created_at, r.attribute as attribute, r.trait as trait "
            "ORDER BY r.created_at DESC LIMIT $limit"
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, **params)
        return [self._to_model(row) for row in r]

    def get_pending(self, limit: int = 50) -> List[AttributeRequestModel]:
        return self.get(status="pending", limit=limit)

    def _get_node(self, tag: str) -> dict:
        query = (
            "MATCH (r:AttributeRequest {tag: $tag}) "
            "RETURN r.tag as tag, r.kind as kind, r.status as status, r.user_tag as user_tag, "
            "r.comment as comment, r.created_at as created_at, r.attribute as attribute, r.trait as trait"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.data)
        if not r:
            raise ValueError(f"Attribute request with tag '{tag}' not found.")
        return r[0]

    def accept(self, tag: str, reviewer_tag: str, comment: Optional[str] = None) -> AttributeRequestModel:
        row = self._get_node(tag)
        if row["status"] != "pending":
            raise ValueError(f"Attribute request with tag '{tag}' is not pending.")
        if row["kind"] == "attribute":
            proposal = row["attribute"]
            attribute_tag = self._attribute_tag(proposal["text"])
            if self.attributes.exists(tag=attribute_tag):
                raise ValueError(f"An attribute with the tag '{attribute_tag}' exists already.")
            ok = self.attributes.insert(
                tag=attribute_tag,
                text=proposal["text"],
                priority=proposal.get("priority", 500),
                abbreviation=proposal.get("abbr"),
                group_tags=proposal.get("group_tags", []),
            )
            if not ok:
                raise ValueError("Failed to insert the proposed attribute.")
            for t in proposal.get("traits", []):
                trait = InsertTraitModel(
                    attribute_tag=attribute_tag,
                    value=t["text"].replace(" ", "_").lower().encode("utf-8", "ignore").decode("utf-8"),
                    text=t["text"],
                    description=t.get("description", ""),
                    priority=t.get("priority", 500),
                )
                self.attributes.insert_trait(trait)
        else:
            proposal = row["trait"]
            if not self.attributes.exists(tag=proposal["attribute_tag"]):
                raise ValueError(f"Attribute '{proposal['attribute_tag']}' not found.")
            trait = InsertTraitModel(
                attribute_tag=proposal["attribute_tag"],
                value=proposal["text"].replace(" ", "_").lower().encode("utf-8", "ignore").decode("utf-8"),
                text=proposal["text"],
                description=proposal.get("description", ""),
                priority=proposal.get("priority", 500),
            )
            if self.attributes.exists(tag=proposal["attribute_tag"], trait=trait.tag):
                raise ValueError(f"A trait with the tag '{trait.tag}' exists already for this attribute.")
            self.attributes.insert_trait(trait)
        query = (
            "MATCH (r:AttributeRequest {tag: $tag}) "
            "SET r.status = 'accepted', r.reviewer_tag = $reviewer_tag, "
            "r.reviewed_at = timestamp(), r.review_comment = $comment "
            "RETURN r.tag"
        )
        self._driver.execute_query(query, routing_="w", tag=tag, reviewer_tag=reviewer_tag, comment=comment)
        row["status"] = "accepted"
        return self._to_model(row)

    def reject(self, tag: str, reviewer_tag: str, comment: Optional[str] = None) -> AttributeRequestModel:
        row = self._get_node(tag)
        if row["status"] != "pending":
            raise ValueError(f"Attribute request with tag '{tag}' is not pending.")
        query = (
            "MATCH (r:AttributeRequest {tag: $tag}) "
            "SET r.status = 'rejected', r.reviewer_tag = $reviewer_tag, "
            "r.reviewed_at = timestamp(), r.review_comment = $comment "
            "RETURN r.tag"
        )
        self._driver.execute_query(query, routing_="w", tag=tag, reviewer_tag=reviewer_tag, comment=comment)
        row["status"] = "rejected"
        return self._to_model(row)
