# query.py
import os
import base64
from langchain_postgres import PGVector
from langchain_experimental.open_clip import OpenCLIPEmbeddings
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("DATABASE_URL")
COLLECTION_NAME = "historical_figures"

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def identify_ancient_person(test_image_path):
    print("Loading OpenCLIP model and connecting to database...")
    embedding_model = OpenCLIPEmbeddings(
        model_name="ViT-H-14", 
        checkpoint="laion2b_s32b_b79k"
    )
    
    vectorstore = PGVector(
        connection=CONNECTION_STRING,
        embeddings=embedding_model,
        collection_name=COLLECTION_NAME,
    )

    if not os.path.exists(test_image_path):
        print(f"Error: Image {test_image_path} not found. Please add an image to the data folder!")
        return
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.3)
    image_base64 = encode_image_to_base64(test_image_path)
    
    pre_prompt = (
        "請客觀且詳細地描述這張畫像中人物的視覺特徵，包含體態、臉部特徵、衣著樣式與顏色。"
        "請不要猜測他的歷史身分，只需要純粹的視覺特徵描述，字數控制在 100 字以內。"
    )
    pre_message = HumanMessage(
        content=[
            {"type": "text", "text": pre_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
    )
    gemini_vision_desc = llm.invoke([pre_message]).content

    print("Converting test image to feature vector...")
    query_vector = embedding_model.embed_image([test_image_path])[0]

    print("Converting Gemini description to text vector...")
    text_query_vector = embedding_model.embed_documents([gemini_vision_desc])[0]


    # pgvector search with score by vector
    print("Searching in pgvector database...")
    results = vectorstore.similarity_search_with_score_by_vector(query_vector, k=1)
    text_results = vectorstore.similarity_search_with_score_by_vector(
        text_query_vector, k=1, filter={"source_type": "text_record"}
    ) 
    # Set distance threshold
    # If the distance is greater than this threshold, it is considered "not found in the database"
    # OpenCLIP ViT-H-14 distance threshold can be set between 0.8 and 1.0, which can be adjusted according to actual testing
    DISTANCE_THRESHOLD = 0.2 
    TEXT_THRESHOLD = 0.3
    
    db_context = ""
    is_found = False
    
    if results:
        doc, distance = results[0]
        # If the distance is less than the threshold -> it means it is very similar and the match is successful
        if distance <= DISTANCE_THRESHOLD:
            name = doc.metadata.get("name", "none")
            desc = doc.metadata.get("description", "no description")
            db_context = f"【SYSTEM HINT: Database precise match successful】\nName: {name}\nBackground Information: {desc}\nFeature Distance Score: {distance:.4f} (closer to 0 is more accurate)"
            is_found = True
            print(f"Successfully matched database character: {name} (Distance: {distance:.4f})")
        else:
            print(f"Although the feature distance is too large ({distance:.4f}), it is judged to be not found in the database.\n")
    # 判定二：文字文獻是否有命中？
    if text_results:
        txt_doc, txt_dist = text_results[0]
        if txt_dist <= TEXT_THRESHOLD:
            txt_name = txt_doc.metadata.get("name", "none")
            desc = txt_doc.metadata.get("description", "no description")
            db_context = (f"【文獻比對成功】最符合特徵的人物為：{txt_name}\n歷史描述：{desc}\n(特徵距離: {txt_dist:.4f})")
            is_found = True
            print(f"✅ 文獻比對成功: {txt_name} (Distance: {txt_dist:.4f})")
        else:
            print(f"❌ 文獻距離過大: {txt_dist:.4f}")

    if not is_found:
        db_context = "【SYSTEM HINT】No similar ancient people comparison data was found in the local pgvector database, indicating that this is a new ancient person."

    if not os.getenv("GEMINI_API_KEY"):
        print("Error: Please set your GEMINI_API_KEY in the .env file first!")
        return
        
    
    if is_found:
        prompt_text = (
            f"你是一個歷史學家與視覺分析專家。這張圖片經過資料庫特徵比對，已確認身份。\n"
            f"請根據以下資料庫提供的精準資訊，結合你的歷史知識，詳細向用戶介紹這張照片中的古人，並確認圖片是否符合該人物特徵：\n\n"
            f"{db_context}"
        )
    else:
        # 盲猜
        prompt_text = (
            f"{db_context}\n"
            "現在，請你發揮你強大的歷史、考古、古代服飾、髮型與藝術畫風知識，仔細分析這張圖片。\n"
            "請你觀察圖片中人物的冠冕、衣服樣式（如領口、顏色）、鬍鬚、五官特徵，甚至畫作的線條與紙張風格。\n"
            "即使資料庫沒有他的資料，也請你「基於你自己的判斷」，在回答中大膽給出一個『最有可能』的古人答案（例如：這看起來最像是唐太宗、或是蘇軾），"
            "並詳細列出你這樣盲猜的視覺依據與歷史推論理由。"
        )

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            }
        ]
    )
    
    response = llm.invoke([message])
    
    print("\n================== The Final Results ==================")
    print(response.content)
    print("=========================================================\n")
    
    return response.content

if __name__ == "__main__":
    identify_ancient_person("data/test_queries/安祿山.JPG")
