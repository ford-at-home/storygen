from langchain.embeddings import BedrockEmbeddings
from langchain.vectorstores import Pinecone
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import pinecone
from pathlib import Path
from config import config

def ingest():
    # Initialize configuration
    config.initialize()
    
    pinecone.init(
        api_key=os.environ["PINECONE_API_KEY"], 
        environment=config.PINECONE_ENVIRONMENT
    )
    
    docs = []
    data_files = list(config.DATA_DIR.glob("*.md"))
    
    if not data_files:
        print("❌ No markdown files found in data directory!")
        return
    
    print(f"📚 Loading {len(data_files)} documents...")
    for file_path in data_files:
        print(f"   - Loading {file_path.name}")
        loader = TextLoader(str(file_path))
        docs.extend(loader.load())

    print(f"✂️  Splitting documents into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, 
        chunk_overlap=config.CHUNK_OVERLAP
    )
    splits = splitter.split_documents(docs)
    print(f"   - Created {len(splits)} chunks")

    print("🔧 Creating embeddings and storing in Pinecone...")
    embeddings = BedrockEmbeddings(
        region_name=config.AWS_REGION,
        model_id=config.BEDROCK_EMBEDDING_MODEL_ID
    )
    
    Pinecone.from_documents(
        splits, 
        embeddings, 
        index_name=config.PINECONE_INDEX_NAME
    )
    
    print("✅ Document ingestion complete!")

if __name__ == "__main__":
    ingest()
