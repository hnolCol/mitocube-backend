from typing import List, Optional
from pydantic import BaseModel, field_serializer

class API_UniprotAnnotationsModel(BaseModel):
    """
    BaseModel for downloading Uniprot Annotations.
    Cursor is required for pagination. (https://www.uniprot.org/help/pagination)
    """
    query : str 
    format : str = "tsv"
    size : int = 500
    fields : List[str] = [
        "accession",
        "protein_name",
        "gene_names",
        "gene_synonym",
        "length",
        "gene_primary",
        "sequence",
        "sequence_version",
        "go_c",
        "go_p",
        "go_f",
        "cc_function",
        "cc_domain",
        "ft_transit",
        "ft_signal",
        "ft_domain",
        "organism_id"
        ]
    #reviewed : bool = True
    cursor : Optional[str] = None
    compressed : Optional[bool] = True

    @field_serializer('fields')
    def serialize_fields(self,fields : list,*args,**kwargs):
        return ",".join(fields)
