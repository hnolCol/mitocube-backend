import json
from typing import List, Optional, Literal

from neo4j import Driver, Result

from lib.database.abstract.AttributeRequests import AttributeRequestsABC
from config.models.requests import AttributeRequestModel, AttributeRequestInsertModel
from config.models.attributes import InsertTraitModel


class Neo4JAttributeRequests(AttributeRequestsABC):
    """Stores attribute/trait requests as AttributeRequest nodes.

    The proposal payload is stored as a JSON string on the node (Neo4j cannot
    store maps as properties), so no Attribute/Trait nodes are created before
    approval. On accept, the (optionally curator-edited) proposal is
    materialized through the regular attribute insert paths and written back
    to the request.
    """

    _RETURN = (
        "RETURN r.tag as tag, r.kind as kind, r.status as status, r.user_tag as user_tag, "
        "r.comment as comment, r.created_at as created_at, r.attribute as attribute, r.trait as trait "
    )

    def __init__(self, driver: Driver, attributes) -> None:
        self._driver = driver
        self.attributes = attributes

    def _normalize(self, text: str) -> str:
        return text.replace(" ", "_").lower().encode("utf-8", "ignore").decode("utf-8")

    def _attribute_tag(self, text: str) -> str:
        return "att_" + self._normalize(text)

    def _check_attribute_tag_length(self, attribute_tag: str) -> None:
        if not 4 < len(attribute_tag) <= 35:
            raise ValueError("The attribute tag must be between 5 and 35 characters long.")

    def _trait_from_proposal(self, proposal: dict) -> InsertTraitModel:
        return InsertTraitModel(
            attribute_tag=proposal["attribute_tag"],
            value=self._normalize(proposal["text"]),
            text=proposal["text"],
            description=proposal.get("description") or "",
            priority=proposal.get("priority", 500),
        )

    def _parse_row(self, row: dict) -> dict:
        for key in ("attribute", "trait"):
            if isinstance(row.get(key), str):
                row[key] = json.loads(row[key])
        return row

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

    def _has_pending_request_for(self, target: str) -> bool:
        query = "RETURN EXISTS { (r:AttributeRequest {status: 'pending', target: $target}) }"
        r = self._driver.execute_query(query, target=target, result_transformer_=Result.value)
        return bool(r[0]) if len(r) > 0 else False

    def _get_node(self, tag: str) -> dict:
        query = "MATCH (r:AttributeRequest {tag: $tag}) " + self._RETURN
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.data)
        if not r:
            raise ValueError(f"Attribute request with tag '{tag}' not found.")
        return self._parse_row(r[0])

    def _set_status(self, tag: str, status: str, reviewer_tag: str, comment: Optional[str],
                    kind: Optional[Literal["attribute", "trait"]] = None, proposal: Optional[dict] = None) -> None:
        """Flips a pending request to accepted/rejected. Only matches pending
        requests, so a concurrent second review fails instead of overwriting.
        If a proposal is given, it replaces the stored one (curator edits)."""
        set_proposal = f"r.{kind} = $proposal, " if kind in ("attribute", "trait") and proposal is not None else ""
        query = (
            "MATCH (r:AttributeRequest {tag: $tag}) WHERE r.status = 'pending' "
            "SET " + set_proposal +
            "r.status = $status, r.reviewer_tag = $reviewer_tag, "
            "r.reviewed_at = timestamp(), r.review_comment = $comment "
            "RETURN r.tag"
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, status=status,
                                       reviewer_tag=reviewer_tag, comment=comment,
                                       proposal=json.dumps(proposal) if proposal is not None else None,
                                       result_transformer_=Result.value)
        if len(r) == 0:
            raise ValueError(f"Attribute request with tag '{tag}' is no longer pending.")

    def insert(self, request: AttributeRequestInsertModel, user_tag: str) -> str:
        if request.kind == "trait":
            trait = self._trait_from_proposal(request.trait.model_dump())
            if not self.attributes.exists(tag=trait.attribute_tag):
                raise ValueError(f"Attribute '{trait.attribute_tag}' not found.")
            if self.attributes.exists(tag=trait.attribute_tag, trait=trait.tag):
                raise ValueError(f"A trait with the tag '{trait.tag}' exists already for this attribute.")
            target = f"{trait.attribute_tag}:{trait.value}"
        else:
            target = self._attribute_tag(request.attribute.text)
            self._check_attribute_tag_length(target)
            if self.attributes.exists(tag=target):
                raise ValueError(f"An attribute with the tag '{target}' exists already.")

        if self._has_pending_request_for(target):
            raise ValueError("A pending request for this proposal exists already.")

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
            "SET r.kind = $kind, r.user_tag = $user_tag, r.comment = $comment, "
            "r.attribute = $attribute, r.trait = $trait, r.target = $target "
            "WITH r "
            "MATCH (u:User {tag: $user_tag}) "
            "MERGE (u)-[:REQUESTED]->(r) "
            "RETURN r.tag"
        )
        self._driver.execute_query(
            query,
            routing_="w",
            tag=tag,
            kind=request.kind,
            user_tag=user_tag,
            comment=request.comment,
            attribute=json.dumps(request.attribute.model_dump()) if request.attribute is not None else None,
            trait=json.dumps(request.trait.model_dump()) if request.trait is not None else None,
            target=target,
            result_transformer_=Result.value,
        )
        return tag

    def exists(self, tag: str) -> bool:
        query = "RETURN EXISTS { (r:AttributeRequest {tag: $tag}) }"
        r = self._driver.execute_query(query, tag=tag, result_transformer_=Result.value)
        return bool(r[0]) if len(r) > 0 else False

    def get(self, tags: List[str] = None, status: Literal["pending", "accepted", "rejected"] = None,
            kind: Literal["attribute", "trait"] = None, user_tag: str = None, limit: int = 50) -> List[AttributeRequestModel]:
        conditions, params = [], {"limit": limit}
        for key, value, condition in (
            ("status", status, "r.status = $status"),
            ("kind", kind, "r.kind = $kind"),
            ("user_tag", user_tag, "r.user_tag = $user_tag"),
            ("tags", tags, "r.tag IN $tags"),
        ):
            if value is not None:
                conditions.append(condition)
                params[key] = value

        query = "MATCH (r:AttributeRequest) "
        if len(conditions) > 0:
            query += "WHERE " + " AND ".join(conditions) + " "
        query += self._RETURN + "ORDER BY r.created_at DESC LIMIT $limit"

        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, **params)
        return [self._to_model(self._parse_row(row)) for row in r]

    def get_pending(self, kind: Literal["attribute", "trait"] = None, limit: int = 50) -> List[AttributeRequestModel]:
        return self.get(status="pending", kind=kind, limit=limit)

    def accept(self, tag: str, reviewer_tag: str, comment: Optional[str] = None,
               edits: Optional[dict] = None) -> AttributeRequestModel:
        row = self._get_node(tag)
        if row["status"] != "pending":
            raise ValueError(f"Attribute request with tag '{tag}' is not pending.")

        kind = row["kind"]
        proposal = {**(row[kind] or {}), **(edits or {})}

        if kind == "attribute":
            if not isinstance(proposal.get("text"), str) or len(proposal["text"].strip()) == 0:
                raise ValueError("The attribute text must not be empty.")
            attribute_tag = self._attribute_tag(proposal["text"])
            self._check_attribute_tag_length(attribute_tag)
            if self.attributes.exists(tag=attribute_tag):
                raise ValueError(f"An attribute with the tag '{attribute_tag}' exists already.")
            ok = self.attributes.insert(
                tag=attribute_tag,
                text=proposal["text"],
                priority=proposal.get("priority", 500),
                abbreviation=proposal.get("abbr"),
                allow_input=proposal.get("allow_input", False),
                group_tags=proposal.get("group_tags") or [],
                parents=proposal.get("parents") or [],
                children=proposal.get("children") or [],
                required_trait_tags=proposal.get("required_trait_tags") or [],
            )
            if not ok:
                raise ValueError("Failed to insert the proposed attribute.")
            for t in proposal.get("traits") or []:
                self.attributes.insert_trait(self._trait_from_proposal({**t, "attribute_tag": attribute_tag}))
        else:
            if not isinstance(proposal.get("text"), str) or len(proposal["text"].strip()) == 0:
                raise ValueError("The trait text must not be empty.")
            trait = self._trait_from_proposal(proposal)
            if not self.attributes.exists(tag=trait.attribute_tag):
                raise ValueError(f"Attribute '{trait.attribute_tag}' not found.")
            if self.attributes.exists(tag=trait.attribute_tag, trait=trait.tag):
                raise ValueError(f"A trait with the tag '{trait.tag}' exists already for this attribute.")
            self.attributes.insert_trait(trait)

        self._set_status(tag, "accepted", reviewer_tag, comment, kind=kind, proposal=proposal)
        row[kind] = proposal
        row["status"] = "accepted"
        return self._to_model(row)

    def reject(self, tag: str, reviewer_tag: str, comment: Optional[str] = None) -> AttributeRequestModel:
        row = self._get_node(tag)
        if row["status"] != "pending":
            raise ValueError(f"Attribute request with tag '{tag}' is not pending.")
        self._set_status(tag, "rejected", reviewer_tag, comment)
        row["status"] = "rejected"
        return self._to_model(row)