from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from app.api.v1.router import api_router
from app.services.git_service import GitService


logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.ENV} environment...")
    logger.info(f"Working directory: {settings.WORK_DIR}")
    logger.info(f"Data directory: {settings.DATA_DIR}")
    logger.info(f"Repos directory: {settings.REPOS_DIR}")
    
    GitService.initialize()
    logger.info("GitService 自动清理和监控任务已启动")
    
    yield
    
    logger.info("Shutting down gracefully...")
    GitService.shutdown()
    
    for task_id, task in list(GitService.process_registry.items()):
        if task.status == "running" and task.process:
            try:
                task.process.terminate()
                logger.info(f"已终止 Git 进程: task_id={task_id}, pid={task.pid}")
            except Exception as e:
                logger.error(f"终止 Git 进程失败: task_id={task_id}, error={e}")


def create_app() -> FastAPI:
    app = FastAPI(
        title="GitPush API",
        description="GitPush Backend API",
        version="2.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(RequestIDMiddleware)
    
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    app.include_router(api_router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "environment": settings.ENV}
    
    @app.get("/ready")
    async def readiness_check():
        return {"status": "ready"}
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENV == "dev",
        log_level=settings.LOG_LEVEL.lower(),
    )
