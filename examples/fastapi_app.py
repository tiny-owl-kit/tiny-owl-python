import os

from fastapi import FastAPI, HTTPException

from tinyowl import TinyOwl
from tinyowl.integrations.asgi_middleware import TinyOwlASGIMiddleware

app = FastAPI()
app.add_middleware(
    TinyOwlASGIMiddleware,
    client=TinyOwl(
        api_key=os.environ["TINYOWL_API_KEY"],
        project_secret=os.environ["TINYOWL_PROJECT_SECRET"],
    ),
)


@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict[str, int]:
    if user_id > 100:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user_id}
