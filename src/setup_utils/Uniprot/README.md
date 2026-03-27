# Annotation Pipeline

A Python script that fetches protein annotation data from a remote URL and uploads it to your annotation database. Handles pagination and compressed responses automatically.

---

## Prerequisites

- Python 3.7+
- Access to a running annotation API
- A valid annotation group

### Install dependencies
```bash
pip3 install pandas requests
```

---

## How It Works

The script fetches a TSV file from a URL you configure on your annotation group. It then:

1. Reads the TSV — first column is the protein ID, second column is the annotation terms (semicolon-separated)
2. Builds a map of **term -> list of proteins**
3. Uploads one annotation per term to the database
4. Automatically follows pagination if the data is split across multiple pages

### TSV Format Expected

| Column | Description |
|---|---|
| First | Protein identifier (e.g. UniProt ID) |
| Second | Semicolon-separated annotation terms (e.g. `GO:0001;GO:0042`) |

Example:
```
protein_id    annotations
P12345        GO:0001;GO:0042
Q67890        GO:0001
```

---

## Setup

#

---

## Expected Output
```
Processed 500 rows
Processed 1000 rows
```

Each line means one page of data was fetched and processed. The script keeps going until all pages are done.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `ValueError: Annotation group has no URL` | Make sure `group.url` is set before calling the function |
| `ValueError: URL did not return TSV` | Check the URL is returning tab-separated data, not HTML or JSON |
| `ValueError: URL must return at least two columns` | The TSV must have at least a protein column and an annotation column |