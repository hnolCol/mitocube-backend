from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

import lib.data as dlib


class DatasetSampleError(dlib.ABCDataError):
    pass

class DatasetSample:
    def __init__(self, dataset: dlib.ABCDataset, label: str, db_id: int | None = None,
                 batch_labels: List[str] | None = None, replicate_labels: List[str] | None = None):
        self._db_id: int | None = db_id
        self._dataset: dlib.ABCDataset = dataset
        self._label: str = label
        self._batch_labels: List[str] | None = batch_labels
        self._replicate_labels: List[str] | None = replicate_labels

    def add_batch_label(self, label):
        if self._batch_labels is None:
            self._batch_labels = []

        self._batch_labels.append(label)

    def add_replicate_label(self, label):
        if self._replicate_labels is None:
            self._replicate_labels = []

        self._replicate_labels.append(label)

    def get_id(self) -> int | None:
        return self._db_id

    def get_dataset(self) -> dlib.ABCDataset:
        return self._dataset

    def get_label(self) -> str:
        return self._label

    def get_batch_labels(self) -> List[str] | None:
        return self._batch_labels

    def get_merged_batch_label(self, delimiter: str = "_"):
        return delimiter.join(sorted(self._batch_labels))

    def get_replicate_labels(self) -> List[str] | None:
        return self._replicate_labels

    def get_merged_replicate_label(self, delimiter: str = "_"):
        return delimiter.join(sorted(self._replicate_labels))

    def set_id(self, db_id: int | None):
        self._db_id: int | None = db_id


class ABCSamples(ABC, dlib.FlexDataClass):
    def __init__(self, samples: List[DatasetSample] | None = None):
        self._samples = samples

    def add_sample(self, sample: DatasetSample):
        if self._samples is None:
            self._samples = []

        self._samples.append(sample)

    def add_samples(self, samples: List[DatasetSample]):
        if self._samples is None:
            self._samples = []

        self._samples.extend(samples)

    def construct_and_add_samples(self, dataset: dlib.ABCDataset,  labels: List[str],
                                  batches: Dict[str, List[str]],  # Sample name and batch labels / replicate labels
                                  replicates: Dict[str, List[str]]) -> List[DatasetSample]:

        new_samples = [DatasetSample(dataset = dataset, label = label , db_id = None,
                                     batch_labels = batches[label] if label in batches else None,
                                     replicate_labels = replicates[label] if label in replicates else None) for label in labels]

        if self._samples is None:
            self._samples = []

        self._samples.extend(new_samples)

        return new_samples

    @abstractmethod
    def write_to_db(self):
        pass

    @staticmethod
    @abstractmethod
    def objectify_by_dataset_id(dataset_id: int) -> ABCSamples:
        pass

    @staticmethod
    @abstractmethod
    def objectify_by_dataset_label(label: str) -> ABCSamples:
        pass

    @staticmethod
    @abstractmethod
    def objectify_by_feature(feature_label: str) -> ABCSamples:
        pass
