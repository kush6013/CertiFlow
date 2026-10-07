import uvicorn
import os

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "True").lower() in ("true", "1")
    print(f"🚀 Starting Bulk Certificate Generator on http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)
