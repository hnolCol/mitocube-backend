



from config.settings.openai import get_open_ai_settings
from openai import OpenAI
open_ai_settings = get_open_ai_settings()

class OpenAIClient:
    def __init__(self):
        self.api_key = open_ai_settings.open_ai_api_key
        self.client = OpenAI(api_key=self.api_key)

    def _generate_cypher_query_prompt(self, query: str) -> str:
        
        cypher_query = f"""The question of the user is: {query}

            IMPORTANT INFO: 
            I want to get just the cypher query, not more to be able to directly inject it into the database query. 
            It is absolutely NOT allowed to use MERGE or DELETE or anything that would delete something in the database. 

            Database Structure:
            - all nodes have a created_at param with the timestamp. 
            - all quantified value are in log2 intensities
            - all nodes have a unique "tag" which can be used. Do not use id() function please, but only the tag. 
            - There might be a typo in the gene name of the query. Would be good to check if that is actually a protein. 
            - 
            (Submission)-[:HAS_SAMPLE]->(Sample)
            (Protein)<-[r:QUANTIFIED]-(Sample)
            The Protein node has a param protein.s that allows to match a string to it. 

            (User)-[:CREATED]-(Submission)

            (Attribute)-[:HAS_TRAIT]->(Trait)
            (Sample)-[:HAS_APPLICATION]->(ConditionApplication)
            (Sample)-[:OF_GENOTYPE]->(Genotype)
            (Submission)-[:HAS_APPLICATION]->(ConditionApplication)
            If a Submission is connected to then this condition is true for all samples. 
            The ConditionApplication is a hierarchical structure and combines any attribute that is hierarchical in a way as: 

            (Attribute)-[:IS_CHILD]->(Attribute). 
            A condition value structure is as follows: 

            (ConditionApplication)-[:HAS_TRAIT]->(Trait)
            (ConditionApplication)-[:OF_ATTRIBUTE]->(Attribute)
            (ConditionApplication)-[:HAS_VALUE]->(ConditionValue)

            Then the ConditionValue has a param .value with a user input value. 
            Please note that The tag of a ConditionApplication is generated a all the params, therefore it can be connected to multiple Samples and Submissions.

            Let me provide some information about the database genotype structure and provide some tips. 
            If a question is regarding a genotype such as AFG3L - KO (another keyword would knockout or mutant). For example a question such as 
            "Is there a protein that is only quantified in AFG3L2-KO, you would have to first find the Genotype using the Protein node as a starting point: 
            (Protein)<-[:AFFECTS]-(Genotype) by the 's' param of the protein (e.e.g search). The s. param contains the official gene name and protein name, but not "KO". 
            Then find samples that are having this Genotype and quantified a protein that is not found in any other sample that has a Genotype as (Protein)-[r:QUANTIFIED]-(Samples)-[:OF_GENOTYPE]-(Genotype). 
            The relationship only exists if the protein was quantified. 

            Return data info

            - the data will be retrieved from the database in python using the neo4j package Result.data(). 

            Please return only the cypher query that I want to enter into the database. Not more, since this is an automatically generated request. 
            """
        return cypher_query

    def generate_cypher_query_for_prompt(self, prompt: str) -> str:
        # Placeholder for actual OpenAI API call
        p = self._generate_cypher_query_prompt(prompt)
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # use the latest model
            messages=[
                {"role": "system", "content": "You are a bioinformatics assistant. Create a neo4j cypher query based on a user prompt. We cannot use MERGE or DELETE in the query."},
                {"role": "user", "content": p}
            ]
        )

        return str(response.choices[0].message.content)
    

    def digest_query_data(self, data : any, cypher_query : str ) -> str:
        """
        Digest the data from the query into a human readable format. 
        """
        # Placeholder for actual OpenAI API call
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # use the latest model
        messages=[
            {"role": "system", "content": "You are a bioinformatics assistant."},
            {"role": "user", "content": f"Here is the data from Neo4j:\n{data}\n\nPlease summarize or analyze it.The original cypher query was: {cypher_query}. Provide the answer in a concise manner and use the data to back up your answer."}
        ]
    )

        return str(response.choices[0].message.content)