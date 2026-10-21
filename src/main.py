from contextlib import asynccontextmanager

if __name__ == '__main__':
    import os
    import sys
    from pathlib import Path

    project_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_dir))
    os.chdir(project_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.api import api_router
from src.core.config import get_settings
from src.db.session import AsyncSessionLocal, engine, init_db
from src.db.seed import seed

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        async with AsyncSessionLocal() as db:
            await seed(db)
        yield
    finally:
        await engine.dispose()


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version='1.0.0-real',
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/')
async def root():
    return {'name': settings.app_name, 'docs': '/docs'}

app.include_router(api_router, prefix='/api/v1')


if __name__ == '__main__':
    import uvicorn

    event_loop = 'auto'
    if sys.platform == 'win32' and settings.database_url.startswith('postgresql+psycopg:'):
        # Keep the selector loop in reloaded workers for Psycopg on Windows.
        event_loop = 'asyncio:SelectorEventLoop'
    uvicorn.run(
        'src.main:app',
        host='localhost',
        port=8000,
        loop=event_loop,
        reload=settings.app_debug,
        reload_dirs=[str(project_dir / 'src')] if settings.app_debug else None,
    )
