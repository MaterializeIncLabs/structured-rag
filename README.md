# Structured RAG Comparison Tool

This application provides a web interface for comparing responses from a Large Language Model (LLM) with and without structured context data. It demonstrates the impact of providing contextual information on the quality and relevance of LLM responses.

## Prerequisites

- Python 3.11 or higher
- UV package manager (`pip install uv`)
- PostgreSQL database
- Kapa AI API key

## Installation

2. Create and activate a virtual environment using UV:
```bash
uv venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
uv pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your configuration:
```env
KAPA_API_KEY=
MATERIALIZE_HOST=
MATERIALIZE_USER=
MATERIALIZE_PASSWORD=
```

## Running the Application

1. Start the server:
```bash
python server.py
```

2. Open a web browser and navigate to:
```
http://localhost:8000
```

## Usage

1. Enter your query in the text box
2. Click "Submit Query" or use Ctrl/Cmd + Enter
3. View the responses:
   - Left panel: Response without context
   - Right panel: Response with context from Materialize 

The query used to fetch context is stored in mz_query.sql. 
Play around with this to see how different data can change the relevance of responses.
