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

# ==========================================
# 🌟 全域初始化區域 (Global Initialization) 🌟
# 把肥大的模型跟資料庫連線移到這裡，整個系統只會載入一次！
# ==========================================
print("🧠 [系統初始化] 正在載入 OpenCLIP 模型、資料庫連線與 Gemini API...")
try:
    # 1. 載入視覺特徵模型
    embedding_model = OpenCLIPEmbeddings(
        model_name="ViT-H-14",
        checkpoint="laion2b_s32b_b79k"
    )

    # 2. 建立資料庫連線
    vectorstore = PGVector(
        connection=CONNECTION_STRING,
        embeddings=embedding_model,
        collection_name=COLLECTION_NAME,
    )

    # 3. 預先準備好大模型
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
    
    print("✅ [系統初始化] 載入完成！準備好接收圖片了。")
except Exception as e:
    print(f"❌ 初始化發生錯誤: {e}")

# ==========================================

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def identify_ancient_person(test_image_path):
    if not os.path.exists(test_image_path):
        print(f"Error: Image {test_image_path} not found. Please add an image to the data folder!")
        return "❌ 找不到測試圖片檔案"

    # 以下邏輯完全保留你原本的寫法，我們只移除了重複載入的部分
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
    
    # 呼叫已經全域載入好的 llm
    gemini_vision_desc = llm.invoke([pre_message]).content

    # 轉換圖片向量
    query_vector = embedding_model.embed_image([test_image_path])[0]

    # 轉換文字向量
    text_query_vector = embedding_model.embed_documents([gemini_vision_desc])[0]

    # pgvector search with score by vector
    results = vectorstore.similarity_search_with_score_by_vector(query_vector, k=50,filter={"source_type":"image"})
    text_results = vectorstore.similarity_search_with_score_by_vector(
        text_query_vector, k=50, filter={"source_type": "text_record"}
    )

    # 門檻值
    DISTANCE_THRESHOLD = 0.1
    TEXT_THRESHOLD = 0.2

    # 狀態變數初始化
    img_passed = False
    txt_passed = False
    best_img = None
    best_txt = None

    # ------------------------------------------
    # 處理軌道一：圖搜圖的群體平均分數
    # ------------------------------------------
    if results:
        img_distances = {}
        img_descs = {}
        for doc, dist in results:
            name = doc.metadata.get("name", "none")
            desc = doc.metadata.get("description", "no description")

            if name not in img_distances:
                img_distances[name] = []
                img_descs[name] = desc
            img_distances[name].append(dist)

        avg_img_results = []
        for name, dists in img_distances.items():
            avg_img_results.append({
                "name": name,
                "avg_dist": sum(dists) / len(dists),
                "count": len(dists),
                "desc": img_descs[name]
            })

        avg_img_results.sort(key=lambda x: x["avg_dist"])
        best_img = avg_img_results[0]

        if best_img["avg_dist"] <= DISTANCE_THRESHOLD:
            img_passed = True
            print(f"🖼️ 圖片群體比對過關: {best_img['name']} (平均距離: {best_img['avg_dist']:.4f})")
        else:
            print(f"❌ 圖片群體距離過大 ({best_img['avg_dist']:.4f})")

    # ------------------------------------------
    # 處理軌道二：文搜文的群體平均分數
    # ------------------------------------------
    if text_results:
        txt_distances = {}
        txt_descs = {}
        for doc, dist in text_results:
            name = doc.metadata.get("name", "none")
            desc = doc.metadata.get("description", "no description")

            if name not in txt_distances:
                txt_distances[name] = []
                txt_descs[name] = desc
            txt_distances[name].append(dist)

        avg_txt_results = []
        for name, dists in txt_distances.items():
            avg_txt_results.append({
                "name": name,
                "avg_dist": sum(dists) / len(dists),
                "count": len(dists),
                "desc": txt_descs[name]
            })

        avg_txt_results.sort(key=lambda x: x["avg_dist"])
        best_txt = avg_txt_results[0]

        if best_txt["avg_dist"] <= TEXT_THRESHOLD:
            txt_passed = True
            print(f"✅ 文獻群體比對過關: {best_txt['name']} (平均距離: {best_txt['avg_dist']:.4f})")
        else:
            print(f"❌ 文獻群體距離過大 ({best_txt['avg_dist']:.4f})")

    # ------------------------------------------
    # 終極判定：雙軌並存，交由大模型與使用者綜合評斷
    # ------------------------------------------
    db_context = ""
    is_found = False

    system_log = "【系統比對數據】\n"

    if img_passed:
        system_log += f"🖼️ 圖片群體比對過關: {best_img['name']} (平均距離: {best_img['avg_dist']:.4f})\n"
    else:
        system_log += "❌ 圖片比對未達標\n"

    if txt_passed:
        system_log += f"✅ 文獻群體比對過關: {best_txt['name']} (平均距離: {best_txt['avg_dist']:.4f})\n"
    else:
        system_log += "❌ 文獻比值得未達標\n"

    system_log += f"\n【Gemini 初始特徵描述】\n{gemini_vision_desc}\n"
    system_log += "\n========================\n\n"

    if img_passed and txt_passed:
        is_found = True
        if best_img['name'] == best_txt['name']:
            print(f"\n🎉 雙軌完美一致！雙方皆判定為：{best_img['name']}")
            db_context = (
                f"【SYSTEM HINT: 雙模態完美吻合】\n"
                f"人物：{best_img['name']}\n"
                f"歷史描述：{best_txt['desc']}\n"
                f"(備註：圖片與文獻皆精準指向同一人，可信度極高)"
            )
        else:
            print(f"\n⚖️ 雙軌結果分歧 (圖片推測: {best_img['name']} vs 文獻推測: {best_txt['name']})，交由大模型雙重分析。")
            db_context = (
                f"【SYSTEM HINT: 雙模態出現分歧，請同時分析以下兩位候選人】\n"
                f"候選人一 (基於視覺畫風與輪廓最接近)：{best_img['name']}\n"
                f"候選人一描述：{best_img['desc']}\n"
                f"---\n"
                f"候選人二 (基於衣著與體態等語意最接近)：{best_txt['name']}\n"
                f"候選人二描述：{best_txt['desc']}\n"
            )

    elif img_passed: 
        is_found = True
        print(f"\n✅ 僅圖片比對成功，判定為: {best_img['name']}")
        db_context = f"【SYSTEM HINT: 僅圖片比對成功】\n人物：{best_img['name']}\n歷史描述：{best_img['desc']}"

    elif txt_passed: 
        is_found = True
        print(f"\n✅ 僅文獻比對成功，判定為: {best_txt['name']}")
        db_context = f"【SYSTEM HINT: 僅文獻比對成功】\n人物：{best_txt['name']}\n歷史描述：{best_txt['desc']}"

    else: 
        print("\n❌ 圖片與文字皆未達標，判定為查無此人。")
        db_context = "【SYSTEM HINT】資料庫中找不到符合此視覺特徵的古人。請啟動盲猜模式。"

    if not os.getenv("GEMINI_API_KEY"):
        print("Error: Please set your GEMINI_API_KEY in the .env file first!")
        return "❌ 未設定 API KEY"

    # ==========================================
    # 最終大模型生成
    # ==========================================
    if is_found:
        prompt_text = (
            f"你是一個歷史學家與視覺分析專家。這張圖片經過我們的多模態資料庫比對，得出了以下結果。\n"
            f"請根據以下資料庫提供的精準資訊，結合你的歷史知識，詳細向用戶介紹照片中的古人。\n"
            f"⚠️ 核心任務：如果資料庫判定為同一人，請專心介紹他。但如果資料庫提供了『兩位』不同的候選人，請你秉持客觀，『同時介紹這兩位人物的生平』，並根據畫像中的細節，分析圖片分別與哪位候選人的特徵比較吻合，引導用戶自行參考。\n\n"
            f"{db_context}"
        )
    else:
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
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
    )

    response = llm.invoke([message])
    final_output = f"{system_log}{response.content}"

    print("\n================== The Final Results ==================")
    print(final_output)
    print("=========================================================\n")

    return final_output

if __name__ == "__main__":
    identify_ancient_person("data/test_queries/武則天.JPEG")
