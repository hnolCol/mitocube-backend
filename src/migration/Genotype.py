from pydantic import BaseModel
from typing import List, Literal 
import time 
# [
#     {
#         "label": "PSpVW",
#         "text": "DNAJC15-KO(+/+)",
#         "proteome_id": "UP000005640",
#         "features": [
#             {
#                 "key": "Q9Y5T4",
#                 "genes": "DNAJC15 DNAJD1 GIG22 HSD18",
#                 "proteins": "DnaJ homolog subfamily C member 15 (Cell growth-inhibiting gene 22 protein) (Methylation-controlled J protein) (MCJ)",
#                 "organism": "Homo sapiens (Human)",
#                 "aa_length": 150,
#                 "reviewed": true
#             }
#         ],
#         "attributes": [
#             {
#                 "att_protein_coding_sequence": [
#                     {
#                         "key": "Q9Y5T4",
#                         "genes": "DNAJC15 DNAJD1 GIG22 HSD18",
#                         "proteins": "DnaJ homolog subfamily C member 15 (Cell growth-inhibiting gene 22 protein) (Methylation-controlled J protein) (MCJ)",
#                         "organism": "Homo sapiens (Human)",
#                         "aa_length": 150,
#                         "reviewed": true
#                     }
#                 ],
#                 "att_gene_engineering": [
#                     {
#                         "id": 344,
#                         "attribute_id": 48,
#                         "text": "Knockout",
#                         "tag": "att_gene_engineering:ko",
#                         "value": "ko",
#                         "description": "Gene knock out."
#                     }
#                 ],
#                 "att_gene_zygosity": [
#                     {
#                         "id": 348,
#                         "attribute_id": 49,
#                         "text": "Wildtype (+/+)",
#                         "tag": "att_gene_zygosity:(+/+)",
#                         "value": "(+/+)",
#                         "description": "Wildtype"
#                     }
#                 ],
#                 "att_gene_editing_method": [
#                     {
#                         "id": 336,
#                         "attribute_id": 47,
#                         "text": "CRISPR-mediated",
#                         "tag": "att_gene_editing_method:crispr",
#                         "value": "crispr",
#                         "description": "A CRISPR-associated (Cas) enzyme is used to cleave target DNA, resulting in a double-strand break (DSB). The Cas enzyme is directed by the guide RNA (gRNA) to a user-defined site in the genome, and then the Cas enzyme cuts the DNA."
#                     }
#                 ],
#                 "att_protein_mutation": [
#                     {
#                         "id": 700,
#                         "attribute_id": 86,
#                         "text": "Frameshift",
#                         "tag": "att_protein_mutation:frameshift",
#                         "value": "frameshift",
#                         "description": "Frameshift mediated by a double strand break"
#                     }
#                 ],
#                 "att_protein_position": {
#                     "att_protein_mutation:frameshift": {
#                         "attribute_value": {
#                             "id": 713,
#                             "attribute_id": 87,
#                             "text": "Region",
#                             "tag": "att_protein_position:region",
#                             "value": "region",
#                             "description": "Protein region defined by a start and stop amino acid. Use this for truncation or gRNA target sequences."
#                         },
#                         "aa_position": [
#                             3,
#                             7
#                         ]
#                     }
#                 }
#             }
#         ]
#     },


class ProteinMutation(BaseModel):
    id : int 
    tag : Literal["att_protein_mutation:frameshift","att_protein_mutation:flag","att_protein_mutation:insertion","att_protein_mutation:truncation","att_protein_mutation:none","att_protein_mutation:gfp"]
    start : int|None #amino acid start,is always given in C-term direction, for N-term tag for example give 0, for C-term the end amino acid sequence, please note that is not the index and starts at 1 not at 0.  can only be  nOne, it tag is "att_protein_mutation:none"
    end : int|None #amino acid end 
    sequence : str|None #amino acids to be added or substituted (e.g. insertion or substitution)
    
class GeneModificationModel(BaseModel):
    tag : str #feature tag (e.g. Uniprot ID )
    zygosity : Literal["att_gene_zygosity:(+/+)","att_gene_zygosity:(-/+)","att_gene_zygosity:(-/-)","att_gene_zygosity:unknown"] #traits from att_gene_zygosity 
    gene_engineering : Literal["att_gene_engineering:ko","att_gene_engineering:ki"] #traits from att_gene_engineering 
    editing_method : Literal["att_gene_editing_method:crispr","att_gene_editing_method:biggybac"] #traits from att_gene_editing_method 
    mutations : List[ProteinMutation]
    

class GenotypeModel(BaseModel):
    id : int 
    created_at : int #timestamp 
    tag : str 
    text : str 
    description : str|None 
    publication : str|None #pubmed id 
    user_tag : str|None # user who created the genotype 
    feature_tags : List[str] #list of uniprot ids of the features that are affected by the genotype 
    proteome_tags : List[str] #list of proteomes that are affected, for example it might be a ko in a human cellline, but re-epxressing a mouse protein, this info could be retireved by the features itself 
    gene_modifications : List[GeneModificationModel]
    
    
    

g = GenotypeModel(
    id = 1,
    created_at= time.time(),
    tag = "asd23sd", #previous named label 
    text = "FLAG.DNAJC15.GFP", # following the protein mod convention 
    description = "DNAJC15 is part of the TIM23 translocase. Here the protein was tagged N-terminal with flag and c-terminal with GFP endogenously ",
    feature_tags = ["Q9Y5T4"],
    zygosity="att_gene_zygosity:(-/-)", #do we need zygosity per feature?
    proteome_tags = ["UP000005640"],
    gene_modifications= [
        GeneModificationModel(
            tag = "Q9Y5T4",
            zygosity = "att_gene_zygosity:(+/+)",
            gene_engineering="att_gene_engineering:ki",
            editing_method="att_gene_editing_method:crispr",
            mutations=[
                ProteinMutation(
                    id = 1,
                    tag="att_protein_mutation:flag",
                    start = -1 
                ),
                ProteinMutation(
                    id = 2,
                    tag="att_protein_mutation:flag",
                    start = 150
                )
            ]
        )
    ]
)


g = GenotypeModel(
    id = 1,
    created_at= time.time(),
    tag = "asd23sd", #previous named label 
    text = "DNAJC15.18fs.(-/-) DNAJC15.Y19-L20del", # following the protein mod convention 
    description = "DNAJC15 is part of the TIM23 translocase. Here the a protein truncated by two amino acids at position 19 and 20 is expressed in a knockout background.",
    feature_tags = ["Q9Y5T4"],
    proteome_tags = ["UP000005640"],
    gene_modifications= [
        #define KO first 
        GeneModificationModel(
            tag = "Q9Y5T4",
            zygosity = "att_gene_zygosity:(-/-)",
            gene_engineering="att_gene_engineering:ko",
            editing_method="att_gene_editing_method:crispr",
            mutations=[
                ProteinMutation(
                    id = 1,
                    tag="att_protein_mutation:frameshift",
                    start = 12
                )
            ]
        ),
        #define reexpression of mutated protein 
        GeneModificationModel(
            tag = "Q9Y5T4",
            zygosity = "att_gene_zygosity:unknwon", #random integration of gene copies 
            gene_engineering="att_gene_editing_method:biggybac",
            editing_method="att_gene_editing_method:biggybac",
            mutations=[
                ProteinMutation(
                    id = 1,
                    tag="att_protein_mutation:truncation",
                    start = 18, #because the  position is C-term!! 
                    end = 20 
                )
            ]
        )
    ]
)
    
    