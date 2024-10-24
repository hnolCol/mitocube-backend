import lib.data as dlib

from lib.rest.security import rest_verify_user_token, RestSessionInformation

from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/metatexts", tags=["Metatext"])

@router.get("/", summary="Returns the metatext configuration / information that can be used to describe a submission.")
def rest_get_meta_text(session: RestSessionInformation = Depends(rest_verify_user_token)):

    # ToDo: Hard copy, move to a configuration, but make it like a json Dict[tag, {title, placeholder, ...}]
    # Maybe make a database table, makes it easier to edit over time. plus information could be gathered with the other select for metatexts and provided

    return {"research_aim": {"title": "Research Aim",
                             "is_required": True,
                             "min_text_length": 100,
                             "max_text_length": 450,
                             "required_for_dataset_state": dlib.DatasetState.UPLOADED,  # ToDo: allow None here ( dlib.DatasetState | None)
                             "placeholder": "Enter background information about your project. Think about it like a small abstract in a paper."},
            "experimental_procedure": {"title": "Experimental Procedure",
                                       "is_tequired": True,
                                       "min_text_length": 50,
                                       "max_text_length": 450,
                                       "required_for_dataset_state": dlib.DatasetState.UPLOADED,
                                       "placeholder": "Provide detailed information about the experimental procedure/sample preparation."},
            "add_info": {"title": "Additional Information",  # Question: add could be confusing, change to extra_ or additional_?
                         "is_required": False,
                         "min_text_length": 0,
                         "max_text_length": 450,
                         "required_for_dataset_state": dlib.DatasetState.UPLOADED,
                         "placeholder": "Add additional information such as batch effects."},
            "protein_digestion": {"title": "Protein Digestion",
                                  "is_required": True,
                                  "min_text_length": 50,
                                  "max_text_length": 450,
                                  "required_for_dataset_state": dlib.DatasetState.PROCESSED,
                                  "placeholder": "Describe the protein digestion method."},
            "lcms": {"title": "Liquid Chromatography and Mass Spectrometry",
                     "is_required": True,
                     "min_text_length": 50,
                     "max_text_length": 450,
                     "required_for_dataset_state": dlib.DatasetState.MEASURING,
                     "placeholder": "Add information about the LC-MS/MS method."}
            }
