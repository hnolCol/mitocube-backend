
import os 
from pydantic import BaseModel 

from lib.database.neo4j.Submission import SubmissionABC
from lib.database.neo4j.Dataset import DatasetABC
from lib.database.neo4j.Users import UserABC
from lib.database.neo4j.Genotypes import GenotypeABC
from config.models.submissions.submissions import DatasetSubmissionModel
from config.models.user import UserModelForRegistration, UserModel
from config.models.genotype import GenotypeModel
from services.json import read_json
import pandas as pd 

DIR = "/Users/hnolte/Desktop/resources"

dirs = os.listdir(os.path.join(DIR,"data"))


class MigrateScripts:

    def __init__(self, submissions :  SubmissionABC, datasets : DatasetABC, users : UserABC, genotypes : GenotypeABC):

        self.submissions = submissions
        self.datasets = datasets 
        self.users = users 
        self.genotypes = genotypes


    def add_users(self):
        "" 
        users_path = os.path.join(DIR,"users","users.json")
        if os.path.exists(users_path):
            us = read_json(users_path)
            users = [UserModel(**u, tag = u["label"]) for u in us]
            self.users.add_users(users=users)
            

    def add_genotypes(self):
        
        genotype_path = os.path.join(DIR,"genotypes","genotypes.json")
        if os.path.exists(genotype_path):
            gs = read_json(genotype_path)
            gs = [GenotypeModel(
                proteome_tag= g["proteome_id"],
                tag = g["label"],
                text = g["text"],
                features=[f["key"] for f in g["features"]]
                ) for g in gs]
            self.genotypes.add()
            

    def run(self):
        
        for submission_tag in dirs: 
            
            json_file_path = os.path.join(DIR,"data",submission_tag,"params.json")
            data_file_path = os.path.join(DIR,"data",submission_tag,"data.txt")
            if not os.path.exists(json_file_path): 
                print("NO params file found", submission_tag)
                continue
            submission = read_json(json_file_path)
            has_data = os.path.exists(data_file_path)
        
           # meta = DatasetSubmissionModel(**submission, tag = submission["label"])
            organisms = submission["dataset_attributes"]["att_organism"]
            #print(organisms)
            submission["dataset_attributes"]["att_proteome"] = [o.replace("att_organism:","").replace("controls","ctrl") for o in organisms]
            del  submission["dataset_attributes"]["att_organism"] 
            #print(submission["dataset_attributes"]["att_proteome"])
            
            d = DatasetSubmissionModel(**submission, tag = submission["label"], user_tag=submission["user_label"])
            #print(d)
            self.submissions.insert(d)
            print(has_data)
            if has_data:
                data = pd.read_csv(data_file_path,sep="\t").set_index("Key")
                print(data)
                self.datasets.insert(data_table=data, tag=submission_tag)
            
            
            
            
           # self.submissions.insert(submission=)
            
            
            
    
    
    