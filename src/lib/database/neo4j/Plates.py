import re
from typing import List, Optional, Tuple
from neo4j import Driver, Result

from config.models.plates import PlateInsertModel, PlateModel, PlateOptionModel, PlateOptionsModel
from config.models.attributes import AttributeTree
from lib.database.abstract.Plates import PlatesABC
from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from services.random_generators import get_random_string


# attribute tags of the storage group used for plates
PLATE_ATTRIBUTES = {"format": "att_container_format", "cold_storage": "att_cold_storage", "plate_type": "att_plate_type", "vendor": "att_vendor"}


def _trait_text(attribute_tag : str) -> str:
    "Cypher pattern comprehension returning the trait text of the plate's condition application for an attribute."
    return (
        "[(p)-[:HAS_APPLICATION]->(ca:ConditionApplication)-[:INSTANCE_OF]->(t:Trait) "
        f"WHERE (ca)-[:OF_ATTRIBUTE]->(:Attribute {{tag : '{attribute_tag}'}}) | t.text][0]"
    )


def _parse_format(value : str) -> Tuple[int, int]:
    "Parses a format trait value like '8x12' into (rows, columns)."
    m = re.fullmatch(r"\s*(\d+)\s*x\s*(\d+)\s*", str(value or ""))
    if m is None:
        raise ValueError(f"Plate format '{value}' is not of the form '<rows>x<columns>' (e.g. 8x12).")
    return int(m.group(1)), int(m.group(2))


class Neo4JPlates(PlatesABC):
    """
    Neo4J implementation of the PlatesABC interface.

    Graph
    -----
    (:User)-[:CREATED]->(:Plate {rows, columns, ...})
    (:Plate)-[:HAS_APPLICATION]->(:ConditionApplication)   # format, cold storage, plate type, vendor
    (:Run)-[:ON_PLATE {row_index, column_index, position}]->(:Plate)
    """

    _PLATE_RETURN = (
        "OPTIONAL MATCH (u:User)-[:CREATED]->(p) "
        "RETURN p{.*, user_tag: u.tag, created_by: u.firstname + ' ' + u.lastname, "
        "   n_used_wells: COUNT {(p)<-[:ON_PLATE]-(:Run)}, "
        f"   format: coalesce(p.format, {_trait_text(PLATE_ATTRIBUTES['format'])}), "
        f"   cold_storage: {_trait_text(PLATE_ATTRIBUTES['cold_storage'])}, "
        f"   plate_type: {_trait_text(PLATE_ATTRIBUTES['plate_type'])}, "
        f"   vendor: {_trait_text(PLATE_ATTRIBUTES['vendor'])}"
        "} AS plate "
    )

    def __init__(self, driver : Driver, condition_applications : ConditionApplicationABC) -> None:
        self._driver = driver
        self._condition_applications = condition_applications

    def exists(self, tag : str) -> bool:
        query = (
            "WITH EXISTS {(p:Plate {tag : $tag})} as plate_exists "
            "RETURN plate_exists "
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        return r[0]

    def name_exists(self, name : str) -> bool:
        query = (
            "MATCH (p:Plate) WHERE toLower(p.name) = toLower($name) "
            "RETURN count(p) > 0 "
        )
        r = self._driver.execute_query(query, routing_="r", name=name, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False

    def next_name(self, rows : int, columns : int) -> str:
        prefix = f"P-{rows * columns}-"
        query = (
            "MATCH (p:Plate) WHERE p.name STARTS WITH $prefix "
            "RETURN p.name "
        )
        names = self._driver.execute_query(query, routing_="r", prefix=prefix, result_transformer_=Result.value)
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
        numbers = [int(m.group(1)) for name in names if (m := pattern.match(name))]
        return f"{prefix}{(max(numbers) + 1 if numbers else 1):03d}"

    def _get_traits(self, attribute_tag : str) -> List[dict]:
        "Returns the traits of an attribute ordered by priority."
        query = (
            "MATCH (:Attribute {tag : $attribute_tag})-[:HAS_TRAIT]->(t:Trait) "
            "RETURN t.tag AS tag, t.text AS text, t.description AS description, t.value AS value "
            "ORDER BY t.priority DESC "
        )
        return self._driver.execute_query(query, routing_="r", attribute_tag=attribute_tag, result_transformer_=Result.data)

    def _get_trait_value(self, attribute_tag : str, trait_tag : str) -> Optional[str]:
        "Returns the trait value if the trait belongs to the attribute, otherwise None."
        query = (
            "MATCH (:Attribute {tag : $attribute_tag})-[:HAS_TRAIT]->(t:Trait {tag : $trait_tag}) "
            "RETURN coalesce(t.value, t.text) "
        )
        r = self._driver.execute_query(query, routing_="r", attribute_tag=attribute_tag, trait_tag=trait_tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else None

    def get_options(self) -> PlateOptionsModel:
        formats = []
        for t in self._get_traits(PLATE_ATTRIBUTES["format"]):
            try:
                rows, columns = _parse_format(t["value"])
            except ValueError:
                continue  # skip traits without a valid '<rows>x<columns>' value
            formats.append(PlateOptionModel(tag=t["tag"], text=t["text"], description=t["description"], rows=rows, columns=columns))

        def options(key : str) -> List[PlateOptionModel]:
            return [PlateOptionModel(tag=t["tag"], text=t["text"], description=t["description"]) for t in self._get_traits(PLATE_ATTRIBUTES[key])]

        return PlateOptionsModel(
            formats=formats,
            cold_storage=options("cold_storage"),
            plate_type=options("plate_type"),
            vendor=options("vendor"),
        )

    def insert(self, plate : PlateInsertModel, user_tag : str) -> str:
        name = plate.name.strip()

        # format -> rows, columns and text (stored on the plate node)
        format_value = self._get_trait_value(PLATE_ATTRIBUTES["format"], plate.format_trait_tag)
        if format_value is None:
            raise ValueError("Unknown plate format.")
        rows, columns = _parse_format(format_value)
        format_text = self._driver.execute_query(
            "MATCH (t:Trait {tag : $tag}) RETURN t.text", routing_="r",
            tag=plate.format_trait_tag, result_transformer_=Result.value)[0]

        if self.name_exists(name):
            raise ValueError(f"A plate with the name '{name}' exists already. "
                             f"Suggested name: {self.next_name(rows, columns)}")

        # selected traits that become condition applications of the plate
        selected = [
            (PLATE_ATTRIBUTES["format"], plate.format_trait_tag),
            (PLATE_ATTRIBUTES["cold_storage"], plate.cold_storage_trait_tag),
            (PLATE_ATTRIBUTES["plate_type"], plate.plate_type_trait_tag),
            (PLATE_ATTRIBUTES["vendor"], plate.vendor_trait_tag),
        ]
        selected = [(a, t) for a, t in selected if t]
        for attribute_tag, trait_tag in selected:
            if self._get_trait_value(attribute_tag, trait_tag) is None:
                raise ValueError(f"Trait '{trait_tag}' does not belong to attribute '{attribute_tag}'.")

        tag = get_random_string(N=10)
        while self.exists(tag):
            tag = get_random_string(N=10)
        query = (
            "MATCH (u:User {tag : $user_tag}) "
            "CREATE (p:Plate {tag : $tag, name : $name, "
            "   format : $format, rows : $rows, columns : $columns, n_wells : $n_wells, "
            "   location : $location, description : $description, created_at : timestamp()}) "
            "MERGE (u)-[:CREATED]->(p) "
            "RETURN p.tag "
        )
        r = self._driver.execute_query(query, routing_="w", result_transformer_=Result.value,
                                       user_tag=user_tag,
                                       tag=tag,
                                       name=name,
                                       format=format_text,
                                       rows=rows,
                                       columns=columns,
                                       n_wells=rows * columns,
                                       location=plate.location,
                                       description=plate.description)
        if len(r) == 0:
            raise ValueError("Plate could not be created (user not found).")

        # create/reuse the condition applications and link them to the plate
        ca_tags = []
        for attribute_tag, trait_tag in selected:
            tree = AttributeTree(tag=attribute_tag, type="attribute", value=None,
                                 children=[AttributeTree(tag=trait_tag, type="trait", value=None, children=[])])
            ca_tags.append(self._condition_applications.insert(condition_application=tree))
        query = (
            "MATCH (p:Plate {tag : $tag}) "
            "UNWIND $ca_tags AS ca_tag "
            "MATCH (ca:ConditionApplication {tag : ca_tag}) "
            "MERGE (p)-[r:HAS_APPLICATION]->(ca) "
            "SET r.created_at = timestamp() "
        )
        self._driver.execute_query(query, routing_="w", tag=tag, ca_tags=ca_tags)
        return tag

    def get(self, tag : str) -> Optional[PlateModel]:
        query = "MATCH (p:Plate {tag : $tag}) " + self._PLATE_RETURN
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        return PlateModel(**r[0]) if len(r) > 0 else None

    def list(self) -> List[PlateModel]:
        query = "MATCH (p:Plate) " + self._PLATE_RETURN + "ORDER BY plate.created_at DESC "
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return [PlateModel(**p) for p in r]

    def get_occupied_positions(self, tag : str) -> List[Tuple[int, int, str]]:
        query = (
            "MATCH (:Plate {tag : $tag})<-[o:ON_PLATE]-(:Run) "
            "RETURN o.row_index AS row_index, o.column_index AS column_index, o.position AS position "
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.data)
        return [(w["row_index"], w["column_index"], w["position"]) for w in r]

    def check_positions(self, tag : str, positions : List[List[bool]]) -> None:
        plate = self.get(tag=tag)
        if plate is None:
            raise ValueError(f"Plate {tag} not found.")
        if len(positions) != plate.rows or any(len(row) != plate.columns for row in positions):
            raise ValueError(f"Well selection does not match plate {plate.name} ({plate.rows} x {plate.columns}).")
        taken = [label for r, c, label in self.get_occupied_positions(tag=tag) if positions[r][c]]
        if taken:
            raise ValueError(f"Wells already used on plate {plate.name}: {', '.join(taken)}")

    def delete(self, tag : str) -> bool:
        if len(self.get_occupied_positions(tag=tag)) > 0:
            raise ValueError("Runs are stored on this plate. Delete the runlists first.")
        # only the plate (and its relationships) is removed, condition applications are shared and stay
        self._driver.execute_query("MATCH (p:Plate {tag : $tag}) DETACH DELETE p", routing_="w", tag=tag)
        return True