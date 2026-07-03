import os
import uvicorn

if __name__ == "__main__":
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    
    # Load configuration from environment variables (useful for container deployment)
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload_str = os.getenv("RELOAD", "True").lower()
    reload = reload_str in ("true", "1", "yes", "y", "t")
    
    print("------------------------------------------------------------")
    print("Starting Google Maps Business Analysis & Transformation Platform...")
    print(f"Access the dashboard at: http://{host}:{port}")
    print("------------------------------------------------------------")
    
    # Run FastAPI server
    uvicorn.run("src.server:app", host=host, port=port, reload=reload)

