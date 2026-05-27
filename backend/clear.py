import os
from langchain_postgres import PGVector
from langchain_experimental.open_clip import OpenCLIPEmbeddings
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("DATABASE_URL")
COLLECTION_NAME = "historical_figures"

def clear_database():
    print("Connecting to database...")
    embedding_model = OpenCLIPEmbeddings(model_name="ViT-H-14", checkpoint="laion2b_s32b_b79k")
    vectorstore = PGVector(
        connection=CONNECTION_STRING,
        embeddings=embedding_model,
        collection_name=COLLECTION_NAME,
    )
    
    print("Dropping existing collection...")
    vectorstore.drop_tables()
    print("Database cleared successfully! You can now run ingest.py again to insert fresh data.")

if __name__ == "__main__":
    clear_database()
