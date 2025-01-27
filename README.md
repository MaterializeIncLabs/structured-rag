# Structured RAG Comparison Tool

This repository contains a sample application that demonstrates how to power Retrieval-Augmented Generation (RAG) workflows with real-time, structured data using Materialize. By combining the power of Materialize’s incremental view maintenance with your existing AI models, this application enables dynamic and low-latency access to fresh, queryable data—solving the challenges of stale data and costly transformations in traditional architectures. For a deeper dive into how Materialize enables real-time structured data for RAG workflows, check out our [blog post](https://materialize.com/blog/realtime-structured-data-for-rag/).

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
