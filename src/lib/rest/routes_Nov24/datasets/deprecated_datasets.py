import time
from typing import Type, Dict, Any, List
from collections import OrderedDict
import warnings

from fastapi import APIRouter, Depends

import lib.data as dlib
import lib.data.sql.postgresql as psql

from lib.rest.security import RestPermissionSteward, RestSessionInformation

router = APIRouter(prefix="/api/datasets",tags=["Dataset", "Deprecated"])

def deprecated_api(message):  # ToDo: Replace with from warnings import deprecated; @deprecated with python 3.13
    warnings.warn(message, DeprecationWarning, stacklevel=2)


# parameter endpoints
# response_model=DatasetSubmissionResponseModel,
# tags=["Parameters" ,"Meta data"])
@router.get("/{dataset_label}/meta", deprecated=True)
def rest_get_dataset_full_details(dataset_label : str,  # deprecated, Todo: /dataset/{label}/meta Is it the same as /datasets/{dataset_label}/ or different?
                                  session: RestSessionInformation = Depends(RestPermissionSteward())):  # ToDo: Implement PRM
    ds: dlib.ABCDataset = dlib.ABCDataset.get_class()
    tv: Type[dlib.ABCTraitValue] = dlib.ABCTraitValue.get_class()

    dataset = ds.objectify_with_label(label=dataset_label)

    #### get all Traits for the Dataset
    try:
        dataset_traits: Dict[str, dlib.ABCTraitValue] = tv.objectify_with_dataset_id(db_id = dataset.get_internal_id())  # Dict[str, PostgreSQLTraitValue]
    except dlib.ABCAttributeError as err:
        dataset_traits: Dict[str, dlib.ABCTraitValue] = {}

    #### get a list of all Samples  # ToDo: Make new ABCSamples class
    sample_info = OrderedDict()
    db_conn = None
    try:  # ToDo: Outsource me to another Class (Change Feature Table), also Deprecated code !
        # if db_cur is None: # db_cur = db_cur_session # db_cur_session: psycopg2.cursor | None = None
        db_conn = psql.PostgreSQLConnection().getConnection()
        db_cur = db_conn.cursor()

        db_cur.execute("""SELECT sa.dataset_id, sa.id, sa.label, ba.batch_label, re.replicate_label 
                            FROM samples AS sa
                                LEFT JOIN sample_batches AS ba ON sa.id = ba.sample_id 
                                LEFT JOIN sample_replicates AS re ON sa.id = re.sample_id 
                            WHERE sa.dataset_id = %(dataset_id)s;""",
                       {"dataset_id": dataset.get_internal_id()})

        for db_row in db_cur.fetchall():
            sample_info[db_row[2]] = {"id": db_row[1],
                                      "label": db_row[2],
                                      "batch": db_row[3],
                                      "replicate": db_row[4]}

    finally:  # fixme: switch to psycopg 3 to be able to use with statements?
        if db_conn:
            psql.PostgreSQLConnection().returnConnection(db_conn)

    samples_traits: Dict[str, Dict[str, dlib.ABCTraitValue]] = {}
    #### collect all traits of the samples above
    for label, sample in sample_info.items():
        try:
            samples_traits[label] = tv.objectify_with_sample_id(sample_id = sample["id"])  # Dict[str, PostgreSQLTraitValue]
        except dlib.ABCAttributeError as err:
            samples_traits[label] = {}

    #### collect all traits and attributes from above dataset and samples
    attributes: Dict[str, dlib.ABCAttribute] = {}
    traits: Dict[str, dlib.ABCTrait] = {}

    for sample_label, trait_values in samples_traits.items():
        for trait_value in trait_values:
            if trait_value.get_trait().get_attribute().get_tag() not in attributes.keys():
                attributes[trait_value.get_trait().get_attribute().get_tag()] = trait_value.get_trait().get_attribute()
            if trait_value.get_trait().get_full_tag()not in traits.keys():
                traits[trait_value.get_trait().get_full_tag()] = trait_value.get_trait()

    ##### initialise variables for return values

    for_return_dataset_attributes: Dict[str, Dict[str, Any]] = {}
    for_return_dataset_traits: Dict[str, List[Dict[str, Any]]] = {}
    for_return_attribute_values_by_tag: Dict[str, Dict[str, Any]] = {}
    for_return_samples_attributes_by_sample: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for_return_samples_attributes: Dict[str, Dict[str, int]] = {}

    #### for_return_dataset_attributes
    for tag, attribute in attributes.items():
        for_return_dataset_attributes[tag] = {"att_organism": {"id": attribute.get_id(),
                                                               "tag": attribute.get_tag(),
                                                               "text": attribute.get_text(),
                                                               "priority": attribute.get_priority(),
                                                               "parent_id": attribute.get_parent_attribute().get_id() if attribute.get_parent_attribute() else None,
                                                               "parent_tag": attribute.get_parent_attribute().get_tag() if attribute.get_parent_attribute() else None,
                                                               "group_tag": attribute.get_text(),
                                                               "mandatory_for_submission": attribute.allowed_for_datasets(),
                                                               "mandatory_for_active": attribute.get_required_for_dataset_state() >= dlib.DatasetState.ACTIVE,
                                                               "has_features_value": attribute.are_trait_values_allowed(),
                                                               # Question, or False here?
                                                               "has_numeric_input": attribute.are_trait_values_allowed(),
                                                               "min_state": attribute.get_required_for_dataset_state(),
                                                               "allow_as_qc": attribute.allowed_for_performance(),
                                                               "allow_as_filter": attribute.allowed_as_filter(),
                                                               "allow_for_measurement": attribute.allowed_for_samples(),
                                                               "allow_for_genotype": attribute.allowed_for_genotypes(),
                                                               "allow_for_dataset": attribute.allowed_for_datasets(),
                                                               "allow_for_user": False,
                                                               "unit": None}}  # ToDo: check type format and continue here

    #### for_return_dataset_traits
    for full_tag, trait in traits.items():
        if trait.get_attribute().get_tag() not in for_return_dataset_traits.keys():
            for_return_dataset_traits[trait.get_attribute().get_tag()] = []

        for_return_dataset_traits[trait.get_attribute().get_tag()].append({"id": trait.get_id(),
                                                                           "attribute_id": trait.get_attribute().get_id(),
                                                                           "attribute_tag": trait.get_attribute().get_tag(),
                                                                           "text": trait.get_text(),
                                                                           "tag": trait.get_full_tag(),
                                                                           "value": trait_value.get_value() if trait_value.get_value() else None,
                                                                           "description": trait.get_description(),
                                                                           "feature": None})

    #### for_return_attribute_values_by_tag
    for full_tag, trait_value in dataset_traits.items():
        attribute = trait_value.get_trait().get_attribute()
        trait = trait_value.get_trait()

        if trait.get_full_tag() not in for_return_attribute_values_by_tag.keys():
            for_return_attribute_values_by_tag[trait.get_full_tag()] = {"id": trait.get_id(),
                                                                        "attribute_id": attribute.get_id(),
                                                                        "attribute_tag": attribute.get_tag(),
                                                                        "text": trait.get_text(),
                                                                        "tag": trait.get_full_tag(),
                                                                        "value": trait.get_tag(),  # Question, what is it used for?
                                                                        "description": trait.get_description(),
                                                                        "feature": None}  # Question, what is it used for?

    for sample, trait_values in samples_traits.items():
        for trait_value in trait_values:
            trait = trait_value.get_trait()
            attribute = trait.get_attribute()

            if trait.get_full_tag() not in for_return_attribute_values_by_tag.keys():
                for_return_attribute_values_by_tag[trait.get_full_tag()] = {"id": trait.get_id(),
                                                                            "attribute_id": attribute.get_id(),
                                                                            "attribute_tag": attribute.get_tag(),
                                                                            "text": trait.get_text(),
                                                                            "tag": trait.get_full_tag(),
                                                                            "value": trait.get_tag(),  # Question, what is it used for?
                                                                            "description": trait.get_description(),
                                                                            "feature": None}  # Question, what is it used for?


    #### for_return_samples_attributes_by_sample for_return_samples_attributes
    for label, sample in sample_info.items():
        for_return_samples_attributes_by_sample[label] = {}

        sample_traits = samples_traits[label]

        for trait_value in sample_traits:
            trait = trait_value.get_trait()
            attribute_tag = trait.get_attribute().get_tag()

            if attribute_tag not in for_return_samples_attributes_by_sample.keys():
                for_return_samples_attributes_by_sample[label][attribute_tag] = []

            for_return_samples_attributes_by_sample[label][attribute_tag].append({"id": trait.get_id(),
                                                                                  "attribute_id": trait.get_attribute().get_id(),
                                                                                  "attribute_tag": trait.get_attribute().get_tag(),
                                                                                  "text": trait.get_text(),
                                                                                  "tag": trait.get_full_tag(),
                                                                                  "value": trait.get_tag(),
                                                                                  "description": trait.get_description(),
                                                                                  "feature": None})

            if attribute_tag not in for_return_samples_attributes.keys():
                for_return_samples_attributes[attribute_tag] = {}

            if trait.get_full_tag() not in for_return_samples_attributes[attribute_tag].keys():
                for_return_samples_attributes[attribute_tag][trait.get_full_tag()] = []

            for_return_samples_attributes[attribute_tag][trait.get_full_tag()].append(list(sample_info.keys()).index(label))


    #### create timeline

    tl: Type[dlib.ABCTimeline] = dlib.ABCTimeline.get_class()
    timeline: List[dlib.ABCDatasetTimelineEvent] = tl.objectify_with_dataset_id(dataset_id=dataset.get_internal_id())

    for_return_timeline = {"label": dataset.get_external_id(),
                           "created_on": time.mktime(dataset.get_created_on_date().timetuple()),
                           "modified_on": time.mktime(max([timeline_event.get_timestamp() for timeline_event in timeline]).timetuple()),
                           "entries": [{"id": timeline_event.get_id(),
                                        "label": str(timeline_event.get_id()),
                                        "created_on": time.mktime(timeline_event.get_timestamp().timetuple()),
                                        "user_id": timeline_event.get_user().get_id() if timeline_event.get_user() else None,
                                        "user_label": timeline_event.get_user().get_username() if timeline_event.get_user() else None,
                                        "username": timeline_event.get_user().get_username() if timeline_event.get_user() else None,
                                        "event_state": timeline_event.get_state(),
                                        "state": timeline_event.get_type(),
                                        "type": timeline_event.get_type(),
                                        "comment": timeline_event.get_state()} for timeline_event in timeline]}

    #### Finally
    return {"id": dataset.get_internal_id(),
            "label": dataset.get_external_id(),
            "title": dataset.get_title(),
            "state": int(dataset.get_state()),
            "user_id": dataset.get_owner().get_id(),
            "username": dataset.get_owner().get_username(),
            "user_label": dataset.get_owner().get_username(),  # deprecated, use username instead
            "collaborators": [],  # ToDo: Check what to fill in
            "created_on": time.mktime(dataset.get_created_on_date().timetuple()) if dataset.get_created_on_date() else None,
            "modified_on": for_return_timeline["modified_on"],
            "metatext": {m.get_tag(): m.get_text() for tag, m in dataset.get_metatexts().items()} if dataset.get_metatexts() else {},
            "links" : [url.get_url() for url in dataset.get_urls()] if dataset.get_urls() else [],  # deprecated, use url instead
            "urls": [url.get_url() for url in dataset.get_urls()] if dataset.get_urls() else [],
            "contact_email": dataset.get_email(),  # NEW
            "runlist": None,  # ToDo: Implement, and counter check what is it about in detail
            "project_id": dataset.get_parent_project().get_id() if dataset.get_parent_project() else None,  # NEW Todo: implement project rest api first
            "instrument_id": dataset.get_instrument().get_id() if dataset.get_instrument() else None,  # NEW
            "dataset_attributes": for_return_dataset_traits,
            "timeline": for_return_timeline,
            "n_samples": len(sample_info),
            "sample_names": list(sample_info.keys()),
            "replicates": [sample["replicate"] for label, sample in sample_info.items()],
            "batches": [sample["batch"] for label, sample in sample_info.items()],
            "samples_attributes": for_return_samples_attributes,
            "samples_attributes_by_sample": for_return_samples_attributes_by_sample,
            "attributes": for_return_dataset_attributes,
            "attribute_values_by_tag": for_return_attribute_values_by_tag,
            "genotypes": {},
            "samples_genotypes": {}
            # "samples_genotypes": {"kuIIP": [0, 1, 2, 3, 4, 5],
            #                       "qGgte": [6, 7, 8, 9, 10, 11]},
            # "genotypes": {"kuIIP": {"label": "kuIIP",
            #                         "text": "Clpb.KO.V182-E215del.V216fs.(+/+)",
            #                         "proteome_id": "UP000000589",
            #                         "features": [{"key": "Q60649",
            #                                       "tag": None,
            #                                       "genes": "Clpb Skd3",
            #                                       "proteins": "dfdsfs",
            #                                       "organism": "Mus musculus (Mouse)",
            #                                       "aa_length": 677,
            #                                       "reviewed": True }],
            #                         "attributes": [{"att_protein_coding_sequence": [{"key": "Q60649",
            #                                                                          "tag": None,
            #                                                                          "genes": "Clpb Skd3",
            #                                                                          "proteins": "Mitochondrial disaggregase (EC 3.6.1.-) (Suppressor of potassium transport defect 3) [Cleaved into: Mitochondrial disaggregase, cleaved form]",
            #                                                                          "organism": "Mus musculus (Mouse)",
            #                                                                          "aa_length": 677,
            #                                                                          "reviewed": True}]
            #                                         }]
            #                         }
            #               }
            }
