import time
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from unittest import result
from httpcore import request
from typing_extensions import runtime 

from fastapi import APIRouter, BackgroundTasks, Depends, Body, HTTPException

from config.models.user import UserModel
from config.models.token.token import TokenVerificationCode, TokenResponse, ShareTokenPassword, TokenValidResponse
from config.settings.general import get_general_settings
from config.settings.email import get_email_settings
from config.settings.openai import get_open_ai_settings 
from services.users import get_user_from_token, is_user_at_least_curator
from typing import Dict, Literal
from services.random_generators import get_random_string

from services.external.pubmed import get_pubmed_ids_by_query, get_pubmed_publications
from langchain_core.messages import AIMessage


from lib.ai.agent.agent import ChatRequest
from lib.ai.agent.runtime import ai_agent_runtime


EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()
OPEN_AI_SETTINGS = get_open_ai_settings()
router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/ai/openai",
    tags=["OpenAI", "ChatGPT"]
    )


@router.get("/literature/feature/proteins/{feature_tag}", response_description="Generates a literate search and summarizes the results.")
def generate_literate_search(feature_tag: str, user: UserModel = Depends(get_user_from_token), sort_by : Literal["pub_date", "relevance"] = "pub_date", limit : int = 5, db : DatabaseABC = Depends(get_db)) -> Dict:
    # Implement the logic for generating a literate search based on the feature_tag
    if not db.proteins.exists(tag = feature_tag): raise HTTPException(status_code=404, detail=f"Protein '{feature_tag}' not found")
    
    protein = db.proteins.get(tag = feature_tag)  # Just to check if the feature exists.
    # session_messages = db.cache.get(session_id) if db.cache.exists(session_id) else [{"role": "system", "content": OPEN_AI_SETTINGS.system_information}]
    pubmed_search_results = get_pubmed_ids_by_query(query = protein.gene_name, limit=limit, sort=sort_by)
    if len(pubmed_search_results["esearchresult"]["idlist"]) == 0:
        return {"message": "No PubMed articles found."}
    
    pubmed_publications_as_text = get_pubmed_publications(pubmed_search_results["esearchresult"]["idlist"])
    response = db.openai.summarize_pubmed_publications(prompt=pubmed_publications_as_text)
    return {"response": response}


@router.get("/cypher", response_description="Generates a cypher query for a given prompt.")
async def generate_cypher_query(prompt: str, session_id: str = None, user: UserModel = Depends(get_user_from_token)) -> Dict:
    
    if session_id is None:
        session_id = f"open_ai_chat_user_{user.tag}_{get_random_string()}"
    
    config = {"configurable": {"thread_id": session_id}}
    print(ai_agent_runtime.agent)
    try:
        result = await ai_agent_runtime.agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt + f" The current user tag is {user.tag}"}]},
            config=config,
        )
    except Exception as e:
        print(repr(e))
        print(getattr(e, "response", None) and e.response.text)
        print(getattr(e, "body", None))
        


    messages = result["messages"]
    last_ai_message = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage)), None
    )
    reply = last_ai_message.content if last_ai_message else ""

    tool_calls = [
        call["name"]
        for m in messages
        if isinstance(m, AIMessage)
        for call in (m.tool_calls or [])
    ]
    print("TOOL CALLS: ", tool_calls)
    print(result)
    print("Agent initialized and test message processed. ")
    
    print(reply)
    
    return {"response" : reply, "session_id": session_id, "session_messages": [{"role" : "user", "content": prompt}, {"role" : "assistant", "content": reply}]}
    
    
    
    # if session_id is None:
    #     session_id = f"open_ai_chat_user_{user.tag}_{get_random_string()}"
    # #if session id is given in the cache, load the messages. 
    # session_messages = db.cache.get(session_id) if db.cache.exists(session_id) else [{"role": "system", "content": OPEN_AI_SETTINGS.system_information}]

    # session_messages.append({"role": "user", "content": prompt, "return": True})
    
    # try:
    #     cypher_query = db.openai.generate_cypher_query_for_prompt(prompt, session_messages=session_messages)
    # except Exception as e:
    #     print(e)
    #     raise HTTPException(status_code=500, detail=f"Error generating cypher query: {e}")


    # session_messages.append({"role": "assistant", "content": cypher_query})

    # queries = [q.strip() for q in re.findall(r"```cypher(?:[^\n]*\n)?(.*?)```", cypher_query, flags=re.S) if q.strip()]
    # print(queries)
    # if len(queries) == 0:
    #     session_messages.append({"role": "assistant", "content": cypher_query, "return": True})
    #     db.cache.insert(session_id,session_messages)
    #     return {"response": f"{cypher_query}. No database valid query.", "session_id": session_id, "session_messages": [msg for msg in session_messages if "return" in msg and msg["return"]]}
    # print(f"Generated {len(queries)} cypher queries.")
    # for q in queries:
    #     print(f"Query: {q}")
    # ds = []
    # for q in queries:
    #     try:
    #         d = db.openai.execute_query(q)
    #         ds.append(d)
    #     except Exception as e:
    #         #try to fix the query. 
    #         print(f"Error executing query '{q}': {e}. Trying a again")
    #         new_prompt =  f"I received an error with this Neo4J v 5.26 prompt {q}. The error returned was this: {e}. Do not change the name of the relationships. Return the fixed cypher query in a ```cypher``` block."
    #         fixed_query = db.openai.generate_cypher_query_for_prompt(new_prompt, temp = 0.5) #session messages not needed here?
    #         #save the messages to store them.
    #         fixed_queries = [q.strip() for q in re.findall(r"```cypher(?:[^\n]*\n)?(.*?)```", fixed_query, flags=re.S) if q.strip()]
    #         print("FIXED QUERY: ", fixed_query)
    #         session_messages.append({"role": "user", "content": new_prompt})
    #         session_messages.append({"role": "assistant", "content": fixed_query})
    #         try:
    #             for q in fixed_queries:
    #                 d = db.openai.execute_query(q)
    #             ds.append(d)
    #         except Exception as e2:
    #             print(f"Second attempt failed for query '{q}': {e2}. Skipping.")
    # if len(ds) == 0:
    #     session_messages.append({"role": "assistant", "content": "All queries failed to execute.", "return": True})
    #     db.cache.insert(session_id,session_messages)
    #     return {"response": "All queries failed to execute.", "session_id": session_id, "session_messages": [msg for msg in session_messages if "return" in msg and msg["return"]]}
    # print("PASSED TO OPENAI FOR DIGESTION: ", [{"role": "assistant", "content": cypher_query},{"role": "user", "content": f"Here is the data from Neo4j:\n{ds}\n\nPlease summarize or analyze it.The original cypher query was: {cypher_query}."}])
    # response = db.openai.digest_query_data(data = ds, cypher_query=cypher_query, session_messages = [{"role": "assistant", "content": cypher_query},{"role": "user", "content": f"Here is the data from Neo4j:\n{ds}\n\nPlease summarize or analyze it.The original cypher query was: {cypher_query}."}] )
    # session_messages.append({"role": "user", "content": f"Here is the data from Neo4j:\n{ds}\n\nPlease summarize or analyze it.The original cypher query was: {cypher_query}."})
    # session_messages.append({"role": "assistant", "content": response, "return": True})
    
    # db.cache.insert(session_id,session_messages)

    # 




# @router.post("/cypher/execute", response_description="Executes a cypher query and returns the results.")
# def execute_cypher_query(cypher_query: str = Body(..., embed=True)) -> dict:
    
#     results = db.openai.execute_cypher_query(cypher_query)
#     print(results)
    
#     return results