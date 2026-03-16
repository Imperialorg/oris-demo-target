import logging
import os
import socket
from datetime import datetime
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

# Read configurations
DB_PORT = os.getenv("DB_PORT", "5432")
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://localhost:9200")
ELASTIC_USER = os.getenv("ELASTIC_USER", "elastic")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD", "changeme")

# Setup Elasticsearch URL
elastic_urls = [url.strip() for url in ELASTIC_URL.split(",") if url.strip()]
es_endpoint = elastic_urls[0] if elastic_urls else "http://localhost:9200"

class ElasticHandler(logging.Handler):
    def emit(self, record):
        try:
            doc = {
                "@timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage()
            }
            if record.exc_info:
                doc["exc_info"] = self.formatException(record.exc_info)
                doc["message"] += "\n" + doc["exc_info"]
                
            auth = HTTPBasicAuth(ELASTIC_USER, ELASTIC_PASSWORD) if ELASTIC_USER else None
            requests.post(
                f"{es_endpoint}/app-logs/_doc",
                auth=auth,
                json=doc,
                verify=False,
                timeout=2
            )
        except Exception as e:
            print(f"Failed to send log to Elasticsearch: {e}")

# Setup Logging
logger = logging.getLogger("dummy_app")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Elastic Handler
elastic_handler = ElasticHandler()
elastic_handler.setFormatter(formatter)
logger.addHandler(elastic_handler)

app = FastAPI(title="Dummy Target", description="A hackathon demo target application.")

@app.on_event("startup")
async def startup_event():
    logger.info("Dummy Target application starting up...")
    logger.info(f"Initial DB_PORT read from environment: {DB_PORT}")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    return response

@app.get("/api/users")
def get_users():
    logger.info("Accessing /api/users endpoint. Returning empty list.")
    return {"status": "ok", "users": []}

def perform_socket_connect(port: int):
    logger.debug(f"Attempting literal TCP socket connect to 127.0.0.1:{port}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    s.connect(("127.0.0.1", port))
    return s

def establish_tcp_session(port: int):
    # Simulated connection layer
    return perform_socket_connect(port)

def make_db_connection(port: int):
    # Simulated ORM layer
    return establish_tcp_session(port)

@app.get("/api/chaos/break-db")
def break_db():
    global DB_PORT
    logger.warning("Chaos Endpoint '/api/chaos/break-db' accessed!")
    logger.warning(f"Current nominal DB_PORT is: {DB_PORT}")
    
    # Deliberately change the running DB_PORT in memory
    DB_PORT = "5433"
    logger.error(f"FATAL MISCONFIGURATION INJECTED! DB_PORT altered in memory to {DB_PORT}")
    logger.info(f"Attempting fake database connection on port {DB_PORT} to simulate service failure...")
    
    try:
        # Cause a massive stack trace by falling through multiple simulated layers
        make_db_connection(int(DB_PORT))
    except Exception as e:
        logger.error("Database connection failed dramatically with ConnectionRefusedError!", exc_info=True)
        # Re-raise to produce the 500 error and stack trace
        raise e

    return {"status": "unexpected success", "message": "Expected a failure, but DB connected."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
