# Ancient RAG Project

A modern Full-Stack Retrieval-Augmented Generation (RAG) web application that identifies ancient historical figures using multi-modal embeddings (OpenCLIP) and generative AI (Gemini).

## Architecture

```mermaid
flowchart TD
    FE["⬡ React Frontend\nlocalhost:5173"]
    API["⬡ FastAPI Backend\nlocalhost:8000"]
    CLIP["OpenCLIP ViT-H-14\nEmbedding Model"]
    PG[("PostgreSQL + pgvector\nCollection: historical_figures")]
    THRESH{"Cosine Distance\n≤ 0.2?"}
    GEMINI["Gemini 2.5 Flash\nMultimodal LLM"]
    OUT["Identification Result"]

    FE -->|"POST /api/chat\n(image upload)"| API
    API -->|"embed image"| CLIP
    CLIP -->|"query vector"| PG
    PG -->|"top-1 nearest neighbor"| THRESH
    THRESH -->|"Hit — name + description"| GEMINI
    THRESH -->|"Miss — blind inference"| GEMINI
    API -->|"image base64"| GEMINI
    GEMINI --> OUT
    OUT -->|"JSON response"| FE

    subgraph Ingestion["Data Ingestion  (ingest.py)"]
        IMG["Portrait Images\ndata/image/"]
        TXT["Text Records\ndata/texts/historical_figures.json"]
        IMG -->|"embed_image()"| PG
        TXT -->|"embed_documents()"| PG
    end
```

### File Structure

```text
ancient-rag-project/
├── frontend/                 
│   ├── src/                  
│   └── Dockerfile           
├── backend/                  
│   ├── api.py                # FastAPI entry point
│   ├── ingest.py             # Vector database seeding script
│   ├── query.py              # LLM + Vector Search core logic
│   └── data/
│       ├── image/            # Portraits used to seed the vector database (Embedding data)
│       └── test_queries/     # Input images used for searching and blind-guessing tests     
│   ├── requirements.txt      
│   └── Dockerfile            
├── docker-compose.yml       
├── .env                     
└── init.sql                
```

## Quick Start

### 1. Configure Environment Variables
1. Copy the example environment file: `cp .env.example .env`
2. Open `.env` and fill in your `GEMINI_API_KEY` and Database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).

### 2. Start the Full-Stack Application
Run the following command in the root directory to build and start all services (Database, API, and Web UI):
```bash
docker compose up --build -d
```

### 3. Initialize Data (Data Ingestion)
Because the database starts completely empty, you need to populate it with the historical figure images located in `backend/data/image/`.
Execute the ingestion script **inside** the running backend container:
```bash
docker exec -it ancient-backend python ingest.py
```

### 4. Open the Web Interface
Once the data ingestion is complete, open your browser and navigate to:

**[http://localhost:5173](http://localhost:5173)**

---

### Service Endpoints
- **Frontend Web UI:** `http://localhost:5173`
- **FastAPI Backend API:** `http://localhost:8000`
- **PGAdmin (Database GUI):** `http://localhost:5050`
