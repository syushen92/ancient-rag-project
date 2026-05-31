import os
import glob
import json
import base64
import time
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

IMAGE_FOLDER = "data/image" 
OUTPUT_JSON = "data/texts/historical_figures.json"

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def build_automated_json():
    print("🚀 啟動自動化圖轉文標註管線 (📸 檔名精準追蹤 + 防 Rate Limit 模式)...")

    if not os.path.exists(IMAGE_FOLDER):
        print(f"❌ 找不到資料夾 {IMAGE_FOLDER}，請先建立並放入古人圖片！")
        return

    extensions = ('*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG')
    image_paths = []
    for ext in extensions:
        image_paths.extend(glob.glob(os.path.join(IMAGE_FOLDER, ext)))
        
    if not image_paths:
        print(f"❌ {IMAGE_FOLDER} 裡面沒有圖片！")
        return

    # ==========================================
    # 讀取已完成進度 (認檔名，不怕同名覆蓋)
    # ==========================================
    records = []
    processed_files = set()
    
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                records = json.load(f)
                for r in records:
                    if "image_filename" in r:
                        processed_files.add(r["image_filename"])
            print(f"📦 已載入 {len(processed_files)} 筆舊資料，準備繼續...")
        except Exception as e:
            print("⚠️ 無法讀取既有的 JSON 檔，將重新開始。")

    print(f"📸 總圖庫共 {len(image_paths)} 張，準備處理剩下的圖片...\n")

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.2)
    
    system_prompt = (
        "你是一個專業的歷史畫像特徵分析師。請客觀且詳細地描述這張畫像中人物的視覺特徵，"
        "包含體態（胖瘦）、臉部特徵（是否有鬍鬚、皺紋）、衣著樣式（圓領/交領）與主要顏色、以及頭飾（冠冕/幞頭）。\n"
        "⚠️ 注意：不要猜測他的歷史身分，不需要開場白，直接給出一段大約 50~100 字的純特徵描述文字即可。"
    )

    for index, img_path in enumerate(image_paths, 1):
        filename = os.path.basename(img_path)
        person_name = filename.split('.')[0].split('_')[0]
        
        # 遇到做過的圖片直接跳過
        if filename in processed_files:
            print(f"[{index}/{len(image_paths)}] ⏭️ 圖片 {filename} 已經處理過，跳過。")
            continue
            
        print(f"[{index}/{len(image_paths)}] 正在處理: {person_name} ({filename})...")
        
        max_retries = 3
        success = False
        for attempt in range(max_retries):
            try:
                image_base64 = encode_image_to_base64(img_path)
                
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": system_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                )
                
                response = llm.invoke([message])
                description = response.content.strip()
                
                records.append({
                    "name": person_name,
                    "image_filename": filename,
                    "description": description
                })
                processed_files.add(filename)
                
                print(f"   ✅ 成功萃取：{description[:30]}...") 
                
                with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False, indent=4)
                    
                success = True
                break
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"   ⚠️ 觸發 API 速限！等待 60 秒後重試 (第 {attempt + 1}/{max_retries} 次)...")
                    time.sleep(60)
                else:
                    print(f"   ❌ 處理 {filename} 時發生錯誤: {error_msg}")
                    break

        if success:
            time.sleep(7)

    print(f"\n🎉 大功告成！總共 {len(records)} 筆資料已安全存入 {OUTPUT_JSON}！")

if __name__ == "__main__":
    build_automated_json()
