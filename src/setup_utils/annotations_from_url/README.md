# Annotation Script

Fetches protein annotations from a remote TSV URL and saves them to the database. Handles pagination and gzip compression automatically.

---

## How It Works

This function is triggered when a user clicks the `Update` button on an annotation group card in the frontend. When clicked:

1. The frontend calls the API which runs `update_annotations_from_group_url` for that group
2. The function fetches TSV data from the URL configured on the group
3. It parses each row, mapping annotation terms to the proteins that carry them
4. Each term is inserted into the database as a separate annotation (duplicates are skipped)
5. If the response is paginated, it follows the pages automatically until all data is loaded

> **Note:** The `Update` button is only enabled when the annotation group has a URL configured.

---

## Usage
```python
from src.setup_utils.annotations_from_url.update_annotations import update_annotations_from_group_url

update_annotations_from_group_url(group, annotations_db)
```

---

## TSV Format

The URL must return a tab-separated file with at least two columns — the first being the protein ID, the second being semicolon-separated annotation terms.
```
protein_id    annotations
P12345        GO:0001;GO:0042
Q67890        GO:0001
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Update button is disabled | The group has no URL configured — set one first |
| `ValueError: URL did not return TSV` | Check the URL returns tab-separated data, not HTML or JSON |
| `ValueError: URL must return at least two columns` | The TSV must have a protein column and an annotation column |