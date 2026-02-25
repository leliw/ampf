from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict

from pydantic import BaseModel, Field


class StorageFormatFlags(BaseModel):
    """Flags for storage format."""
    save_new_format: bool = Field(default=False)
    """Whether to save data in the new format. If false, the old format will be used for saving data."""
    migrate_legacy_on_read: bool = Field(default=False)
    """Whether to migrate legacy data on read. If true, legacy data will be migrated to the new format."""


class VersionedBaseModel(BaseModel, ABC):
    CURRENT_VERSION: ClassVar[int] = 1  # Override in subclasses
    FORMAT_FLAGS: ClassVar[StorageFormatFlags] = StorageFormatFlags()

    v: int = Field(default=None, ge=1, description="Schema version from storage") # type: ignore

    def model_post_init(self, _) -> None:
        if self.v is None:
            self.v = self.__class__.CURRENT_VERSION

    @classmethod
    @abstractmethod
    def from_storage(cls, data: Dict[str, Any]):
        """Convert the data from storage format to the model instance.

        Args:
            data: The data to convert.
        Returns:
            The converted data.
        """
        return cls.model_validate(data)

    @abstractmethod
    def to_storage(self) -> Dict[str, Any]:
        """Convert the data to storage format.

        Returns:
            The converted data.
        """
        return self.model_dump(by_alias=True, exclude_none=True)
