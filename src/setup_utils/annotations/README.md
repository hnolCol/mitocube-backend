# MitoCarta Annotation Uploader

A collection of Python scripts that read data from the **MitoCarta3.0** Excel file and upload annotations to your API. Each script groups proteins differently depending on what you want to annotate.

---

## Scripts

| Script | Groups proteins by | Column used |
|---|---|---|
| `upload_pathways.py` | Metabolic pathway | `MitoCarta3.0_MitoPathways` |
| `upload_localization.py` | Sub-mitochondrial localization | `MitoCarta3.0_SubMitoLocalization` |

Both scripts work the same way, they just group proteins by a different column.

---

## Prerequisites

- Python 3.7+
- Access to the [MitoCarta3.0 Excel file]
- A running annotation API endpoint at a known base URL
- A valid Token for the API

### Install dependencies
```bash
pip3 install pandas requests openpyxl
```

---

## Setup

### 1. Navigate to the backend directory

Before running any script, make sure you are in the `mitocue-backend` directory:
```bash
cd path/to/mitocue-backend
```

> All scripts must be run from this directory.

### 2. Configure the script

Open whichever script you want to run and update these variables at the top:
```python
base_url         = "http://localhost:5002/api/annotations/"   # Your API base URL
Token            = "your_Token_here"                          # Your Bearer token
annotatiion_file = "path_to_your/MitoCarta3.0.xlsx"           # Path to Excel file
group_tag        = "enter_your_group_tag_here"                # Your annotation group tag
```

---

## Running the Scripts

Make sure you are in the `mitocue-backend` directory first, then run:
```bash
# Upload pathway annotations
python3 /src/setup_utils/annotations/mitocarta_pathways_from_file.py

# Upload localization annotations
python3 /src/setup_utils/annotations/mitocarta_localization_from_file.py
```

### Expected output
```
Uploading OXPHOS > Complex I (45 proteins)
Status: 200
Uploading Inner membrane (60 proteins)
Status: 200
```

A `200` status means the annotation was created successfully.

---

## How It Works

Both scripts follow the same logic:

1. Load the `A Human MitoCarta3.0` sheet from the Excel file
2. For each row, extract the `UniProt` ID and the relevant grouping column
3. Split the column on `|` since proteins can belong to multiple groups
4. Build a map of group -> list of UniProt IDs
5. POST one annotation per group to the API

### API Payload
```json
{
  "text": "OXPHOS > Complex I",
  "description": "OXPHOS > Complex I",
  "group_tag": "your_group_tag",
  "protein_tags": ["P03886", "O75306", "Q16718"]
}
```

---

## Notes

- Proteins can appear in multiple annotations since the columns are pipe-separated (`|`)

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `401 Unauthorized` | Check your `Token` value |
| `404 Not Found` | Confirm `base_url` is correct and API is running |
| `FileNotFoundError` | Update `annotatiion_file` to the correct path |
| `KeyError: 'UniProt'` | Confirm the sheet name and column headers match |
| `ModuleNotFoundError` | Run `pip3 install pandas requests openpyxl` |