from config.models.consortium import ConsortiumInput, ConsortiumModel
import pytest


def test_consortium_input_requires_mandatory_fields():
    with pytest.raises(Exception):
        ConsortiumInput()


def test_consortium_input_accepts_valid_data():
    c = ConsortiumInput(
        text="Mitochondrial Research Consortium",
        abbreviation="MRC",
        email="consortium@example.org",
    )
    assert c.text == "Mitochondrial Research Consortium"
    assert c.profile_text is None
    assert c.url is None


def test_consortium_input_rejects_invalid_email():
    with pytest.raises(Exception):
        ConsortiumInput(
            text="Mitochondrial Research Consortium",
            abbreviation="MRC",
            email="not-an-email",
        )


def test_consortium_model_roundtrip():
    c = ConsortiumModel(
        tag="cons-1",
        text="Mitochondrial Research Consortium",
        abbreviation="MRC",
        email="consortium@example.org",
    )
    dumped = c.model_dump(exclude_none=True)
    assert dumped["tag"] == "cons-1"
    assert "profile_text" not in dumped
