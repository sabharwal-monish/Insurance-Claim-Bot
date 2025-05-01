from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import router

app = FastAPI()

# Serve uploaded images
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")

# Include routes
app.include_router(router)
