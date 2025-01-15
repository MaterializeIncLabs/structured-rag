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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

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

# Constants
KAPA_API_URL = "https://api.kapa.ai/query/v1/projects/486796bb-793a-479b-afa5-9d8248eb6a51/chat/custom/"

# Create connection pool on startup
@app.on_event("startup")
async def startup():
    # Create the connection pool
    conninfo = psycopg.conninfo.make_conninfo(
        host=os.getenv('MATERIALIZE_HOST'),
        port=int(os.getenv('MATERIALIZE_PORT', '6875')),
        user=os.getenv('MATERIALIZE_USER'),
        password=os.getenv('MATERIALIZE_PASSWORD'),
        dbname=os.getenv('MATERIALIZE_DB')
    )
    app.state.pool = AsyncConnectionPool(
        conninfo=conninfo,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row}
    )

@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()

async def get_context_from_db():
    """Query the database for context"""
    try:
        async with app.state.pool.connection() as conn:
            async with conn.cursor() as curr:
                # Replace this query with your actual query
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
    return FileResponse("static/index.html")

@app.post("/api/query")
async def query_kapa(request: QueryRequest):
    try:
        messages = []
        
        if request.include_context:
            messages.append({
                "role": "system",
                "content": SYSTEM_PROMPT
            })
        
        messages.append({
            "role": "context"
        })
        
        if request.include_context:
            try:
                context = await get_context_from_db()
                logger.debug(context)
                if context:
                    messages.append({
                        "role": "user",
                        "content": context
                    })
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
            "content": request.query
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
