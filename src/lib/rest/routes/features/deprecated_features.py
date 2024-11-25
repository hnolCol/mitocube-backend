from typing import Any, Dict, List, Type
import warnings

import lib.data as dlib
import lib.data.sql.postgresql as psql

import psycopg2

from fastapi import APIRouter, Depends, HTTPException, status

from lib.rest.security import RestPermissionSteward, RestSessionInformation


router = APIRouter(prefix="/api/features",
                   tags=["Features", "Deprecated_api"])

def deprecated_api(message):  # ToDo: Replace with from warnings import deprecated; @deprecated with python 3.13
    warnings.warn(message, DeprecationWarning, stacklevel=2)



@router.get("/{feature_key}/data", deprecated=True)  # ToDo Implement PRM, response_model=FeatureDataResponseModel)
def rest_get_dataset_data_by_feature(feature_key: str,  # Deprecated, implement /api/datasets/data/{feature_key}
                                     max_datasets: int = 200,  # Deprecated max_datasets, use limit_to_n instead
                                     limit_to_n: int = 200,
                                     limit_offset: int = 0,
                                     session: RestSessionInformation = Depends(RestPermissionSteward())):
    deprecated_api("called deprecated function rest_get_dataset_data_by_feature(...)")

    # at: Type[dlib.ABCAttribute] = dlib.ABCAttribute.get_class()
    # tr: Type[dlib.ABCTrait] = dlib.ABCTrait.get_class()
    tv: Type[dlib.ABCTraitValue] = dlib.ABCTraitValue.get_class()
    db: Type[dlib.ABCDatabase] = dlib.ABCDatabase.get_class()
    ds: Type[dlib.ABCDataset] = dlib.ABCDataset.get_class()

    dataset_ids, dataset_labels = db.query_datasets_ids(feature_keys = [feature_key],
                                                        # states = [dlib.DatasetState.ACTIVE],  # Fixme, remove comment if you are done!
                                                        limit_to_n = limit_to_n,
                                                        limit_offset = limit_offset)

    # ToDo / Fixme: Implement argument to not catch the data here, or only selected features / proteins
    datasets: Dict[str, dlib.ABCDataset] = {dataset_labels[ix]: ds.objectify_with_id(db_id=dataset_ids[ix]) for ix in range(len(dataset_ids))}

    attributes: Dict[int, dlib.ABCAttribute] = {}  # at.get_all_attributes()  # Dict[int, PostgreSQLAttribute]
    traits: Dict[int, dlib.ABCTrait] = {}  # tr.get_all_traits()

    dict_dataset_data: Dict[str, List[Dict[str, Any]]] = {}  # Deprecated !!!
    for_return_samples_attributes: Dict[str, Dict[str, List[str]]] = {}  # Deprecated !!!
    for_return_samples_attributes_by_sample: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}  # Deprecated !!!

    for dataset_label, dataset in datasets.items():
        for_return_samples_attributes[dataset_label] = {}
        dict_dataset_data[dataset_label] = []

        try:
            sample_traits = tv.objectify_sample_trait_values_with_dataset_id(dataset_id=dataset.get_internal_id())
        except dlib.ABCTraitValueNotFoundError:
            # No Grouping / Attribute & Traits saved for the samples --> skip it since no grouping
            continue

        # This part below to END is mostly deprecated code that can be received differently / better
        for sample_label, trait_values in sample_traits.items():  # Deprecated !!!
            for_return_samples_attributes_by_sample[sample_label] = {}

            for trait_value in trait_values:
                trait = trait_value.get_trait()
                attribute_tag = trait.get_attribute().get_tag()

                if trait.get_attribute().get_id() not in attributes.keys():
                    attributes[trait.get_attribute().get_id()] = trait.get_attribute()

                if trait.get_id() not in traits.keys():
                    traits[trait.get_id()] = trait

                if attribute_tag not in for_return_samples_attributes[dataset_label].keys():
                    for_return_samples_attributes[dataset_label][attribute_tag] = []

                if trait.get_full_tag() not in for_return_samples_attributes[dataset_label][attribute_tag]:
                    for_return_samples_attributes[dataset_label][attribute_tag].append(trait.get_full_tag())

                if attribute_tag not in for_return_samples_attributes_by_sample[sample_label].keys():
                    for_return_samples_attributes_by_sample[sample_label][attribute_tag] = []

                for_return_samples_attributes_by_sample[sample_label][attribute_tag].append({"id": trait.get_id(),
                                                                                             "attribute_id": trait.get_attribute().get_id(),
                                                                                             "attribute_tag": attribute_tag,
                                                                                             "text": trait.get_text(),
                                                                                             "tag": trait.get_full_tag(),
                                                                                             "value": trait_value.get_value() if trait_value.get_value() else trait.get_tag(),
                                                                                             "description": trait.get_description(),
                                                                                             "feature": None})
        # END of deprecated code

        db_conn = None
        try:  # ToDo: Outsource me to another Class (Change Feature Table), also Deprecated code !
            # if db_cur is None: # db_cur = db_cur_session # db_cur_session: psycopg2.cursor | None = None
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("""SELECT s.id AS sample_id, s.label AS sample, 
                                    v.feature_id, f.label AS accession, f.is_grouped, f.proteome_id, 
                                    v.feature_value AS intensity 
                                FROM samples AS s  ---- (SELECT * FROM samples WHERE dataset_id = %(dataset_id)s) AS s  ---- ToDo: Rearrange order
                                    LEFT JOIN feature_pg_values AS v ON s.id = v.sample_id  ---- (SELECT * FROM feature_pg_values WHERE dataset_id = %(dataset_id)s) AS v
                                    LEFT JOIN feature_pgs AS f ON v.feature_id = f.id 
                                WHERE v.dataset_id = %(dataset_id)s AND f.label = %(feature_accession)s;""",
                           # ToDo: or s.dataset_id = <xyz> ? v.dataset_id should be faster, maybe with sub-select first
                           {"dataset_id": dataset.get_internal_id(),
                            "feature_accession": feature_key})

            db_rows = db_cur.fetchall()

            # 00 sample_id # 01 sample # 02 feature_id  # 03 accession # 04 is_grouped # 05 proteome_id # 06 intensity
            for db_row in db_rows:
                row_obj = {"index": db_row[1], "value": db_row[6]}

                if db_row[1] not in for_return_samples_attributes_by_sample.keys():
                    continue  # Bug, this scenario makes the frontend go bye bye ( i think this happens if no grouping / no trait , or all are the same, exist for the sample)
                for attribute_tag, items in for_return_samples_attributes_by_sample[db_row[1]].items():
                    for item in items:
                        row_obj[attribute_tag] = item["tag"]  # Bug: Dirty Solution for now, issue if attributes with multiple traits occurre!

                dict_dataset_data[dataset_label].append(row_obj)
        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    return {"feature_key": feature_key,
            "title_by_label": {label: dataset.get_title() for label, dataset in datasets.items()},
            "dataset_ids": dataset_ids,
            "dataset_labels": dataset_labels,
            "genotypes_by_label": {label: {} for label, dataset in datasets.items()},  # ToDo: Implement Genotype
            "data": dict_dataset_data,  # Deprecated !!! Should be in a different format!
            "samples_attributes_by_sample": for_return_samples_attributes_by_sample,  # Deprecated: Redundant, covered by 'samples_attributes' and 'data' already?! # Fixme: Issue if two samples with same name!
            "samples_attributes": for_return_samples_attributes,  # Deprecated: Redundant, covered by 'samples_attributes_by_sample' and 'data' already?!
            "attributes": {attribute.get_tag(): {"id": db_id,  # Deprecated, should not be needed here
                                                 "tag": attribute.get_tag(),
                                                 "text": attribute.get_text(),
                                                 "priority":attribute.get_priority(),
                                                 "parent_id": attribute.get_parent_attribute().get_id() if attribute.get_parent_attribute() else None,
                                                 "parent_tag": attribute.get_parent_attribute().get_id() if attribute.get_parent_attribute() else None,
                                                 "group_tag": "None",  # Deprecated? Implement id version with nm table
                                                 "mandatory_for_submission": attribute.get_required_for_dataset_state() >= dlib.DatasetState.UPLOADED,  # Deprecated, is it not covered by min state?  # ToDo: Check
                                                 "mandatory_for_active": attribute.get_required_for_dataset_state() >= dlib.DatasetState.ACTIVE,  # Deprecated, is it not covered by min state?
                                                 "has_features_value": False,  # Question, check solution
                                                 "has_numeric_input": False,  # Question, check solution
                                                 "min_state": attribute.get_required_for_dataset_state(),
                                                 "unit": None,  # Deprecated! belongs to ABCTrait
                                                 "allow_as_qc": attribute.allowed_for_performance(),
                                                 "allow_as_filter": attribute.allowed_as_filter(),
                                                 "allow_for_measurement": attribute.allowed_for_samples(),
                                                 "allow_for_genotype": attribute.allowed_for_genotypes(),
                                                 "allow_for_dataset": attribute.allowed_for_datasets(),
                                                 "allow_for_user": False} for db_id, attribute in attributes.items()},  # Deprecated: Redundant, why needed here?
            "attribute_values_by_tag": {trait.get_full_tag(): {"id": db_id,
                                                               "attribute_id": trait.get_attribute().get_id(),
                                                               "attribute_tag": trait.get_attribute().get_tag(),
                                                               "text": trait.get_text(),
                                                               "tag": trait.get_full_tag(),
                                                               "value": trait.get_tag(),  # Deprecated! Does not belong here
                                                               "description": trait.get_description(),
                                                               "feature": None} for db_id, trait in traits.items()}  # Deprecated: Redundant, why needed here?
            }

