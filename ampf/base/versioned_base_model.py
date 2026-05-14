from abc import ABC, abstractmethod
from typing import (
    Annotated,
    Any,
    ClassVar,
    Dict,
    Literal,
    Type,
    Union,
    get_args,
    get_origin,
)

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

    v: int = Field(default=None, ge=1, description="Schema version from storage")  # type: ignore

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


def resolve_versioned_class[T](clazz: Type[T], data: Dict[str, Any]) -> Type[T]:
    """Resolve the real class for a versioned model based on the discriminator field in the data.
    
    Args:
        clazz: The base class to resolve.
        data: The data to resolve.
    Returns:
        The real class.
    """
    origin = get_origin(clazz)

    # unwrap Annotated
    if origin is Annotated:
        base_type, *metadata = get_args(clazz)

        discriminator = None
        for m in metadata:
            if hasattr(m, "discriminator"):
                discriminator = m.discriminator
                break
    else:
        base_type = clazz
        discriminator = None

    if get_origin(base_type) is not Union:
        return base_type

    if not discriminator:
        raise ValueError("Discriminator not defined")

    discriminator_value = data.get(discriminator)
    if discriminator_value is None:
        raise ValueError(f"Missing discriminator field '{discriminator}'")

    for cls in get_args(base_type):
        field = cls.model_fields.get(discriminator)
        if field and get_origin(field.annotation) is Literal:
            if discriminator_value in get_args(field.annotation):
                return cls

    raise ValueError("No matching class found")
