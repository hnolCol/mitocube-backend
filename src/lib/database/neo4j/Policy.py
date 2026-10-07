from neo4j import Driver, Result

from lib.database.abstract.Policy import PolicyABC
from config.models.Policy import PolicyModel, PolicyUpdateModel, PolicyStatusModel, POLICY_TAG


class Neo4JPolicy(PolicyABC):

    def __init__(self, driver : Driver) -> None:
        self._driver = driver

    def get(self) -> PolicyModel | None:
        "Returns the current policy, or None if no policy has been created yet."
        query = (
            "MATCH (p:Policy {tag : $tag}) "
            "RETURN properties(p) "
        )
        r = self._driver.execute_query(query, routing_="r", tag=POLICY_TAG, result_transformer_=Result.value)
        return PolicyModel(**r[0]) if len(r) > 0 else None

    def update(self, policy : PolicyUpdateModel, user_tag : str) -> PolicyModel:
        """Creates or updates the policy. If bump_version is True, the version is increased
        and all users have to agree again."""
        is_new = self.get() is None
        query = (
            "MERGE (p:Policy {tag : $tag}) "
            "ON CREATE SET p.version = 0, p.created_at = timestamp() "
            "SET p.title = $title, p.text = $text, p.required = $required, "
            "    p.updated_at = timestamp(), p.updated_by = $user_tag, "
            "    p.version = CASE WHEN $bump_version THEN p.version + 1 ELSE p.version END "
            "RETURN p.version "
        )
        self._driver.execute_query(query, routing_="w",
                                   tag=POLICY_TAG,
                                   title=policy.title,
                                   text=policy.text,
                                   required=policy.required,
                                   bump_version=policy.bump_version,
                                   user_tag=user_tag)

        if policy.bump_version or is_new:
            reset_query = (
                "MATCH (u:User) "
                "SET u.agreed_to_policy = false "
            )
            self._driver.execute_query(reset_query, routing_="w")

        return self.get()

    def agree(self, user_tag : str) -> bool:
        "Marks the user as agreed to the current policy version."
        query = (
            "MATCH (p:Policy {tag : $tag}) "
            "MATCH (u:User {tag : $user_tag}) "
            "SET u.agreed_to_policy = true, "
            "    u.agreed_policy_version = p.version, "
            "    u.policy_agreed_at = timestamp() "
            "RETURN true "
        )
        r = self._driver.execute_query(query, routing_="w", tag=POLICY_TAG, user_tag=user_tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False

    def get_status(self, user_tag : str) -> PolicyStatusModel:
        "Returns whether the user has to agree to the policy before using MitoCube."
        query = (
            "MATCH (u:User {tag : $user_tag}) "
            "OPTIONAL MATCH (p:Policy {tag : $tag}) "
            "RETURN coalesce(p.required, false) AS required, "
            "       coalesce(u.agreed_to_policy, false) AS agreed, "
            "       coalesce(p.version, 0) AS version "
        )
        r = self._driver.execute_query(query, routing_="r", tag=POLICY_TAG, user_tag=user_tag, result_transformer_=Result.data)
        if len(r) == 0:
            return PolicyStatusModel(required=False, agreed=False, must_agree=False, version=0)
        row = r[0]
        return PolicyStatusModel(
            required=row["required"],
            agreed=row["agreed"],
            must_agree=row["required"] and not row["agreed"],
            version=row["version"],
        )