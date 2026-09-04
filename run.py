import sys
import uvicorn

if __name__ == "__main__":
    # Ensure UTF-8 output encoding on Windows consoles
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    print("\n" + "="*60)
    print("  Starting NEXUS PULSE - Smart Market Watchlist")
    print("  Access the application at: http://localhost:8000")
    print("  API documentation at: http://localhost:8000/docs")
    print("="*60 + "\n")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
