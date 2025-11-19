import os
import ftplib
import requests 
from typing import List



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

