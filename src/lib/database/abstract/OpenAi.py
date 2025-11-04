



from config.settings.openai import get_open_ai_settings
from openai import OpenAI
from neo4j import Result, Driver
open_ai_settings = get_open_ai_settings()
from abc import abstractmethod, ABC
from typing import List, Dict
class OpenAIClient(ABC):
    def __init__(self):
        
        self.api_key = open_ai_settings.open_ai_api_key
        self.base_url = open_ai_settings.chat_ai_base_url
        self.ai_model = open_ai_settings.chat_model
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)


    @abstractmethod
    def execute_query(self, cypher_query : str) -> dict:
        """
        Executes a database query and returns the results.
        """
        
        
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
                    Please linke the pubmed IDs using the format [pubmedid](https://pubmed.ncbi.nlm.nih.gov/{pubmedid})
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