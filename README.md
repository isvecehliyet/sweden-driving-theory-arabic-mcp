# Sweden Driving Theory Arabic MCP

Read-only MCP server for ArabiskaKorkort.se.

## Tools
- `search_theory`
- `get_theory_page`
- `get_membership_plans`
- `get_free_theory_test`

## Local run
```bash
pip install -r requirements.txt
python server.py
```

MCP endpoint: `http://localhost:8000/mcp`  
Health endpoint: `http://localhost:8000/health`

## Render
Build command:
```text
pip install -r requirements.txt
```
Start command:
```text
python server.py
```

Optional environment variable:
- `ARABISKAKORKORT_API_BASE=https://arabiskakorkort.se/wp-json/ak-chatgpt/v1`
- `MCP_ALLOWED_HOSTS=your-service.onrender.com,your-service.onrender.com:*`
