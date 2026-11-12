import pandas as pd

from lib.data.runs.runs import RunListCreator


class _StubUser:
    tag = "abcd1234"
    firstname = "Jane"
    lastname = "Doe"


def _sample_list():
    return pd.DataFrame(
        {"attribute": [1, 1, 0, 0]},
        index=["20240101_kXeMa_a", "20240101_kXeMa_b", "20240101_kXeMa_c", "20240101_kXeMa_d"],
    )


def _plate(n_wells):
    return [[True] * n_wells]


def test_scramble_within_plates_preserves_plate_index():
    runlist = RunListCreator(
        dataset_label="subm-1234",
        sample_list=_sample_list(),
        free_plate_positions=[_plate(2), _plate(2)],
        user=_StubUser(),
        scramble=True,
        scramble_across_plates=False,
    ).create()

    assert len(runlist.runs) == 4
    assert all(run.plate_index in (0, 1) for run in runlist.runs)
    assert all(run.position for run in runlist.runs)
    assert sorted(run.measurement_index for run in runlist.runs) == [0, 1, 2, 3]


def test_scramble_across_plates_preserves_plate_index():
    runlist = RunListCreator(
        dataset_label="subm-1234",
        sample_list=_sample_list(),
        free_plate_positions=[_plate(2), _plate(2)],
        user=_StubUser(),
        scramble=True,
        scramble_across_plates=True,
    ).create()

    assert len(runlist.runs) == 4
    assert all(run.plate_index in (0, 1) for run in runlist.runs)
