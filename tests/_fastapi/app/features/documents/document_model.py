from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    name: str
    content_type: Optional[str] = None


class DocumentPatch(BaseModel):
    name: Optional[str] = None
    content_type: Optional[str] = None


class Document(BaseModel):
    id: UUID
    name: str
    content_type: str
    created_at: datetime
    updated_at: datetime
