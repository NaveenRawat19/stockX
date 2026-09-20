import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.graph.graph import run_research
from app.api.websocket_manager import ConnectionManager
from app.market_config import market_options
from app.models.responses import ResearchRequest, ResearchResponse


router = APIRouter()
manager = ConnectionManager()


@router.post("/research")
@router.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
	return ResearchResponse.model_validate(await run_research(request.model_dump()))


@router.get("/markets")
async def markets():
	return {"markets": market_options()}


async def _research_websocket(websocket: WebSocket):
	await manager.connect(websocket)
	try:
		request = ResearchRequest.model_validate(await websocket.receive_json())
	except WebSocketDisconnect:
		manager.disconnect(websocket)
		return
	except Exception as exc:
		await manager.send(websocket, {"type": "error", "message": str(exc)})
		await websocket.close(code=1003)
		manager.disconnect(websocket)
		return

	async def on_progress(stage: str, message: str, data: dict | None = None):
		await manager.send(websocket, {
			"type": "stage", "stage": stage, "message": message, "data": data
		})

	job = asyncio.create_task(run_research(request.model_dump(), on_progress=on_progress))
	try:
		await manager.send(websocket, {"type": "started"})
		while not job.done():
			try:
				await asyncio.wait_for(asyncio.shield(job), timeout=15)
			except asyncio.TimeoutError:
				await manager.send(websocket, {"type": "keepalive"})
		result = ResearchResponse.model_validate(await job)
		await manager.send(websocket, {"type": "complete", "data": result.model_dump(mode="json")})
	except WebSocketDisconnect:
		job.cancel()
		await asyncio.gather(job, return_exceptions=True)
	finally:
		manager.disconnect(websocket)
		if not job.done():
			job.cancel()
			await asyncio.gather(job, return_exceptions=True)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
	await _research_websocket(websocket)


@router.websocket("/research/ws")
async def research_websocket(websocket: WebSocket):
	await _research_websocket(websocket)
