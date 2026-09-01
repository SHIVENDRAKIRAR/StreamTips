from fastapi import FastAPI

from app.routers import auth, users, public

app = FastAPI(title="StreamTips API", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(public.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
