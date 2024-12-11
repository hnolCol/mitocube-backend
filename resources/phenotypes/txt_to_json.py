import os 
import pandas as pd 


phenotypes = pd.read_csv("phenotypes.txt", sep="\t")

phenotypes.to_json("phenotypes.json", indent=4, orient = "records")

