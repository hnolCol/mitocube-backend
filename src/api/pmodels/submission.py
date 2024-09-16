from pydantic import BaseModel

class ExamplePModel(BaseModel):
    id: int
    name: str = "Jane Doe"
