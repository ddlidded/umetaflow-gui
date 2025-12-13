"""
Run the new FastAPI + Tailwind/Flowbite UI.

Usage (local):
  python3 run_web.py
"""

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "src.webapp.app:app",
        host="0.0.0.0",
        port=8501,
        reload=False,
    )

