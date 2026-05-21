from fastapi import APIRouter, Depends
from typing import List
from collections import OrderedDict
import json 

from services.users import is_user_admin, get_user_from_token
from services.json import read_json 

from config.models.user import UserModel
from config.models.info.info import InfoResponse
from config.settings.general import get_general_settings
from config.settings.keyfigures import get_key_figure_settings

from lib.database.Database import Database 




from config.enums.states import SubmissionStatesEnums

GENERAL_SETTINGS  = get_general_settings()
KEY_FIGURE_SETTINGS = get_key_figure_settings()


DB = Database.DB()

router = APIRouter(
    prefix="/api",
    tags=["App Information"],
    )

# Statistical Metrics for Protein Differential Analysis

stats_markdown = """This module computes statistical and effect-size metrics to identify proteins that vary across experimental conditions.

Each metric captures a different aspect of the data:
- **Statistical significance** → are differences real?
- **Effect size** → how strong are the differences?
- **Biological relevance** → are the differences meaningful?
- **Data quality** → can we trust the measurement?

---

## 1. F-statistic (ANOVA)

**What it is:**
A ratio comparing variability **between groups** to variability **within groups**.

**Meaning:**
- High F → group means differ more than expected from random variation
- Low F → differences likely due to noise

**Intuition:**
> "Are the groups more different from each other than the variability inside them?"

**Important:**
- Does NOT tell how large the difference is
- Only indicates presence of differences

---

## 2. p-value

**What it is:**
Probability of observing the data (or more extreme) if there were **no real differences**.

**Meaning:**
- Small p-value → unlikely due to chance → statistically significant
- Large p-value → differences could be random

**Typical threshold:**
- **p < 0.05**

**Important caveat:**
- Large datasets can produce small p-values even for tiny effects

**Intuition:**
> "How surprised should we be by this result if nothing is actually happening?"

---

## 3. Eta Squared (η²)

**What it is:**
Proportion of total variance explained by group differences.

**Range:** 0 → 1

**Meaning:**
- 0 → groups explain nothing
- 1 → groups explain everything

**Interpretation:**

| Value | Effect |
|------|--------|
| 0.01 | Small |
| 0.06 | Medium |
| 0.14 | Large |

**Intuition:**
> "How much of the variation in this protein is actually driven by the conditions?"

---

## 4. Cohen’s f

**What it is:**
A standardized effect size derived from η².

**Why it matters:**
- Makes effect sizes comparable across experiments

**Interpretation:**

| Value | Effect |
|------|--------|
| 0.10 | Small |
| 0.25 | Medium |
| 0.40 | Large |

**Intuition:**
> "How strong is the effect in a standardized way?"

---

## 5. Max Pairwise Fold Change (log2)

**What it is:**
Largest difference between any two group means.

**Scale (log2):**

| Value | Fold Change |
|------|------------|
| 1    | 2× |
| 2    | 4× |

**Meaning:**
- Captures the strongest biological contrast

**Intuition:**
> "What is the biggest change this protein shows across conditions?"

---

## 6. Standard Deviation of Group Means

**What it is:**
Spread of average values across groups.

**Meaning:**
- High → groups differ widely
- Low → groups are similar

**Why useful:**
- More robust than max fold change
- Less sensitive to extreme values

**Intuition:**
> "How spread out are the condition averages overall?"

---

## 7. Missingness

**What it is:**
Fraction of missing observations.

**Range:** 0 → 1

| Value | Meaning |
|------|--------|
| 0    | Fully observed |
| 1    | Completely missing |

**Meaning:**
- High missingness → unreliable estimates

**Intuition:**
> "How much data do we actually have for this protein?"

---

## 8. Number of Groups (n_groups)

**What it is:**
Number of distinct condition groups.

**Meaning:**
- More groups → better representation of conditions
- Fewer groups → weaker statistical reliability

**Intuition:**
> "How many different conditions are we comparing?"

---

## 9. Composite Score

A combined metric to rank proteins by relevance:

\`\`\`math
score = η² × max_fold_change × log10(n_groups + 1)
\`\`\`

**What it captures:**
- **η²** → consistency of differences
- **Fold change** → magnitude of effect
- **n_groups** → diversity of conditions

**Meaning:**
- High score → strong, consistent, biologically meaningful variation

**Intuition:**
> "Is this protein consistently different, strongly changing, and across many conditions?"

---

## 10. Exclusive Proteins

**What it is:**
Proteins detected in only one condition.

**Meaning:**
- Cannot perform ANOVA
- Still biologically important

**Interpretation:**
- May indicate condition-specific expression

**Intuition:**
> "Does this protein appear only in a specific condition?"

---

## How to Use These Metrics

### Step 1: Filter Data
- Remove proteins with high missingness
- Ensure enough groups

### Step 2: Identify Strong Signals
Focus on:
- High η² → strong group effect
- High fold change → biological relevance

### Step 3: Check Significance
- Use p-value / F-statistic

### Step 4: Rank Proteins
- Use composite score

---

## Key Takeaways

- **p-value ≠ importance**
- **Effect size = biological relevance**
- **Best candidates have BOTH**

---

## Caveats

- ANOVA assumes:
  - Normal distribution
  - Similar variances
- Missing data can bias results
- Statistical significance does not guarantee biological importance

---
`;"""


@router.get("/info/app",summary="Returns basic information about the app.", response_model=InfoResponse)
def get_application_info(): #user : UserModel = Depends(get_user_from_token)
    """"""
    return InfoResponse(
        app_name=GENERAL_SETTINGS.app_name, 
        version=GENERAL_SETTINGS.version, 
        lead_contact=GENERAL_SETTINGS.lead_contact, 
        app_description=GENERAL_SETTINGS.description
        )



@router.get("/info/statistics/metrics",summary="Returns the defined key figures that are defined in the corresponding settings.")
def get_stat_metric_text(user : UserModel = Depends(get_user_from_token)) -> str:
    return stats_markdown


@router.get("/info/keyfigures",summary="Returns the key figures of the backend")
def get_keyfigures(user : UserModel = Depends(get_user_from_token)):
    """Returns the defined key figures that are defined 
    in the corresponding settings.

    Parameters
    ----------
    user : UserModel, optional
        the user that is inferred from the token, by default Depends(get_user_from_token)
    """
    
    
    key_figures = OrderedDict()
    if KEY_FIGURE_SETTINGS.number_submissions:
        key_figures["Submissions"] = len(DB.get_submission_tags())
    if KEY_FIGURE_SETTINGS.number_published_datasets:
        published_datasets = DB.submission_filter.find(state = [SubmissionStatesEnums.ACTIVE], limit = None)
        key_figures["Published Data"] = len(published_datasets)
    if KEY_FIGURE_SETTINGS.number_proteins:
        key_figures["Quantified Proteins"] = DB.proteins.count(quantified=True)
    if KEY_FIGURE_SETTINGS.number_genotypes:
        key_figures["Genotypes"] = DB.genotypes.count()
    if KEY_FIGURE_SETTINGS.number_users:
        key_figures["Users"] = DB.users.count()
    return [{"label" : k, "metric" : v} for k,v in key_figures.items()]



@router.get("/info/terms")
def get_terms_of_use(user : UserModel = Depends(get_user_from_token)):
    path_to_file = GENERAL_SETTINGS.use_terms_file 
    use_of_terms = read_json(path_to_file)
    return use_of_terms