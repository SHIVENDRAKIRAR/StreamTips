from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, users, public, tips, webhooks, ws

app = FastAPI(title="StreamTips API", version="0.1.0")

# TODO tighten allow_origins to the real frontend domain before going live
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(public.router)
app.include_router(tips.router)
app.include_router(webhooks.router)
app.include_router(ws.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
