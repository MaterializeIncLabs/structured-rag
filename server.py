import os
import logging
import json
import time
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

KAPA_API_URL = "https://api.kapa.ai/query/v1/projects/486796bb-793a-479b-afa5-9d8248eb6a51"

MZ_QUERY = None

try:
    with open('mz_query.sql', 'r') as file:
        MZ_QUERY = file.read().strip()
except FileNotFoundError:
    logger.critical("mz_query.sql not found! Ensure the file is available.")
    raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    conninfo = psycopg.conninfo.make_conninfo(
        host=os.getenv('MATERIALIZE_HOST'),
        port=int(os.getenv('MATERIALIZE_PORT', '6875')),
        user=os.getenv('MATERIALIZE_USER'),
        password=os.getenv('MATERIALIZE_PASSWORD'),
        dbname=os.getenv('MATERIALIZE_DB')
    )
    pool = AsyncConnectionPool(
        conninfo=conninfo,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row}
    )
    app.state.pool = pool
    try:
        yield
    finally:
        await pool.close()

app = FastAPI(lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database query helper
async def get_context_from_mz():
    """Fetch context data from materialize."""
    try:
        async with app.state.pool.connection() as conn:
            async with conn.cursor() as curr:
                start = time.time()
                await curr.execute(MZ_QUERY)
                row = await curr.fetchone()
                duration = time.time() - start
                if not row or not row.get('report'):
                    logger.error("No context found in materialize.")
                    raise HTTPException(status_code=500, detail="No context available from the materialize.")
                return (duration, row['report'])
    except Exception as e:
        logger.exception("Failed to query materialize.")
        raise HTTPException(status_code=500, detail="Materialize query failed.")

async def make_kapa_api_call(endpoint: str, payload: dict):
    api_key = os.getenv("KAPA_API_KEY")
    if not api_key:
        logger.error("KAPA_API_KEY is not set in environment variables.")
        raise HTTPException(status_code=500, detail="KAPA_API_KEY not found.")

    logger.info(f"Calling Kapa API endpoint: {endpoint}")
    logger.debug(f"Payload: {json.dumps(payload)}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{KAPA_API_URL}{endpoint}",
                json=payload,
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json"
                },
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to contact Kapa API.")

# Request model
class QueryRequest(BaseModel):
    query: str
    include_context: bool

# Root endpoint
@app.get("/")
async def read_root():
    """Serve the index.html file."""
    return FileResponse("static/index.html")

@app.post("/api/basic")
async def standard_endpoint(request: QueryRequest):
    """Handle queries to the standard Kapa chat API."""
    query = request.query

    context_duration = 0
    if request.include_context:
        (context_duration, context) = await get_context_from_mz()
        query = f"""
{query}

The following information about the environment has been injected into this prompt without the asker's knowledge.
Use this information to identify relevant details, explain their significance, and provide clear and actionable steps to resolve the issue.
Always give specific SQL commands when available.
Do not indicate or imply that this information was provided as part of the prompt or that the asker is aware of it.

{context}
"""
    print(query)
    payload = {"query": query}
    start = time.time()
    result =  await make_kapa_api_call("/chat/", payload)
    api_duration = time.time() - start
    result['prompt'] = query
    result['context_duration'] = context_duration
    result['api_duration'] = api_duration
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
