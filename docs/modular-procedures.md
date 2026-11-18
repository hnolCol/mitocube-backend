# Modular Procedures (facility workflow modules)

Modular procedures model the facility's wet-lab workflow as a chain of **modules** (e.g.
"Protein Concentration Measurement" → "SP3 Digestion" → "Measurement"). Submissions are
tracked while they pass through these modules, and **executions** record what physically
happened to the samples: which input plate wells were transferred into which output plate
wells, under which conditions, with which measured values.

All endpoints live under `/api/procedures` and require authentication. Creating, editing,
publishing, versioning, linking, marking done and executing requires the **curator** role
or higher; viewing is open to all users. The router is `src/routers/procedures/procedures.py`,
the database implementation `src/lib/database/neo4j/Procedures.py`, the models
`src/config/models/procedures.py`.

---

## Concepts

| Concept | Meaning |
|---|---|
| **Modular procedure** | A workflow module (like an SOP): title, description, condition applications (instruments, protocols, treatments via the attribute/trait system) and linked protocols. Drafts are editable; **publishing** freezes the content with a SHA-256 hash. |
| **Version** | Published procedures are immutable, but a new **draft version** can be created from a published one (`POST /{tag}/versions`). Versions of one procedure share a `lineage_tag` and are chained via `PREVIOUS_VERSION`. Submissions stay linked to the exact version they were assigned to. |
| **Link** | `(Submission)-[:IN_PROCEDURE {position, created_at, done, done_at, done_by}]->(Procedure)`. A submission can be linked to several procedures over its lifetime (the module history), but **only one open (not done) module at a time**. |
| **Execution** | A concrete run of a published procedure: input plate wells (with samples) are mapped to output plate wells; pooling and splitting are supported. An execution starts in the **RUNNING** state and is closed by an explicit confirmation (`finish`: SUCCEEDED / FAILED / ABORTED) that frees the submissions owning the placed samples for the next module. |
| **Well metric** | A measured value of an output well, e.g. the protein concentration. Metrics follow the condition-application pattern: each value is a node that is an **instance of a trait** (the trait defines the measured quantity, e.g. *µg/µL* of the *Concentration* attribute). |

## Data model

```
(:ModularProcedure {tag, title, description, status: DRAFT|PUBLISHED, version, lineage_tag,
                    content_hash, created_at, published_at, user_tag})
    -[:HAS_CONDITION_APPLICATION]-> (:ConditionApplication)
    -[:ACCEPTS_INPUT_ATTRIBUTE]->   (:Attribute)
    -[:EXPECTS_OUTPUT_ATTRIBUTE]-> (:Attribute)
    -[:HAS_PROTOCOL]->               (:Protocol)
    <-[:PREVIOUS_VERSION]-           (:ModularProcedure)          # newer version
    <-[:IN_PROCEDURE {position, created_at, done, done_at, done_by}]- (:Submission)
    <-[:WAS_EXECUTED]-               (:ModularProcedureExecution)

(:ModularProcedureExecution {tag, procedure_tag, input_plate_tag, output_plate_tag,
                             user_tag, responsible_user_tag, created_at,
                             status: RUNNING|SUCCEEDED|FAILED|ABORTED,
                             finished_at, finished_by, finish_comment, done_submission_tags})
    -[:HAS_WELL]-> (:ExecutionWell {execution_tag, position, row_index, column_index,
                                    side: INPUT|OUTPUT, output_positions})
    -[:EXECUTED]- (:User), (:User)-[:EXECUTED]-> (execution)

(:Sample)-[:IN_WELL]->        (:ExecutionWell)          # many-to-many: pooling and splitting
(:ExecutionWell)-[:HAS_APPLICATION]-> (:ConditionApplication)   # output wells only
(:ExecutionWell)-[:HAS_METRIC]-> (:ExecutionWellMetric {value, created_at})
(:ExecutionWellMetric)-[:INSTANCE_OF]-> (:Trait)        # e.g. the µg/µL trait
(:ExecutionWellMetric)-[:OF_ATTRIBUTE]-> (:Attribute)   # e.g. Concentration
```

Notes:

- `ExecutionWell.output_positions` (input side) stores the transfer map: the output wells
  this input well was transferred to. The samples of an output well are derived from this
  map, so a sample can legitimately appear in several output wells (splitting) and a pooled
  output well contains the samples of all input wells mapped into it.
- Execution and procedure tags are **content hashes** (procedure tag: title + description +
  condition applications + version; execution tag: the full transfer map). Identical
  entities are rejected instead of duplicated.
- The responsible user of an execution defaults to the executing user and is validated to exist.

## Endpoints

| Method | Path | Role | Description |
|---|---|---|---|
| `POST` | `/api/procedures` | curator+ | Create a draft procedure. |
| `GET` | `/api/procedures/q` | all | Query procedures; parameters `search_string`, `status`, `limit`, `latest_only` (only the highest version per lineage). |
| `GET` | `/api/procedures/{tag}` | all | One procedure with CAs, protocols and status. |
| `PATCH` | `/api/procedures/{tag}` | curator+ | Edit a **draft** (published procedures are immutable). |
| `POST` | `/api/procedures/{tag}/publish` | curator+ | Publish: set the content hash, lock the procedure. |
| `POST` | `/api/procedures/{tag}/versions` | curator+ | Create a new draft version from a **published** procedure (copies content, CAs, protocols). |
| `GET` | `/api/procedures/{tag}/versions` | all | All versions of the lineage, oldest first. |
| `DELETE` | `/api/procedures/{tag}` | curator+ | Delete a draft. |
| `POST` | `/api/procedures/{tag}/link/{submission_tag}` | curator+ | Assign a submission. Rejected if the submission has an open link to another procedure. |
| `DELETE` | `/api/procedures/{tag}/link/{submission_tag}` | curator+ | Unlink a submission. |
| `POST` | `/api/procedures/{tag}/link/{submission_tag}/done` | curator+ | Mark the submission done in this module. |
| `DELETE` | `/api/procedures/{tag}/link/{submission_tag}/done` | curator+ | Reopen (revert done). |
| `GET` | `/api/procedures/{tag}/submissions` | all | Submissions linked to a procedure. |
| `GET` | `/api/procedures/submissions/{submission_tag}` | all | Modules of a submission, ordered by link position (the module history). |
| `POST` | `/api/procedures/{tag}/execute` | curator+ | Start an execution of a **published** procedure (see below). |
| `GET` | `/api/procedures/{tag}/executions` | all | Execution tags of a procedure. |
| `GET` | `/api/procedures/executions/q` | all | Summaries of the executions visible to the user (submission scope respected): `search_submission_tag`, `status`, `limit`. |
| `GET` | `/api/procedures/executions/{execution_tag}` | all | One execution with input wells, output wells, samples, CAs, metrics and status (restricted users only see their own submissions' data). |
| `GET` | `/api/procedures/executions/{execution_tag}/states` | all | The state history of the execution: state, created_at and the user who changed it, newest first. |
| `POST` | `/api/procedures/executions/{execution_tag}/metrics` | curator+ | Set or update well metrics (see below). |
| `POST` | `/api/procedures/executions/{execution_tag}/finish` | curator+ | Confirm a running execution with an outcome (SUCCEEDED/FAILED/ABORTED): frees the linked submissions; on success optionally sets the submission state and adopts the condition applications. |

## Executing a procedure

`POST /api/procedures/{tag}/execute` with:

```json
{
  "input_plate_tag": "plt_...",
  "output_plate_tag": "plt_...",
  "responsible_user_tag": "usr_...",            // optional, defaults to the executing user
  "input_wells": [
    { "position": "A1", "sample_tags": ["smp_1", "smp_2"], "output_positions": ["A1"] },
    { "position": "B1", "sample_tags": ["smp_3"], "output_positions": ["A1", "B1", "C1"] }
  ],
  "output_wells": [
    { "position": "A1", "condition_application_tags": ["ca_heat_treatment"] },
    { "position": "B1", "condition_application_tags": [] },
    { "position": "C1", "condition_application_tags": [] }
  ],
  "output_well_metrics": [
    { "position": "A1", "trait_tag": "trt_ug_per_ul", "value": 2.5 }
  ]
}
```

The example shows both mapping modes: **pooling** (A1 and B1 both map into output A1 —
differently treated samples are pooled into a single well) and **splitting** (B1 maps into
A1, B1 and C1 — one sample appears in several output wells).

Validation: the procedure must be published; plates, samples, users and traits must exist;
well positions must be unique and parseable (`A1` style); input wells must contain samples;
every transfer target must be a defined output well; **output wells already used by another
execution on the same plate are rejected**; the input and output plates must match the
**plate layout constraints** the procedure defines (see below); the responsible user must
be a **curator** (it defaults to the executing user); metrics must reference declared
attributes of the procedure.

The execution is created in the **RUNNING** state: the submissions are **not** freed yet.

### Procedure setup (SOP definition)

A procedure defines more than title/description/condition applications/protocols — it is a
tightly defined SOP. The setup (insert/update) additionally accepts:

| Field | Meaning |
|---|---|
| `input_plate_format` / `input_plate_type` | Required container format (e.g. `8x12` for a 96 well plate) and/or plate type (e.g. a PCR strip) of the **input** plate. `null` = unconstrained. Executions are rejected (400) if the chosen plate does not match. |
| `output_plate_format` / `output_plate_type` | Same for the **output** plate. |
| `input_attribute_tags` | Attributes whose values may be entered per **input** well before the run (`allow_input` semantics), e.g. *Concentration*. |
| `output_attribute_tags` | Attributes for which data are expected on the output wells of a successful run. |
| `success_submission_state` | Optional submission state (`SubmissionStatesEnums` name, e.g. `PROCESSED`) that is set automatically for the linked **submissions** when an execution is confirmed successful. `null` = the state is not changed. |

Attributes are stored via `(:ModularProcedure)-[:ACCEPTS_INPUT_ATTRIBUTE]->(:Attribute)` and
`-[:EXPECTS_OUTPUT_ATTRIBUTE]->(:Attribute)`; plate constraints and the success state are
procedure properties and part of the content hash.

Input well values: `input_well_metrics` (`{position, trait_tag, value, side: "INPUT"}`) records
the numeric per-well values of the declared input attributes at execution time (e.g. the
concentration of each sample before harmonization). `output_well_metrics` defaults to
`side: "OUTPUT"` and keeps its previous meaning.

### Finishing an execution (confirmation)

`POST /api/procedures/executions/{execution_tag}/finish` with `{"outcome": "SUCCEEDED" |
"FAILED" | "ABORTED", "comment": "..."}` closes a **running** execution. Regardless of the
outcome the submissions owning the placed samples are marked **done** in the procedure
(`done`, `done_at`, `done_by` on `IN_PROCEDURE`, recorded in `done_submission_tags`): the
samples physically stay where the execution placed them (the `IN_WELL` links are kept),
but the submissions are freed for the next module. Only `SUCCEEDED` additionally:

- sets the optional `success_submission_state` on each linked submission, and
- makes the submissions **adopt** the condition applications of the module (both the
  procedure-level ones and the ones applied to the output wells their samples ended up in)
  via `HAS_APPLICATION`.

The execution node records `status`, `finished_at`, `finished_by` and `finish_comment`.
Changing to the current state is rejected with 400; finished executions can be corrected
(e.g. FAILED → SUCCEEDED: the success effects are then applied and the submissions had already
been freed when the execution first left RUNNING).

### Execution states (history)

Like submissions, executions keep a full **state history**: every state is a separate
`(:ProcessingState {tag})` node (RUNNING, SUCCEEDED, FAILED, ABORTED) linked via

```
(:ModularProcedureExecution)-[:IN_STATE {created_at, user_tag}]->(:ProcessingState)
```

`execute` creates the RUNNING state; `finish` appends the new state — the user who made the
change and the timestamp are recorded on the relationship. `GET /executions/{tag}/states`
returns the history (state, `created_at`, `user_tag`), newest first.

### Execution overview and data visibility

`GET /api/procedures/executions/q?search_submission_tag=&status=&limit=` lists execution
**summaries** (header data and well counts) for the overview dashboard, newest first, and
respects the **submission scope** of the requesting user:

- **curators and admins** (role ≥ curator): all executions.
- **group curators**: the executions of their research group's (and consortium-shared and own)
  submissions — the same scope the submissions database computes for them.
- **other users**: only executions placing samples of their own accessible submissions
  (creators); searching for a foreign submission returns nothing.

The same rules apply to `GET /executions/{tag}` (the full plate details): restricted users
only see wells holding their own samples — wells with only foreign samples are omitted,
shared wells expose only the own sample tags and neither their metrics (input values and
output data) nor their condition applications. Changing the state is reserved for curators
and admins (`403` otherwise).

## Well metrics

Metrics are measured attribute values per output well, stored the same way condition values
are: a node per value, `INSTANCE_OF` a trait (the quantity, e.g. *µg/µL*) and `OF_ATTRIBUTE`
the attribute (e.g. *Concentration*). This makes them first-class graph citizens:

```
MATCH (w:ExecutionWell)-[:HAS_METRIC]->(m:ExecutionWellMetric)-[:INSTANCE_OF]->(t:Trait)
WHERE t.tag = $trait AND m.value < $threshold
RETURN w.execution_tag, w.position, m.value
```

Metrics can be supplied at execution time (`output_well_metrics`, `input_well_metrics`) or
set/updated afterwards via `POST /executions/{tag}/metrics` with a list of
`{position, trait_tag, value, side}` entries. Duplicate `(position, trait, side)` pairs are
rejected; traits are validated to exist.


## Single open module rule

A submission can only be linked to one modular procedure at a time: `link` is rejected with
a 400 if the submission has an `IN_PROCEDURE` relationship with `done = false` to another
procedure. Done links never block — that is what lets a submission proceed through the
module chain while keeping its full module history. Reverting a done flag (reopen) puts the
submission back into the open state of that module and blocks new links accordingly.
