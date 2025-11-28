from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import user_api
from app.api import chat as chat_api
from app.database import init_db
from app.utils.multi_writer import DorisQueue
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Marry System API", version="0.1.0")
STATIC_ROOT = os.getenv("STATIC_ROOT", "static")
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # init_db()
    DorisQueue.start()

# 路由挂载
app.include_router(user_api.router, prefix="/api/user", tags=["User"])
app.include_router(user_api.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat_api.router, prefix="/api/chat", tags=["chat"])

@app.get("/")
def root():
    return {"ok": True, "service": "Marry System API"}


# ✅ 关键部分：自动启动 uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",       # 模块路径
        host="0.0.0.0",       # 必须要写成 0.0.0.0 才能让外部访问（WSL、局域网）
        port=8000,            # 默认端口
        reload=True           # 开发模式下自动重载
    )
