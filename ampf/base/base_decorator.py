class BaseDecorator[T]:
    """Base decorator class."""

    def __init__(self, decorated: T) -> None:
        """Initialize the decorator with a decorated object.

        Args:
            decorated (T): The object to be decorated.
        """
        self.decorated = decorated

    def __getattr__(self, name):
        """Get attribute from the decorated object."""
        if hasattr(self.decorated, name):
            return getattr(self.decorated, name)
        else:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
