# Submission statistics endpoints

All endpoints require authentication. All filter parameters are optional and default to "no filtering", so the endpoints stay backward compatible.

## General filter parameters

The following parameters are shared by the statistics endpoints listed below:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `state` | string (semicolon-separated) | `None` | Restrict to submissions in one of these states. |
| `user_tags` | string (semicolon-separated) | `None` | Restrict to submissions created or collaborated on by these users (same semantics as the submission query endpoints, e.g. `user_tags=usr_abc;usr_def`). A literal `null`/`None` value is ignored. |
| `ca_tags` | string (semicolon-separated) | `None` | Restrict to submissions containing these condition applications (submission-level by default). |
| `include_sample_ca` | boolean | `false` | Only relevant together with `ca_tags`: when `true`, sample-level condition applications are matched as well, not only submission-level ones. |
| `genotype_tags` | string (semicolon-separated) | `None` | Restrict to submissions whose samples contain all of these genotypes (same semantics as the submission query endpoints, e.g. `genotype_tags=gen_a;gen_b`). A literal `null`/`None` value is ignored. |

The filters are combined with AND semantics. `include_sample_ca` without `ca_tags` has no effect. All listed genotypes must be present (AND within `genotype_tags`).

## Endpoints

### `GET /api/stats/submissions/counts/submissions`

Number of submissions per research group or trait and year. Supports `group_by`, `years`, `attribute_tag`, `group_by_entity` plus the general filter parameters (`state`, `user_tags`, `ca_tags`, `include_sample_ca`, `genotype_tags`).

### `GET /api/stats/submissions/counts/samples`

Number of samples per research group and year. Supports `group_by`, `years` plus the general filter parameters (`state`, `user_tags`, `ca_tags`, `include_sample_ca`, `genotype_tags`).

### `GET /api/stats/submissions/counts/users`

Number of submissions per user and year. Supports `years`, `research_group_tags` plus the general filter parameters (`state`, `user_tags`, `ca_tags`, `include_sample_ca`, `genotype_tags`).

### `GET /api/stats/submissions/durations`

Duration statistics between two states (aggregated or per-year quantiles via `group_by_year=true`). Supports `state_01`, `state_02`, `aggregate`, `group_by_year`, `years` plus the general filter parameters (`state`, `user_tags`, `ca_tags`, `include_sample_ca`, `genotype_tags`). Null values sent for `user_tags` are ignored.

### `GET /api/stats/submissions/samples_per_submission`

Per-year quantile summaries of the number of samples per submission. Supports `years` plus the general filter parameters (`state`, `user_tags`, `ca_tags`, `include_sample_ca`, `genotype_tags`).

### `GET /api/stats/submissions/counts/states`

Number of submissions currently in each state, grouped by the submission's current (latest) state.
Returns flat rows: `[{ "state_tag": 2, "value": 31 }, ...]`. States with no submissions are absent.
Supports the general filter parameters (`user_tags`, `ca_tags`, `include_sample_ca`, `genotype_tags`).
There is no `state` parameter since the state is the grouping variable.

### `GET /api/submissions/quantifications/protein_groups/count`

Number of quantified protein groups per submission. Supports the general filter parameters (`user_tags`, `ca_tags`, `include_sample_ca`); results are restricted to the matching submissions.
