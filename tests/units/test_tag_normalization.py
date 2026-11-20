import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from services.tags import normalize_tag_text


@pytest.mark.parametrize("text,expected", [
    ("brain region", "brain_region"),
    ("Brain Region", "brain_region"),
    ("%", "perc"),
    ("50%", "50_perc"),
    ("10 µM", "10_um"),
    ("+", "plus"),
    ("SIRT3 overexpression", "sirt3_overexpression"),
    ("> 5 fold", "gt_5_fold"),
    ("< 2%", "lt_2_perc"),
    ("N & C-term", "n_and_c_minus_term"),
    ("glucose 6-phosphate", "glucose_6_minus_phosphate"),
    ("30°C", "30_deg_c"),
    ("mM (100)", "mm_100"),
    ("[NaCl]", "nacl"),
    ("...", ""),
])
def test_normalize_tag_text(text, expected):
    assert normalize_tag_text(text) == expected
