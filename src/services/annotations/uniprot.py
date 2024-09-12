import os 
import requests 
from typing import List, Dict, Optional
#internal imports 
from config.models.annotations.proteome import ProteomeModel
from config.models.annotations.uniprot import API_UniprotAnnotationsModel

from ..ftp import list_ftp_directory, downloadFileFromFTP
from services.paths.utils import getPathToResources, check_dir_exists
from services.read_text import tsv_string_to_dataframe
from services.regex import get_cursor_from_header_link
from pydantic import BaseModel
import pandas as pd 
import zipfile 
import gzip
import zlib
from io import StringIO, BytesIO
#https://rest.uniprot.org/uniprotkb/search?compressed=true&fields=accession%2Creviewed%2Cid%2Cprotein_name%2Cgene_names%2Corganism_name%2Clength%2Cgo_p%2Cgo_c%2Cgo_f&format=tsv&query=%28%28proteome%3AUP000005640%29%29&size=500

def download_proteome_annotations(annotationUrl : str,
                                  proteome_tags : List[str],
                                  apiParamModel : BaseModel = API_UniprotAnnotationsModel,
                                  add_proteome_callback = None,
                                  reviewed : bool = False,
                                  user_tag : str = None,
                                  chunc_callback = None) -> pd.DataFrame:
    """
    Download annotations from Uniprot Server using proteome upid. 
    The function utilizes pagination (e.g. downloads sets of 500 entries per API get request)
    and merges them into a pandas dataframe. 
    Settings for the API call and fields are defined in the apiParamModel BaseModel 
    """
    N = 0
    ##get proteome information 
    #check proteome exists 
    for proteome_tag in proteome_tags:
        proteome_info = requests.get(f"https://www.ebi.ac.uk/proteins/api/proteomes?offset=0&size=1&upid={proteome_tag}")
        uniprot_proteome_info = proteome_info.json()
        if len(uniprot_proteome_info) == 0:
            raise ValueError("The proteome was not found in the Uniprot database. ")
        elif add_proteome_callback is not None:
            add_proteome_callback(proteome_tag, uniprot_proteome_info[0])
        uniprot_query = f"((proteome:{proteome_tag}) AND (reviewed:true))" if reviewed else f"(proteome:{proteome_tag})"
        apiParams = apiParamModel(query=uniprot_query)
        rr = requests.get(annotationUrl,params=apiParams.model_dump())
        rr.raise_for_status()
        # Extract the zip file
        proteome_entries = tsv_string_to_dataframe(gzip.decompress(rr.content))
        chunc_callback(proteome_entries,proteome_tag,user_tag)
        N += proteome_entries.index.size
    # result.append(tsv_string_to_dataframe(gzip.decompress(rr.content)))
        while "Link" in rr.headers: #if there is no link in the response, last page is reached.
            print("Found link, going to next page.")
            headers = rr.headers
            #get pointer from headers
            try:
                pointerFromHeaderLink = get_cursor_from_header_link(headers["link"])
            except Exception as e:
                raise Exception(f"There was an error extracting the cursor from header link.  {headers['link']}. "+str(e))
                
            updatedApiParams = apiParams.model_copy(update={"cursor" : pointerFromHeaderLink})
            #get cursor for next link
            rr = requests.get(annotationUrl,params=updatedApiParams.model_dump())
            
            if chunc_callback is not None:
                proteome_entries = tsv_string_to_dataframe(gzip.decompress(rr.content))
                chunc_callback(proteome_entries, proteome_tag,user_tag)
                N += proteome_entries.index.size
            print(f"{N} proteins added.")
    return N


def downloadRecentProteomeFasta(proteome : ProteomeModel,
                                domain : str = "ftp.uniprot.org",
                                path : str = "/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes"):
    """
    Download a reference proteome data file using Uniprot's puid
    """
    #merge domain and upid to path
    pathToReferenceProteome = "/".join([path,proteome.domain,proteome.upid])
    #extract basename and path in list of dicts
    filesInDir : Dict[str : str] = dict([(os.path.basename(filePath), filePath) for filePath in list_ftp_directory(domain,pathToReferenceProteome)])
    if not len(filesInDir):
        raise ValueError("No files detected on ftp server. Please check proteome entries. Provided: " + str(proteome))

    rr = requests.get("https://www.ebi.ac.uk/proteins/api/proteomes", {"upid" : proteome.upid})
    rr.raise_for_status()
    data = rr.json()[0] #should only be a single result, index == 0 
    taxonomy = data["taxonomy"] ## the taxonomy id (4 digists) is also present in the files of the reference proteomes  
    protomeName = data["name"]
    #prepare download folder

    if check_dir_exists(os.path.join(getPathToResources(),"Proteomes",proteome.upid),True,True):

        print(os.listdir("./resources/proteomes"))
    
        print(f"Download fasta file for {protomeName} - {proteome.upid}")
        fastaFileName = f"{proteome.upid}_{taxonomy}.fasta.gz"
        if fastaFileName in filesInDir:
            downloadFileFromFTP(filePath=filesInDir[fastaFileName],domain=domain, downloadPath="./resources/proteomes/download.fasta.gz")
        raise ValueError(f"FastaFileName {fastaFileName} was not found in the ftp dir.")
