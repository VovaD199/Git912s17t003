
import pytest
from data_normalizer import normalize_all_sources

def test_invalid_json_structure():
    invalid_data = {"wrong_key": []}
    with pytest.raises(Exception):
        normalize_all_sources(json_files=[invalid_data], csv_file=None)

def test_missing_fields():
    bad_json = {
        "quarter": "Q1",
        "months": [{}]
    }
    with pytest.raises(Exception):
        normalize_all_sources(json_files=[bad_json], csv_file=None)
