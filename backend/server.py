import os
import uvicorn
from app.main import app
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    reload = not settings.is_production() and os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=reload)
