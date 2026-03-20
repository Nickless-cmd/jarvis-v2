from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool
    app: str
    environment: str
