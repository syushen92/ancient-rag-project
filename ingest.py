import os
from langchain_postgres import PGVector
from langchain_experimental.open_clip import OpenCLIPEmbeddings
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("DATABASE_URL")
COLLECTION_NAME = "historical_figures"

def main():
    print("Initializing CLIP model")
    print("Note: The first time you run this script, it will automatically download the CLIP model weights from HuggingFace, which may take one or two minutes. Please be patient.")
    
    embedding_model = OpenCLIPEmbeddings(
        model_name="ViT-H-14", 
        checkpoint="laion2b_s32b_b79k"
    )
    
    print("Successfully loaded the CLIP model")

    vectorstore = PGVector(
        connection=CONNECTION_STRING,
        embeddings=embedding_model,
        collection_name=COLLECTION_NAME,
    )
    image_dir = "data/image"
    
    if not os.path.exists(image_dir):
        print(f"Error: Directory {image_dir} not found. Please create it and add images!")
        return

    # get all the images in the image directory
    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_files:
        print(f"No images found in {image_dir}.")
        return

    texts_to_insert = []
    embeddings_to_insert = []
    metadatas_to_insert = []

    print(f"Found {len(image_files)} images. Starting embedding process...")

    for image_file in image_files:
        image_path = os.path.join(image_dir, image_file)
        # get the base name of the image (e.g., IMG_1270.png -> IMG_1270)
        base_name = os.path.splitext(image_file)[0]  
        
        print(f"Converting {image_file} to vector...")
        image_vector = embedding_model.embed_image([image_path])[0]
        
        # collect the data
        texts_to_insert.append(base_name)
        embeddings_to_insert.append(image_vector)
        metadatas_to_insert.append({
            "name": base_name,
            "source_type": "image"
        })

    print("Writing all vectors and metadata to database...")
    vectorstore.add_embeddings(
        texts=texts_to_insert,
        embeddings=embeddings_to_insert,
        metadatas=metadatas_to_insert
    )
    
    print("Successfully wrote all vectors and metadata to database!")

if __name__ == "__main__":
    main()