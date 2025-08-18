from pydantic import BaseModel

class Schedule(BaseModel):
    query: str
    level: str | None = None
    deadline: str | None = None