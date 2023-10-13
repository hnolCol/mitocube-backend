import os
import ftplib
import requests 
from typing import List


"/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/"


# URL = "https://rest.uniprot.org/uniprotkb/search"

# rr = requests.get(URL,params={"query": "human,cdc7"})
# rr.raise_for_status()
# print(rr.headers["Link"])
# print(rr.json())
# URL = "https://rest.uniprot.org/proteomes/search"
# #?compressed=true&fields=upid%2Corganism%2Corganism_id%2Cprotein_count%2Cbusco%2Ccpd%2Cgenome_assembly&format=tsv&query=%28%2A%29&size=500"


# rr = requests.get(URL,params={"fields" : "upid,organism,protein_count", "format" : "tsv", "size" : 500, "query" : "Homo sapiens", "compressed" : True})
# rr.raise_for_status()
# print(rr.headers)
# print(rr.json())
# print(b)

file = "pub/databases/uniprot/current_release/knowledgebase/pan_proteomes/UP000000212.fasta.gz"  
def downloadFileFromFTP(filePath : str, domain : str = "ftp.uniprot.org", username : str = "", password : str = "", downloadPath = "."):
    """
    
    """
    with ftplib.FTP(domain) as ftp:
        ftp.login(user=username,passwd=password) 
        with open(downloadPath, 'wb') as fp:
                ftp.retrbinary("RETR " + filePath,  fp.write)

    #FTP("ftp://ftp.uniprot.org/pub/databases/uniprot/current_release")



def list_ftp_directory(domain : str, pathToDir : str ,user : str ='', password : str='') -> List[str]:
    """
    Lists all files present in folder from FTP server.

    """
    ftp_url = "ftp://"+"ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/pan_proteomes"
    #domain = ftp_url.split('/')[2]
    print(domain)
    try:
        with ftplib.FTP(domain) as ftp:
            ftp.login(user=user, passwd=password)
            files = ftp.nlst(pathToDir)
    except ftplib.error_perm as err:
        raise Exception("builder_utils - Problem listing file at {} ftp directory > {}.".format(pathToDir, err))

    return files

