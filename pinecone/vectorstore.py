import pinecone
from langchain.embeddings import BedrockEmbeddings
from langchain.vectorstores import Pinecone
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from config import config

def init_vectorstore():
    pinecone.init(
        api_key=os.environ["PINECONE_API_KEY"], 
        environment=config.PINECONE_ENVIRONMENT
    )
    return Pinecone(
        index_name=config.PINECONE_INDEX_NAME, 
        embedding=BedrockEmbeddings(
            region_name=config.AWS_REGION,
            model_id=config.BEDROCK_EMBEDDING_MODEL_ID
        )
    )

def retrieve_context(query):
    store = init_vectorstore()
    docs = store.similarity_search(query, k=5)
    return "\n\n".join([d.page_content for d in docs])
