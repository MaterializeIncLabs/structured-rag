import os
import logging
from typing import Optional
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

KAPA_API_URL = "https://api.kapa.ai/query/v1/projects/486796bb-793a-479b-afa5-9d8248eb6a51/chat/custom/"

try:
    with open('system_prompt.txt', 'r') as file:
        SYSTEM_PROMPT = file.read().strip()
except FileNotFoundError:
    logger.error("system_prompt.txt not found!")
    raise

try:
    with open('mz_query.sql', 'r') as file:
        MZ_QUERY = file.read().strip()
except FileNotFoundError:
    logger.error("mz_query.sql not found!")
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

app.mount("/static", StaticFiles(directory="static"), name="static")

async def get_context_from_db():
    """Query the database for context."""
    try:
        async with app.state.pool.connection() as conn:
            async with conn.cursor() as curr:
                await curr.execute(MZ_QUERY)
                row = await curr.fetchone()
                report = row['report'] if row else None
                logger.info(report)
                return report
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        raise

class QueryRequest(BaseModel):
    query: str
    include_context: bool

@app.get("/")
async def read_root():
    """Serve the index.html file."""
    return FileResponse("static/index.html")

@app.post("/api/query")
async def query_kapa(request: QueryRequest):
    """Handle queries to the Kapa API."""
    try:
        messages = []
        
        if request.include_context:
            messages.append({
                "role": "system",
                "content": SYSTEM_PROMPT
            })
        
        query = request.query
        
        if request.include_context:
            try:
                context = await get_context_from_db()
                if context:
                    query = f"""
LIVE CONTEXT:
{context}

USER QUERY:
{query}
"""
                else:
                    logger.warning("No context found in database")
            except Exception as e:
                logger.error(f"Failed to get context from database: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to retrieve context from database: {str(e)}"
                )
        
        messages.append({
            "role": "query",
            "content": query
        })
        
        payload = {
            "generation_model": "gpt-4o",
            "messages": messages
        }
        
        api_key = os.getenv("KAPA_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="KAPA_API_KEY not found in environment variables")
        
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Making request to Kapa API with payload: {payload}")
                response = await client.post(
                    KAPA_API_URL,
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
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Kapa API error: {e.response.text}"
                )
            except httpx.RequestError as e:
                logger.error(f"Request error occurred: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error making request to Kapa API: {str(e)}"
                )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
