import os
import sys
import uvicorn

# Add current directory to path
sys.path.append(os.path.dirname(__file__))
# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

service_type = os.environ.get("SERVICE_TYPE", "ml")

print(f"🚀 Dispatcher: SERVICE_TYPE={service_type}")

if service_type == "backend":
    print("🚀 DEBUG: IMPORTING BACKEND_API NOW")
    print("🔄 Routing to Data API (backend_api.py)")
    try:
        from backend_api import app
    except ImportError:
        from backend.backend_api import app
else:
    print("🤖 Routing to ML API (ml_api_impl.py)")
    try:
        from ml_api_impl import app
    except ImportError:
        from backend.ml_api_impl import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting dispatched app on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
