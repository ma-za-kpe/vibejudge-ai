# Auto-Update Documentation Hook

## Trigger
**Event:** On file save
**Pattern:** `src/models/*.py`

## Action
When Pydantic models are modified, automatically update the OpenAPI schema documentation to keep the API specification in sync with the code.

## Instructions
When a Pydantic model file is saved (e.g., `src/models/hackathon.py`), perform the following:

1. **Update FastAPI OpenAPI schema:**
   - Ensure `src/api/main.py` has correct model imports
   - Verify all route functions use updated type hints
   - Check that response_model parameters match current schemas

2. **Update inline documentation:**
   - Add/update docstrings in route handlers
   - Ensure example values in Field() definitions are accurate
   - Update any README or API documentation files

3. **Validate schema consistency:**
   - Run FastAPI's schema validation
   - Check for breaking changes in request/response models
   - Warn if public API contracts have changed

## Example

**File saved:** `src/models/hackathon.py`

**Action:**
```python
# Check if src/api/routes/hackathons.py needs updates
# Verify imports are correct
from src.models.hackathon import HackathonCreate, HackathonDetail

# Ensure route signatures match
@router.post("/hackathons", response_model=HackathonDetail)
async def create_hackathon(data: HackathonCreate):
    ...
```

**Generated update in:** `src/api/main.py`
```python
# Auto-updated OpenAPI metadata
app = FastAPI(
    title="VibeJudge AI API",
    description="AI-powered hackathon judging platform",
    version="1.0.0",
    # Schema automatically reflects latest models
)
```

## Benefits
- **Keeps docs in sync** with code changes
- **Prevents stale documentation** that confuses users
- **Maintains API contract** integrity
- **Reduces manual documentation** maintenance

## Configuration
- **Runs automatically** on model file saves
- **Checks OpenAPI** schema generation
- **Logs warnings** for breaking changes
