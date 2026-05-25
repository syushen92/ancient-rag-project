import os
import json
from langchain_postgres import PGVector
from langchain_experimental.open_clip import OpenCLIPEmbeddings
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("DATABASE_URL")
COLLECTION_NAME = "historical_figures"

def main():
    print("Initializing CLIP model...")
    print("Note: The first time you run this script, it will automatically download the CLIP model weights from HuggingFace.")

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
    
    texts_to_insert = []
    embeddings_to_insert = []
    metadatas_to_insert = []

    # ==========================================
    # 階段一：處理圖片
    # ==========================================
    image_dir = "data/image"

    if not os.path.exists(image_dir):
        print(f"Error: Directory {image_dir} not found. Please create it and add images!")
        return

    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not image_files:
        print(f"No images found in {image_dir}.")
        return

    print(f"Found {len(image_files)} images. Starting embedding process...")

    for image_file in image_files:
        image_path = os.path.join(image_dir, image_file)
        base_name = os.path.splitext(image_file)[0]

        print(f" -> Converting image {image_file} to vector...")
        image_vector = embedding_model.embed_image([image_path])[0]

        texts_to_insert.append(base_name)
        embeddings_to_insert.append(image_vector)
        metadatas_to_insert.append({
            "name": base_name,
            "source_type": "image"
        })

    # ==========================================
    # 階段二：處理 JSON 文字
    # ==========================================
    json_path = "data/texts/historical_figures.json"
    
    if not os.path.exists(json_path):
        print(f"Warning: JSON file {json_path} not found.")
    else:
        print(f"\nFound JSON data. Starting text embedding process...")
        with open(json_path, "r", encoding="utf-8") as f:
            historical_data = json.load(f)
            
        for item in historical_data:
            name = item["name"]
            text_desc = item["description"]
            dynasty = item.get("dynasty", "未知")
            
            print(f" -> Converting text for {name} to vector...")
            text_vector = embedding_model.embed_documents([text_desc])[0]
            
            texts_to_insert.append(name)
            embeddings_to_insert.append(text_vector)
            metadatas_to_insert.append({
                "name": name,
                "description": text_desc,
                "dynasty": dynasty,
                "source_type": "text_record"
            })

    # ==========================================
    # 階段三：一次性寫入資料庫
    # ==========================================
    if embeddings_to_insert:
        print("\nWriting all vectors and metadata to database...")
        vectorstore.add_embeddings(
            texts=texts_to_insert,
            embeddings=embeddings_to_insert,
            metadatas=metadatas_to_insert
        )
        print("🎉 Successfully wrote all vectors and metadata to database!")
    else:
        print("No valid data (images or text) found to insert.")

if __name__ == "__main__":
    main()
