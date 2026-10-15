from neo4j import Driver, Result

from lib.database.abstract.Impressum import ImpressumABC
from config.models.Impressum import ImpressumModel, ImpressumUpdateModel, IMPRESSUM_TAG


class Neo4JImpressum(ImpressumABC):

    def __init__(self, driver : Driver) -> None:
        self._driver = driver

    def get(self) -> ImpressumModel | None:
        "Returns the current impressum, or None if no impressum has been created yet."
        query = (
            "MATCH (i:Impressum {tag : $tag}) "
            "RETURN properties(i) "
        )
        r = self._driver.execute_query(query, routing_="r", tag=IMPRESSUM_TAG, result_transformer_=Result.value)
        return ImpressumModel(**r[0]) if len(r) > 0 else None

    def update(self, impressum : ImpressumUpdateModel, user_tag : str) -> ImpressumModel:
        "Creates or updates the impressum."
        query = (
            "MERGE (i:Impressum {tag : $tag}) "
            "ON CREATE SET i.created_at = timestamp() "
            "SET i.title = $title, i.text = $text, "
            "    i.updated_at = timestamp(), i.updated_by = $user_tag "
        )
        self._driver.execute_query(query, routing_="w",
                                   tag=IMPRESSUM_TAG,
                                   title=impressum.title,
                                   text=impressum.text,
                                   user_tag=user_tag)
        return self.get()
