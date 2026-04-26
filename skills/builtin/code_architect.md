---
name: code_architect
version: 1.0.0
capabilities: [design, structure, best_practices, documentation]
tools_required: [file, code, memory]
telos_alignment: 0.92
author: ApeironAI Lab
---

# Code Architect Skill

## Purpose
Design and architect software solutions following best practices. Create well-structured, maintainable code with proper separation of concerns and clear documentation.

## Invocation Contract
Given a software requirement or problem, this skill:
1. Analyzes requirements and identifies key components
2. Designs appropriate architecture and data structures
3. Implements clean, well-documented code
4. Follows SOLID principles and design patterns
5. Provides usage examples and tests

## Output Format
Returns complete implementation with:
- Architecture overview and design rationale
- Well-structured code with clear interfaces
- Comprehensive docstrings and comments
- Usage examples
- Basic test cases
- Performance considerations

## Examples
**Input:** "Create a REST API for managing a todo list with CRUD operations"

**Output:**
```python
# todo_api.py
"""
REST API for todo list management.

Architecture:
- FastAPI for async HTTP handling
- Pydantic for request/response validation
- In-memory storage (easily replaceable with database)
- Clean separation of concerns
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="Todo API")

class TodoItem(BaseModel):
    """Todo item with validation."""
    id: Optional[int] = None
    title: str
    description: str = ""
    completed: bool = False
    created_at: Optional[datetime] = None

# Storage (replace with database in production)
todos: dict[int, TodoItem] = {}
next_id = 1

@app.post("/todos/", response_model=TodoItem)
def create_todo(todo: TodoItem):
    """Create a new todo item."""
    global next_id
    todo.id = next_id
    todo.created_at = datetime.utcnow()
    todos[next_id] = todo
    next_id += 1
    return todo

@app.get("/todos/", response_model=List[TodoItem])
def list_todos():
    """List all todo items."""
    return list(todos.values())

@app.get("/todos/{todo_id}", response_model=TodoItem)
def get_todo(todo_id: int):
    """Get a specific todo item."""
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todos[todo_id]

@app.put("/todos/{todo_id}", response_model=TodoItem)
def update_todo(todo_id: int, todo: TodoItem):
    """Update a todo item."""
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo.id = todo_id
    todos[todo_id] = todo
    return todo

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    """Delete a todo item."""
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    del todos[todo_id]
    return {"message": "Todo deleted"}
```
