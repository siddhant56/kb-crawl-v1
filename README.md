# To run app run

uvicorn api:app --reload

# To trigger manual ingestion

curl -X POST http://localhost:8000/api/ingest

# To check ingestion status

curl http://localhost:8000/api/ingest/status
