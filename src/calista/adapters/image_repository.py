"""image repositories."""

import abc

from calista.domain.model import ImageAggregate


class AbstractImageRepository(abc.ABC):
    """Abstract base class for image repositories."""

    def __init__(self):
        self.seen: set[ImageAggregate] = set()

    def add(self, image: ImageAggregate):
        """Add a new image to the repository."""
        self._add(image)
        self.seen.add(image)

    def get(self, image_id: str) -> ImageAggregate | None:
        """Get an image by its ID."""
        if image := self._get(image_id):
            self.seen.add(image)
            return image
        return None

    @abc.abstractmethod
    def _add(self, image: ImageAggregate):
        """Add a new image to the repository."""

    @abc.abstractmethod
    def _get(self, image_id: str) -> ImageAggregate | None:
        """Get an image by its ID."""
