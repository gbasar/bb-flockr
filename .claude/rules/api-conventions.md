---
paths:
  - "src/flockr/api/**/*.py"
  - "src/flockr/handlers/**/*.py"
---
# Design Design Rules

- FastAPI handlers: use `async def` for any I/O operations
- Use Pydantic `BaseModel` for all request and response schemas — never raw dicts
- Use `pydantic-settings` `BaseSettings` for environment config
