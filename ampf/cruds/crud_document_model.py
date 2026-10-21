from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseDocument(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    blob_name: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    content_type: str
