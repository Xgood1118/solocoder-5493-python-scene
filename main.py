from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import scene, device, template
from app.services.trigger_engine import trigger_engine
from app.devices.manager import device_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await trigger_engine.start()
    yield
    await trigger_engine.stop()


app = FastAPI(
    title="智能家居场景联动系统",
    description="场景配置、触发器评估、动作执行引擎、冲突检测、模板市场",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scene.router, prefix="/api/v1")
app.include_router(device.router, prefix="/api/v1")
app.include_router(template.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": "智能家居场景联动系统",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
