from datetime import datetime
from mimetypes import guess_file_type
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    name: str
    content_type: Optional[str] = None


class DocumentPatch(BaseModel):
    name: Optional[str] = None
    content_type: Optional[str] = None


class DocumentUpdate(BaseModel):
    id: UUID
    name: str
    content_type: str


class Document(BaseModel):
    id: UUID
    name: str
    content_type: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, document_create: DocumentCreate) -> "Document":
        document_create_dict = document_create.model_dump()
        if not document_create_dict["content_type"]:
            content_type, _ = guess_file_type(document_create.name)
            if not content_type:
                content_type = "application/octet-stream"        
            document_create_dict["content_type"] = content_type
        return cls(
            id=uuid4(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            **document_create_dict,
        )

    def update(self, value_update: DocumentUpdate) -> None:
        for key, value in value_update.model_dump().items():
            setattr(self, key, value)
        self.updated_at = datetime.now()

    def patch(self, value_patch: DocumentPatch) -> None:
        patch_dict = value_patch.model_dump(exclude_unset=True, exclude_none=True)
        self.__dict__.update(patch_dict)
        self.updated_at = datetime.now()
