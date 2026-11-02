import os

from flask import Flask, abort

from tinyowl import TinyOwl
from tinyowl.integrations.flask_middleware import TinyOwlFlask

app = Flask(__name__)
TinyOwlFlask(
    app,
    TinyOwl(
        api_key=os.environ["TINYOWL_API_KEY"],
        project_secret=os.environ["TINYOWL_PROJECT_SECRET"],
    ),
)


@app.get("/users/<int:user_id>")
def get_user(user_id: int) -> dict[str, int]:
    if user_id > 100:
        abort(404)
    return {"id": user_id}
