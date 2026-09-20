from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router


app = FastAPI(title="Stock Research Agent")
app.include_router(router, prefix="/api")
app.mount("/ui", StaticFiles(directory="ui"), name="ui")


@app.get("/", include_in_schema=False)
async def dashboard():
	return FileResponse("ui/index.html")
