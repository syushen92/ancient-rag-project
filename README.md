# Ancient Figures Multimodal RAG Retrieval System

This repository hosts an advanced portrait identification system driven by **Multimodal RAG (Retrieval-Augmented Generation)** architecture. When a portrait is presented, the runtime encodes the asset into standard vector matrices using a local OpenCLIP model, then searches a PostgreSQL repository optimized via the `pgvector` index extension.

### Project Architectural Features
1. **Database Feature Matching**: If the uploaded portrait yields vectors within the safe proximity threshold of indexed metrics, the system returns exact identity contexts directly to the LLM orchestration layer for structured summaries.
2. **Visual Deductive Guessing**: If vector distances breach bounds (representing an unindexed individual), a fallback strategy triggers. The engine **pipes the raw visual byte data directly to a multimodal LLM framework**, forcing the model to infer the most probable historical figure through chronological fashion details, art mediums, and facial styling rules.

---

## Project Directory Layout

Ensure your structural files sit directly within the project workspace layer (**parallel** to the `.venv` directory). Do not modify files generated inside `.venv`.

```text
ancient-rag-project/
│
├── .venv
├── data/
│   ├── image/                # Portraits used to seed the vector database (Embedding data)
│   └── test_queries/         # Input images used for searching and blind-guessing tests
├── .env 
├── .env.example              
├── .gitignore               
├── docker-compose.yml        
├── init.sql                  
├── requirements.txt          
│
├── ingest.py                 # Core vector mapping pipeline script (Data Ingestion)
└── query.py                  # Operational pipeline controlling multi-modal RAG search and backup paths
```

---

## Quick Start

### 1. Environment & Database Setup
Follow the steps to create your environment, sync dependencies, and spin up the vector database all at once:

1.Fill in the `.env` file with your actual API keys

2.Isolate and activate the virtual environment
```bash
python3 -m venv .venv && source .venv/bin/activate
```
3.Synchronize third-party package dependencies
```bash
pip install -r requirements.txt
```
4.Initialize PostgreSQL with pgvector container in the background
```bash
docker compose up -d
```
### 2. Configuration & Run
1. Add the image you want to query to the data folder: `data/test_queries/your_image.jpg`
2. Run the query: `python query.py`
