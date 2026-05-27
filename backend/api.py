import os
import shutil
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from query import identify_ancient_person

app = FastAPI(title="Ancient RAG API")

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat_with_image(image: UploadFile = File(...)):
    os.makedirs("data/test_queries", exist_ok=True)
    temp_path = f"data/test_queries/temp_{image.filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    try:
        result_text = identify_ancient_person(temp_path)
        return {"response": result_text}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
