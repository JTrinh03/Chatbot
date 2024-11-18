from llama_index.core import SimpleDirectoryReader
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from dotenv import load_dotenv
import openai
import os


# load environment variables
load_dotenv()

openai.api_key = os.getenv("OPEN_API_KEY")
Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.2, max_tokens= 1024, streaming=True)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")

# path to the file
file_path = "./data/ingestion_storage"
# path to the index storage
index_storage = "./data/index_storage"
# load the file
documents = SimpleDirectoryReader(input_dir=file_path).load_data()

try:
    # reload the storage context
    storage_context = StorageContext.from_defaults(persist_dir = index_storage)
    # load the index from the storage context
    index = load_index_from_storage(storage_context)
    print("All indices loaded from storage.")
except:
    # create a new storage context
    storage_context = StorageContext.from_defaults()
    # create index from documents
    index = VectorStoreIndex.from_documents(documents, storage_context = storage_context)
    # store the new index
    storage_context.persist(persist_dir = index_storage)
    print("New indexes created and persisted.")
    

    
    





