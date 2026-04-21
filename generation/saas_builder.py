# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""
saas_builder.py — SaaS project scaffolding

scaffold_project(name, description, features) → NVIDIA generates:
- main.py (FastAPI)
- index.html (Tailwind)
- requirements.txt
- README.md

Saves to ./workspace/projects/{name}/
register_as_tool: "build_saas" tool
"""
import logging
from pathlib import Path
from core.llm_gateway import call_nvidia

log = logging.getLogger("SaaSBuilder")
PROJECTS_DIR = Path("./workspace/projects")


class SaaSBuilder:
    def __init__(self):
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    def scaffold_project(self, name: str, description: str, features: list) -> dict:
        """
        Generate a complete SaaS project scaffold.
        Returns: {"success", "path", "files_created": []}
        """
        project_dir = PROJECTS_DIR / name
        project_dir.mkdir(parents=True, exist_ok=True)

        # Generate main.py (FastAPI)
        main_py = self._generate_main_py(name, description, features)
        (project_dir / "main.py").write_text(main_py)

        # Generate index.html (Tailwind)
        index_html = self._generate_index_html(name, description, features)
        (project_dir / "index.html").write_text(index_html)

        # Generate requirements.txt
        requirements = self._generate_requirements()
        (project_dir / "requirements.txt").write_text(requirements)

        # Generate README.md
        readme = self._generate_readme(name, description, features)
        (project_dir / "README.md").write_text(readme)

        log.info(f"[SAAS] Created project: {name}")
        return {
            "success": True,
            "path": str(project_dir),
            "files_created": ["main.py", "index.html", "requirements.txt", "README.md"]
        }

    def _generate_main_py(self, name: str, description: str, features: list) -> str:
        """Generate FastAPI main.py with auth and dashboard."""
        has_auth = "auth" in features or "login" in features
        auth_parts = []
        if has_auth:
            auth_parts = [
                "class User(BaseModel):",
                "    email: str",
                "    password: str",
                ""
            ]
        auth_model = "\n".join(auth_parts)
        auth_storage = "users_db = []\n" if has_auth else ""
        auth_routes = """
# Auth endpoints
@app.post("/api/auth/register")
async def register(user: User):
    users_db.append({"email": user.email, "password": user.password})
    return {"success": True, "message": "User registered"}

@app.post("/api/auth/login")
async def login(user: User):
    for u in users_db:
        if u["email"] == user.email and u["password"] == user.password:
            return {"success": True, "token": "demo_token_123"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

""" if has_auth else ""

        code = f'''"""
{name} - {description}
FastAPI backend with {', '.join(features)}
"""
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import json
from pathlib import Path

app = FastAPI(title="{name}", description="{description}")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
{auth_model}class Item(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str = "active"

# In-memory storage (replace with database in production)
items_db = []
{auth_storage}counter = 0

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("index.html")

@app.get("/api/health")
async def health():
    return {{"status": "ok", "service": "{name}"}}

@app.get("/api/items")
async def get_items():
    return {{"items": items_db}}

@app.post("/api/items")
async def create_item(item: Item):
    global counter
    counter += 1
    item.id = counter
    items_db.append(item.dict())
    return {{"success": True, "item": item}}

@app.get("/api/items/{{item_id}}")
async def get_item(item_id: int):
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.put("/api/items/{{item_id}}")
async def update_item(item_id: int, update: Item):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db[i].update(update.dict(exclude_unset=True))
            return {{"success": True, "item": items_db[i]}}
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/api/items/{{item_id}}")
async def delete_item(item_id: int):
    global items_db
    items_db = [i for i in items_db if i["id"] != item_id]
    return {{"success": True}}

{auth_routes}if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        return code

    def _generate_index_html(self, name: str, description: str, features: list) -> str:
        """Generate Tailwind CSS frontend."""
        features_html = ''.join([f'<div class="bg-gray-800 rounded-lg p-6"><h3 class="text-lg font-semibold text-white mb-2">{f.title()}</h3><p class="text-gray-400">{f} feature implemented and ready to use.</p></div>' for f in features[:3]])
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name}</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>body{{font-family:'Inter',sans-serif}}</style>
</head>
<body class="bg-gray-900 text-white min-h-screen">
<!-- Header -->
<nav class="bg-gray-800 border-b border-gray-700">
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
<div class="flex justify-between h-16">
<div class="flex items-center">
<span class="text-xl font-bold text-indigo-400">{name}</span>
</div>
<div class="flex items-center space-x-4">
<a href="#dashboard" class="text-gray-300 hover:text-white px-3 py-2">Dashboard</a>
<a href="#about" class="text-gray-300 hover:text-white px-3 py-2">About</a>
</div>
</div>
</div>
</nav>

<!-- Hero -->
<div class="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
<div class="text-center">
<h1 class="text-4xl font-bold text-white mb-4">{name}</h1>
<p class="text-xl text-gray-400 max-w-2xl mx-auto">{description}</p>
<div class="mt-8 space-x-4">
<button onclick="showDashboard()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-6 rounded-lg transition">Get Started</button>
<button onclick="showDocs()" class="bg-gray-700 hover:bg-gray-600 text-white font-medium py-3 px-6 rounded-lg transition">Documentation</button>
</div>
</div>
</div>

<!-- Features -->
<div class="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
<div class="grid grid-cols-1 md:grid-cols-3 gap-8">
{features_html}
</div>
</div>

<!-- Dashboard -->
<div id="dashboard" class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
<div class="bg-gray-800 rounded-lg shadow p-6">
<h2 class="text-2xl font-bold text-white mb-6">Dashboard</h2>
<div id="items">Loading...</div>
</div>
</div>

<script>
const API = window.location.origin;

async function loadItems() {{
try {{
const res = await fetch(`${{API}}/api/items`);
const data = await res.json();
const html = data.items.map(i => `
<div class="bg-gray-700 rounded p-4 mb-2 flex justify-between">
<div>
<h4 class="font-medium">${{i.title}}</h4>
<p class="text-sm text-gray-400">${{i.description || 'No description'}}</p>
</div>
<span class="text-sm text-green-400">${{i.status}}</span>
</div>
`).join('') || '<p class="text-gray-400">No items yet. Create one!</p>';
document.getElementById('items').innerHTML = html;
}} catch (e) {{
document.getElementById('items').innerHTML = '<p class="text-red-400">Failed to load</p>';
}}
}}

function showDashboard() {{ document.getElementById('dashboard').scrollIntoView({{behavior: 'smooth'}}); }}
function showDocs() {{ alert('API Docs: GET /api/items, POST /api/items'); }}

// Load on start
loadItems();
</script>
</body>
</html>'''

    def _generate_requirements(self) -> str:
        """Generate requirements.txt."""
        return '''fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
'''

    def _generate_readme(self, name: str, description: str, features: list) -> str:
        """Generate README.md."""
        features_list = chr(10).join([f"- {f.title()}" for f in features])
        return f'''# {name}

{description}

## Features

{features_list}

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py

# Open browser to http://localhost:8000
```

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/items` - List all items
- `POST /api/items` - Create new item
- `GET /api/items/{{id}}` - Get specific item
- `PUT /api/items/{{id}}` - Update item
- `DELETE /api/items/{{id}}` - Delete item

## Development

Built with FastAPI + Tailwind CSS
'''

    # ── GitHub Spark Style Builder ─────────────────────────────

    def build_from_description(self, description: str, stack: str = "react-fastapi") -> dict:
        """
        GitHub Spark equivalent: Natural language → complete working app.

        Example: "Build a meal planner that remembers dietary preferences"
        → Complete app in ./workspace/projects/{name}/
        Returns: {success, app_name, path, preview_url, files_created, design, next_steps}
        """
        import json
        import re
        import subprocess
        from core.llm_gateway import call_nvidia

        # Step 1: App design (architecture decision)
        design_prompt = f"""Design a complete web app: "{description}"

Return ONLY JSON:
{{
  "app_name": "snake_case_name",
  "description": "one line",
  "frontend": "React+TypeScript",
  "backend": "FastAPI+Python",
  "features": ["feature1", "feature2", "feature3"],
  "db_schema": [{{"table": "...", "columns": ["..."]}}],
  "api_endpoints": [{{"method": "GET/POST", "path": "/api/...", "description": "what it does"}}],
  "ai_features": ["chatbot|content_gen|recommendations|none"]
}}"""
        raw = call_nvidia([{"role": "user", "content": design_prompt}], max_tokens=800)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            return {"success": False, "error": "Design generation failed"}

        try:
            design = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid design JSON"}

        app_name = design.get("app_name", "myapp")
        project_dir = PROJECTS_DIR / app_name
        project_dir.mkdir(parents=True, exist_ok=True)

        # Step 2: Generate backend
        backend_prompt = f"""Generate a complete FastAPI backend for: {description}

Design: {json.dumps(design)}

Requirements:
- Complete working Python code
- SQLite with aiosqlite for persistence
- CORS enabled for localhost:3000
- All endpoints from the design
- Error handling and validation
- Include /api/health endpoint
- If AI features: include OpenAI-compatible /api/ai endpoint

Write ONLY Python code:"""
        backend_code = call_nvidia([{"role": "user", "content": backend_prompt}], max_tokens=3000)
        backend_code = re.sub(r'```python\n?|```\n?', '', backend_code).strip()
        (project_dir / "main.py").write_text(backend_code, encoding="utf-8")

        # Step 3: Generate frontend
        frontend_prompt = f"""Generate a complete single-file React+TypeScript app:

App: {description}
Backend: http://localhost:8000/api
Design: {json.dumps(design)}

Use:
- React 18 via CDN
- Tailwind CSS via CDN
- Dark modern UI
- Fetch API for backend calls

Write ONLY the HTML file:"""
        frontend_code = call_nvidia([{"role": "user", "content": frontend_prompt}], max_tokens=3000)
        frontend_code = re.sub(r'```html?\n?|```\n?', '', frontend_code).strip()
        (project_dir / "index.html").write_text(frontend_code, encoding="utf-8")

        # Step 4: Config files
        requirements = """fastapi
uvicorn
aiosqlite
python-multipart
httpx
"""
        (project_dir / "requirements.txt").write_text(requirements, encoding="utf-8")

        readme = f"""# {design.get('app_name','App')}

{design.get('description','')}

## Run

```bash
pip install -r requirements.txt
python main.py &
open index.html
```

## Features

"""
        for f in design.get('features', []):
            readme += f"- {f}\n"
        (project_dir / "README.md").write_text(readme, encoding="utf-8")

        # Step 5: Start dev server (optional)
        try:
            subprocess.Popen(
                ["python", "-m", "uvicorn", "main:app", "--port", "8000", "--reload"],
                cwd=str(project_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

        preview_url = f"file://{project_dir.resolve()}/index.html"

        return {
            "success": True,
            "app_name": app_name,
            "path": str(project_dir),
            "preview_url": preview_url,
            "backend_port": 8000,
            "files_created": ["main.py", "index.html", "requirements.txt", "README.md"],
            "design": design,
            "next_steps": [
                f"Open: {preview_url}",
                "Refine: 'make the header blue' or 'add user authentication'",
                "Deploy: 'deploy this app to GitHub'"
            ]
        }

    def refine_app(self, app_name: str, instruction: str) -> dict:
        """Iterative refinement: 'make the header blue' → update index.html"""
        import re
        from core.llm_gateway import call_nvidia

        project_dir = PROJECTS_DIR / app_name
        if not project_dir.exists():
            return {"success": False, "error": f"App '{app_name}' not found"}

        # Read current files
        current_files = {}
        for fname in ["main.py", "index.html"]:
            fpath = project_dir / fname
            if fpath.exists():
                current_files[fname] = fpath.read_text(encoding="utf-8")[:3000]

        prompt = f"""Refine this web app:

Instruction: "{instruction}"

Current files: {current_files}

Generate ONLY the CHANGED file content.
Return JSON: {{"file": "main.py or index.html", "content": "complete new file content"}}"""
        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=3000)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            return {"success": False, "error": "Refinement failed"}

        try:
            result = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON"}

        fname = result.get("file")
        content = result.get("content", "")
        if fname and content:
            (project_dir / fname).write_text(content, encoding="utf-8")
            return {"success": True, "updated": fname, "app_name": app_name}
        return {"success": False, "error": "No file returned"}

    def register_as_tool(self, registry):
        builder = self

        def build_saas(params: dict) -> dict:
            """Legacy scaffold method."""
            name = params.get("name", "")
            description = params.get("description", "A SaaS application")
            features = params.get("features", ["auth", "dashboard"])
            if not name:
                return {"success": False, "error": "Project name required"}
            return builder.scaffold_project(name, description, features)

        def build_app(params: dict) -> dict:
            """GitHub Spark style: NL → complete app."""
            desc = params.get("description", "")
            if not desc:
                return {"success": False, "error": "Describe your app"}
            return builder.build_from_description(desc, params.get("stack", "react-fastapi"))

        def refine_app(params: dict) -> dict:
            """Refine existing app with NL."""
            return builder.refine_app(
                params.get("app_name", ""),
                params.get("instruction", "")
            )

        registry.register(
            "build_saas",
            build_saas,
            "Generate a complete SaaS project scaffold with FastAPI backend and Tailwind frontend",
            {
                "name": {"type": "string", "required": True},
                "description": {"type": "string", "default": "A SaaS application"},
                "features": {"type": "list", "default": ["auth", "dashboard"]}
            },
            "generation"
        )

        # Spark-style tools
        registry.register(
            "build_app",
            build_app,
            "Build a complete web app from natural language description (GitHub Spark style). "
            "Generates React+TypeScript frontend + FastAPI backend + deploys locally.",
            {"description": {"type": "string", "required": True}},
            "spark"
        )

        registry.register(
            "refine_app",
            refine_app,
            "Refine an existing app with natural language: 'make header blue', 'add login'",
            {
                "app_name": {"type": "string", "required": True},
                "instruction": {"type": "string", "required": True}
            },
            "spark"
        )
