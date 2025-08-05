from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DocumentBase(BaseModel):
    name: str
    content_type: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(DocumentBase):
    id: UUID


class Document(DocumentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class DocumentHeader(BaseModel):
    id: UUID
    name: str
    content_type: Optional[str] = None
    created_at: datetime

class DocumentPatch(BaseModel):
    name: Optional[str] = None
    content_type: Optional[str] = None