import re
from string import ascii_uppercase
from typing import List, Optional, Tuple
from neo4j import Driver, Result

from config.models.plates import PlateInsertModel, PlateModel, PlateOptionModel, PlateOptionsModel, PlateRunlistModel, PlateSubmissionModel, PlateSubmissionsLayoutModel, PlateWellSubmissionModel, PlateSubmissionLegendModel
from config.models.attributes import AttributeTree
from lib.database.abstract.Plates import PlatesABC
from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from services.random_generators import get_random_string


# attribute tags of the storage group used for plates
PLATE_ATTRIBUTES = {"format": "att_container_format", "cold_storage": "att_cold_storage", "plate_type": "att_plate_type", "vendor": "att_vendor"}

# attributes + traits the plates need; created on startup if missing (existing ones are never changed)
STORAGE_GROUP_TAG = "storage"
STORAGE_ATTRIBUTES = [
    {"tag": "att_container_format", "text": "Container Format", "traits": [
        {"value": "1x8",   "text": "1x8",   "description": "8-tube PCR strip"},
        {"value": "1x12",  "text": "1x12",  "description": "12-tube PCR strip"},
        {"value": "3x5",   "text": "3x5",   "description": "15 wells (PAL)"},
        {"value": "6x9",   "text": "6x9",   "description": "54 wells (PAL)"},
        {"value": "8x12",  "text": "8x12",  "description": "96-well plate"},
        {"value": "16x24", "text": "16x24", "description": "384-well plate"},
    ]},
    {"tag": "att_cold_storage", "text": "Cold Storage", "traits": [
        {"value": "-20", "text": "-20 °C freezer", "description": "Standard freezer (-20 °C)"},
        {"value": "-80", "text": "-80 °C freezer", "description": "Ultra-low temperature freezer (-80 °C)"},
    ]},
    {"tag": "att_plate_type", "text": "Plate Type", "traits": [
        {"value": "pcr_skirted", "text": "PCR plate (skirted)", "description": "Fully skirted PCR plate, autosampler/robot compatible"},
    ]},
    {"tag": "att_vendor", "text": "Vendor", "traits": [
        {"value": "thermo_fisher", "text": "Thermo Fisher Scientific", "description": "Thermo Fisher Scientific"},
    ]},
]


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
        "   n_runlists: COUNT { MATCH (p)<-[:ON_PLATE]-(:Run)<-[:HAS_RUN]-(rl:RunList) RETURN DISTINCT rl }, "
        "   n_submissions: COUNT { MATCH (p)<-[:ON_PLATE]-(:Run)<-[:HAS_RUN]-(:RunList)<-[:HAS_RUNLIST]-(s:Submission) RETURN DISTINCT s }, "
        f"   format: coalesce(p.format, {_trait_text(PLATE_ATTRIBUTES['format'])}), "
        f"   cold_storage: {_trait_text(PLATE_ATTRIBUTES['cold_storage'])}, "
        f"   plate_type: {_trait_text(PLATE_ATTRIBUTES['plate_type'])}, "
        f"   vendor: {_trait_text(PLATE_ATTRIBUTES['vendor'])}"
        "} AS plate "
    )

    def __init__(self, driver : Driver, condition_applications : ConditionApplicationABC):
        self._driver = driver
        self._condition_applications = condition_applications
        self.ensure_storage_attributes()

    def ensure_storage_attributes(self) -> None:
        """Creates the storage attribute group, the plate attributes and their default traits
        if they do not exist yet. Existing attributes and traits are not changed.
        """
        attributes = [
            {
                "tag": a["tag"],
                "text": a["text"],
                "s": f"{a['text'].lower()} {a['tag']}",
                "traits": [
                    {**t,
                     "tag": f"{a['tag']}:{t['value']}",
                     "s": f"{t['text'].lower()} {t['description'].lower()}"}
                    for t in a["traits"]
                ]
            }
            for a in STORAGE_ATTRIBUTES
        ]
        query = (
            "MERGE (ag:AttributeGroup {tag: $group_tag}) "
            "ON CREATE SET ag.created_at = timestamp() "
            "WITH ag "
            "UNWIND $attributes AS attr "
            "MERGE (a:Attribute {tag: attr.tag}) "
            "ON CREATE SET a.text = attr.text, a.priority = 500, a.allow_input = false, "
            "              a.s = attr.s, a.created_at = timestamp() "
            "MERGE (a)-[:PART_OF]->(ag) "
            "WITH a, attr "
            "OPTIONAL MATCH (s:State) WHERE toInteger(s.tag) = 0 "
            "FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END | MERGE (a)-[:REQUIRES_STATE]->(s)) "
            "WITH a, attr "
            "UNWIND attr.traits AS trait "
            "MERGE (t:Trait {tag: trait.tag}) "
            "ON CREATE SET t.text = trait.text, t.description = trait.description, t.value = trait.value, "
            "              t.priority = 500, t.attribute_tag = attr.tag, t.s = trait.s, t.created_at = timestamp() "
            "MERGE (a)-[:HAS_TRAIT]->(t) "
        )
        self._driver.execute_query(query, group_tag=STORAGE_GROUP_TAG, attributes=attributes, routing_="w")

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

    _RUNLISTS_QUERY = (
        "MATCH (p:Plate {tag : $tag})<-[o:ON_PLATE]-(r:Run)<-[:HAS_RUN]-(rl:RunList)<-[:HAS_RUNLIST]-(s:Submission) "
        "OPTIONAL MATCH (u:User)-[:CREATED]->(rl) "
        "OPTIONAL MATCH (rl)-[:MEASURED_BY]->(inst:Trait) "
        "RETURN rl.tag AS runlist_tag, rl.created_at AS created_at, "
        "   inst.tag AS instrument_tag, inst.text AS instrument_text, "
        "   rl.fractionated AS fractionated, rl.scrambled AS scrambled, "
        "   count(r) AS n_runs_on_plate, collect(DISTINCT o.position) AS used_positions, "
        "   u.tag AS user_tag, u.firstname AS user_firstname, u.lastname AS user_lastname, "
        "   s.tag AS submission_tag, coalesce(s.label, s.tag) AS submission_label, s.title AS submission_title "
        "ORDER BY rl.created_at DESC "
    )

    def get_runlists(self, tag : str) -> List[PlateRunlistModel]:
        "Returns all runlists that have at least one run on the plate, newest first."
        r = self._driver.execute_query(self._RUNLISTS_QUERY, routing_="r", tag=tag, result_transformer_=Result.data)
        return [PlateRunlistModel(**row) for row in r]

    _SUBMISSIONS_QUERY = (
        "MATCH (p:Plate {tag : $tag})<-[o:ON_PLATE]-(r:Run)<-[:HAS_RUN]-(rl:RunList)<-[:HAS_RUNLIST]-(s:Submission) "
        "OPTIONAL MATCH (u:User)-[:CREATED]->(s) "
        "WITH s, rl, count(r) AS n_runs_on_plate "
        "RETURN s.tag AS submission_tag, coalesce(s.label, s.tag) AS submission_label, "
        "   s.title AS submission_title, "
        "   u.tag AS user_tag, u.firstname AS user_firstname, u.lastname AS user_lastname, "
        "   sum(n_runs_on_plate) AS n_runs_on_plate, count(DISTINCT rl) AS n_runlists "
        "ORDER BY s.tag "
    )

    def get_submissions(self, tag : str) -> List[PlateSubmissionModel]:
        "Returns the distinct submissions that were measured on the plate via any runlist."
        r = self._driver.execute_query(self._SUBMISSIONS_QUERY, routing_="r", tag=tag, result_transformer_=Result.data)
        return [PlateSubmissionModel(**row) for row in r]

    _LAYOUT_QUERY = (
        "MATCH (p:Plate {tag : $tag}) "
        "OPTIONAL MATCH (p)<-[o:ON_PLATE]-(r:Run)<-[:HAS_RUN]-(rl:RunList)<-[:HAS_RUNLIST]-(s:Submission) "
        "OPTIONAL MATCH (u:User)-[:CREATED]->(s) "
        "RETURN p.tag AS plate_tag, p.rows AS rows, p.columns AS columns, "
        "   collect(DISTINCT {row_index: o.row_index, column_index: o.column_index, position: o.position, "
        "       submission_tag: s.tag, runlist_tag: rl.tag, run_name: r.text, measured_at: rl.created_at}) AS used, "
        "   collect(DISTINCT {submission_tag: s.tag, submission_label: coalesce(s.label, s.tag), "
        "       submission_title: s.title, user_tag: u.tag, "
        "       user_firstname: u.firstname, user_lastname: u.lastname}) AS submissions "
    )

    def get_submission_layout(self, tag : str) -> Optional[PlateSubmissionsLayoutModel]:
        """Returns the full well grid of the plate with the well -> submission mapping
        and the submission legend. Returns None if the plate does not exist."""
        r = self._driver.execute_query(self._LAYOUT_QUERY, routing_="r", tag=tag, result_transformer_=Result.data)
        if len(r) == 0:
            return None
        row = r[0]
        used = {(w["row_index"], w["column_index"]): w for w in row["used"]
                if w["row_index"] is not None and w["submission_tag"] is not None}
        wells = []
        for row_index in range(row["rows"]):
            for column_index in range(row["columns"]):
                position = f"{ascii_uppercase[row_index]}{column_index + 1}"
                w = used.get((row_index, column_index))
                wells.append(PlateWellSubmissionModel(
                    row_index=row_index, column_index=column_index, position=position,
                    submission_tag=w["submission_tag"] if w else None,
                    runlist_tag=w["runlist_tag"] if w else None,
                    run_name=w["run_name"] if w else None,
                    measured_at=w["measured_at"] if w else None,
                ))
        n_wells = {}
        submissions = []
        for s in row["submissions"]:
            if s["submission_tag"] is None or s["submission_tag"] in n_wells:
                continue
            n_wells[s["submission_tag"]] = sum(1 for w in used.values() if w["submission_tag"] == s["submission_tag"])
            submissions.append(PlateSubmissionLegendModel(**s, n_wells=n_wells[s["submission_tag"]]))
        submissions.sort(key=lambda s : s.submission_tag)
        return PlateSubmissionsLayoutModel(plate_tag=row["plate_tag"], rows=row["rows"], columns=row["columns"],
                                           wells=wells, submissions=submissions)

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