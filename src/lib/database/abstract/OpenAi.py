



from config.settings.openai import get_open_ai_settings
from openai import OpenAI
from neo4j import Result, Driver
open_ai_settings = get_open_ai_settings()
from abc import abstractmethod, ABC
from typing import List, Dict
from services.external.pubmed import get_pubmed_ids_by_query, get_pubmed_publications
import time 
import pandas as pd 
from io import StringIO
class OpenAIClient(ABC):
    def __init__(self):
        
        self.api_key = open_ai_settings.open_ai_api_key
        self.base_url = open_ai_settings.chat_ai_base_url
        self.ai_model = open_ai_settings.chat_model
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        print(self.api_key, self.base_url, self.ai_model)

    @abstractmethod
    def execute_query(self, cypher_query : str) -> dict:
        """
        Executes a database query and returns the results.
        """
        
    
    def generate_protein_phenotype_relationships(self, protein_name : str) -> str:
        """
        Generates a chat completion using the OpenAI API.
        """
        pubmed_search_result = get_pubmed_ids_by_query(query=protein_name, limit=50)
        print(pubmed_search_result)
        pubmed_ids = pubmed_search_result.get("esearchresult", {}).get("idlist", [])
        pubmed_publication_abstracts = get_pubmed_publications(pubmedids=pubmed_ids)
        
        print(pubmed_publication_abstracts)
        
        response = self.client.chat.completions.create(
            model=self.ai_model,
            messages=[{
                "role" : "system", 
                "content" : open_ai_settings.phenotype_relationship_system_message},
                {
            "role": "user",
            "content": f"Please extract protein-phenotype relationships for the protein: {protein_name}. Here are the PubMed article abstracts related to the protein:\n{pubmed_publication_abstracts}. This is the list of PubMed IDs you got the abstracts from: {', '.join(pubmed_ids)}. Please provide the output in a markdown table inside a ```markdown ... ``` block as specified in the system message."}
            ]
        )
        return str(response.choices[0].message.content)
    
        
        
    def generate_functional_classification(self, protein_names : List[str], ai_model : str = None) -> str:
        """
        Generates a chat completion using the OpenAI API.
        """
        
        print("FUNCTIONAL CLASSIFICATION FOR PROTEINS: ", protein_names)
        r = dict()
        classes = ""
        df_out = pd.DataFrame(columns=["Protein Name", "Functional Category", "Pathway", "PubmedIDs"])
        for protein_name in protein_names:
            print(protein_name)

            pubmed_search_result = get_pubmed_ids_by_query(query=protein_name, limit=15, sort = "relevance")
            pubmed_search_result_pub_data = get_pubmed_ids_by_query(query=protein_name, limit=5, sort = "pub_date")
            
            
            pubmed_ids = pubmed_search_result.get("esearchresult", {}).get("idlist", [])
            pubmed_ids_pub_date = pubmed_search_result_pub_data.get("esearchresult", {}).get("idlist", [])
            print(list(set(pubmed_ids + pubmed_ids_pub_date)))
            pubmed_publication_abstracts = get_pubmed_publications(pubmedids=list(set(pubmed_ids + pubmed_ids_pub_date)))
            r[protein_name] = {
                "pubmed_ids" : pubmed_ids,
                "abstracts" : pubmed_publication_abstracts
            }
        
    
            response = self.client.chat.completions.create(
                model=self.ai_model if ai_model is None else ai_model,
                messages=[{
                "role" : "system", 
                "content" : open_ai_settings.functional_classification_system_message},
                {
                "role": "user",
                "content": f"Please classify the following proteins based on your defined system role. Here are the abstracts I downloaded with the associated protein_name. {pubmed_publication_abstracts} and the matching pubmedids {pubmed_ids}.  Please provide the output in a text tab delimited with the headers Protein Name, Functional Category, Pathway, PubmedIDs (headers). Add the pubmed id for references. The pathway should be something like 'OXPHOS assembly' or 'Mitochondrial Import Regulation' 'Mitochondrial Import Component'. Please focus on mitochondrial pathways. The table must only contain the following protein names: {protein_names} IF there are no pubmed ids available, pease classify the protein as Unknown. So far the classification of other proteins is this : '{classes}'. You may align the functional categories and pathways retrospective with the ones you have already defined for other proteins to build relativ general (please dont overgeneralize it, some specificity should remain) and larger groups. Please be concise in the description of the functional category and pathway, as I want to use them in a network analysis. As an example: 'Mitochondrial ribosomes' or 'OXPHOS' or 'OXPHOS assembly' could reprents functional groups. You can also add multiple rows per table if you think the protein is involved in two pathways or has multiple functionns. IF the title contains the gene name, you shall prioritize this pubmed entry. Ideally, sort the classification/pathway by relevance/number of pubmed ids. Dont add any other protein to the list. Do not add any information about expression data such as 'allele specific expression' I am only interested in general pathways. The table will increase with consecutive queries. Make sure to provide TAB deliminted data!! The output table from the protein name must not contain any other protein that you find in the abstract."}
                ]
            )
            time.sleep(1) # to avoid hitting rate limits
            
           # classes += str(response.choices[0].message.content) + "\n"
            
            df = pd.read_csv(StringIO(response.choices[0].message.content), sep="\t")
            df.columns = ["Protein Name", "Functional Category", "Pathway", "PubmedIDs"]
            if "Functional Category" in df.columns:
            
                boolIdx = df.loc[:,"Functional Category"] == "Unknown"
                df = df.loc[~boolIdx] # remove unknowns, we will add them later, but we do not want to feed them back into the model.
            
            df.dropna(subset=["PubmedIDs"], inplace=True) # we want to make sure that there is at least a pubmed id for the classification, otherwise we do not want to feed it back into the model.
            
            df_out = pd.concat([df_out, df], ignore_index=True).drop_duplicates(keep="first") # we want to keep the first classification, as it is more likely to be correct, but we do not want duplicates in the output.

            classes = df_out.to_dict(orient="records")
        print(df_out)
        df_out.to_csv("functional_classification_output.csv", index=False, sep="\t")
        return classes
        
    def summarize_pubmed_publications(self, prompt) -> str:
        """
        Generates a chat completion using the OpenAI API.
        """
        response = self.client.chat.completions.create(
            model=self.ai_model,
            messages=[{
                "role" : "system", 
                "content" : """You are a literature summarizer. The prompt will be a list of pubmed publication's title, authors and abstract. 
                        Please summarize the findings and implications of the provided papers. You can also add other information that you find in the internet, 
                    but you must clearly state what the source for this statement is. You should return your results as markdown to enhance structure and readability.
                    Please link the pubmed IDs using the format [pubmedid](https://pubmed.ncbi.nlm.nih.gov/{pubmedid})
                    Please be concise and do not add unnecessary information."""},
                    {
                "role": "user", 
                "content":"Please summarize the following publications. I have attached the abstracts. The pubmedid can be found in the end of each paper. The publications start with 1. 2. 3. ...: \n" + prompt}]
        )
        return str(response.choices[0].message.content)

    def _generate_cypher_query_prompt(self, query: str) -> str:
        
        cypher_query = f"""The question of the user is: {query}

            """
        return cypher_query

    def generate_cypher_query_for_prompt(self, prompt: str, session_messages : List[Dict] = [], temp : float = 0.1, top_p : float = 1.0) -> str:
        # Placeholder for actual OpenAI API call
        p = self._generate_cypher_query_prompt(prompt)
        messages = session_messages + [{"role": "user", "content": f"The user asked this question regarding the Neo4J database. Recheck the system message to remember the rules. In line with the system information, please only provide the cypher queries in ```cypher``` blocks. : {p}"}]
        response = self.client.chat.completions.create(
            model=self.ai_model,  # use the latest model
            messages=messages,
            temperature=temp,
            top_p=top_p
        )
        return str(response.choices[0].message.content)
    

    def digest_query_data(self, data : any, cypher_query : str, session_messages : List[Dict] = [] ) -> str:
        """
        Digest the data from the query into a human readable format. 
        """
        # Placeholder for actual OpenAI API call

        response = self.client.chat.completions.create(
                model=open_ai_settings.chat_model,  # the API key must have access to the model, if you want to use another model, change it here.
                messages= session_messages + [
                    {
                        "role": "system",
                        "content": 
                            """You are a bioinformatic data analyst assistant. I have provided you with data from a cypher query to a Neo4j database.
                                Your task is to summarize or analyze the data based on the user's request.
                                Please provide concise and informative answers, using the data to back up your conclusions.
                                If the data is empty or does not contain relevant information, please indicate that as well.
                                Avoid overly verbose explanations.
                                Please provide your data in styled mark down format for better readability.
                                If there is a submission.tag reported in the data, please highlight it in the summary and you can also link to it using the format [submission.tag](https://mitocube.age.mpg.de/submissions/{submission.tag})
                                """},
                    {
                        "role": "user", 
                        "content": f"Here is the data from Neo4j:\n{data}\n\nPlease summarize or analyze it.The original cypher query was: {cypher_query}. Provide the answer in a concise manner and use the data to back up your answer. Always use mark down formatting."
                    }
                ]
    )

        return str(response.choices[0].message.content)