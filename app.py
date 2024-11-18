import os
import json
import openai
from datetime import datetime
from dotenv import load_dotenv
import chainlit as cl
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import load_index_from_storage, Settings
from llama_index.core import StorageContext
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.agent.openai import OpenAIAgent
from llama_index.core.storage.chat_store import SimpleChatStore
from prompts import CUSTOM_AGENT_SYSTEM_TEMPLATE
from llama_index.core.query_engine import SubQuestionQueryEngine
from typing import Dict, Optional

#load environment variables
load_dotenv()

openai.api_key = os.getenv("OPEN_API_KEY")
Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.2, max_tokens= 1024, streaming=True)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")
Settings.context_window = 4096 # manage the amount of text the model can process at once

# path to the index storage
index_storage = "./data/index_storage"
# path to the chat history storage
conversation_file = "./data/cache/chat_history.json"

# load the conversation history
def load_chat_store():
    if os.path.exists(conversation_file) and os.path.getsize(conversation_file) > 0:
        try:
            chat_store = SimpleChatStore.from_persist_path(conversation_file)
        except:
            chat_store = SimpleChatStore()
    else:
        chat_store = SimpleChatStore()
    return chat_store

# build the agent
def initialize_chatbot(chat_store):
    memory = ChatMemoryBuffer.from_defaults(
        token_limit=1500, 
        chat_store=chat_store, 
        chat_store_key= "user"
    )  
    storage_context = StorageContext.from_defaults(
        persist_dir= index_storage
    )
    
    # load the index from the storage context
    index = load_index_from_storage(
        storage_context
    )
    
    # setup base query engine 
    individual_query_engine_tool = [
        QueryEngineTool(
            query_engine = index.as_query_engine(),
            metadata = ToolMetadata(
                name="booksource",
                description=(
                    f"Provide information about diseases of trees and plants in Vietnam"
                    f"based on the stored document 'Diagnostic manual for plant diseases in Vietnam'."
                )
            )
        )        
    ]
    
    # setup subquery engine
    query_engine = SubQuestionQueryEngine.from_defaults(
        query_engine_tools = individual_query_engine_tool,
        llm = OpenAI(model="gpt-4o-mini", temperature=0.2, max_tokens= 1024, streaming=True)
    )
    
    # setup quey engine tool using the subquery engine
    query_engine_tool= QueryEngineTool(
        query_engine=query_engine, 
        metadata=ToolMetadata(
            name="subqueryengine",
            description=(
                f"Provide information about diseases of trees and plants in Vietnam"
                f"based on the stored document 'Diagnostic manual for plant diseases in Vietnam'."
            )
        )
    )   
    
    #combine all the query engines as tool
    tool = individual_query_engine_tool + [query_engine_tool]

    agent = OpenAIAgent.from_tools(
        tool,
        memory=memory,
        verbose=True, # print some intermediate logs to the console.
        system_prompt=CUSTOM_AGENT_SYSTEM_TEMPLATE.format(user_info="Hao")
    )
    
    return agent

# Define some default starter questions
@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Steps to perform Koch’s postulates",
            message="Based on the document 'Diagnostic manual for plant diseases in Vietnam', please describe the steps to perform Koch’s postulates.",
            icon="/public/banana.svg",
        ),
        cl.Starter(
            label="Field equipment for diagnostic studies",
            message="Based on the document 'Diagnostic manual for plant diseases in Vietnam', what are the equipment in the field equipment checklist?",
            icon="/public/rocket.svg",
        ),
        cl.Starter(
            label="Common symptoms of plant diseases",
            message="Based on the document 'Diagnostic manual for plant diseases in Vietnam', please describe the common symptoms of plant diseases.",
            icon="/public/sun.svg",
        ),
        cl.Starter(
            label="Pathogenicity testing",
            message="Based on the document 'Diagnostic manual for plant diseases in Vietnam',what are factors that need to be considered in pathogenicity testing?",
            icon="/public/tree.svg",
        )
    ]
    
# authenticate the user login into the chatbot
@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    if (username, password) == ("haotrinh", "211003"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
        return None
    
# authenticate the user login into the chatbot with google
@cl.oauth_callback
def oauth_callback(
  provider_id: str,
  token: str,
  raw_user_data: Dict[str, str],
  default_user: cl.User,
) -> Optional[cl.User]:
  return default_user

# Function when a new chat session starts
@cl.on_chat_start
async def on_chat_start():
    chat_store = load_chat_store()
    agent = initialize_chatbot(chat_store)
    cl.user_session.set("agent", agent)
    cl.user_session.set("chat_store", chat_store)
    

@cl.on_chat_resume
async def on_chat_resume():
    chat_store = load_chat_store()
    agent = initialize_chatbot(chat_store)
    cl.user_session.set("agent", agent)
    cl.user_session.set("chat_store", chat_store)
    
@cl.on_message
async def on_chat_message(message):
    agent = cl.user_session.get("agent")
    chat_store = cl.user_session.get("chat_store")

    #create a new message instance
    msg = cl.Message(content="", author="Assistant")

    #response generation
    res = await cl.make_async(agent.stream_chat)(message.content)
    
    #stream the response tokens
    for token in res.response_gen:
        await msg.stream_token(token)

    #persist the conversation
    chat_store.persist(conversation_file)
    await msg.send()
    
if __name__ == "__main__":
    cl.run()




