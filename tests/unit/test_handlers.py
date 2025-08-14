"""Testsuite for service layer command handlers"""

from collections.abc import Iterable
from pathlib import Path

from calista.adapters.filestore import AbstractFileStore
from calista.adapters.image_repository import AbstractImageRepository
from calista.domain import commands
from calista.domain.model import ImageAggregate
from calista.service_layer import handlers
from calista.service_layer.uow import AbstractUnitOfWork

# pylint: disable=too-few-public-methods


class FakeFileStore(AbstractFileStore):
    """A FileStore that does not persist anything."""

    def __init__(self, root: Path):
        """Initialize the fake file store with a root directory."""
        super().__init__(root)
        self.put_calls: list[tuple[Path, str]] = []  # list of (src, dest)
        self.get_calls: list[str] = []  # list of dest
        self.exists_calls: list[str] = []
        self.fake_exists: set[str] = set()  # simulate which files "exist"

    def put(self, src: Path, dest_rel: str):
        dest = self.root / dest_rel
        self.put_calls.append((src, str(dest)))
        self.fake_exists.add(dest_rel)

    def exists(self, dest_rel: str) -> bool:
        self.exists_calls.append(dest_rel)
        return dest_rel in self.fake_exists


class FakeImageRepository(AbstractImageRepository):
    """A fake image repository for testing purposes."""

    def __init__(self, images: Iterable[ImageAggregate] = ()):
        super().__init__()
        self._images: dict[str, ImageAggregate] = {}
        for image in images:
            self._images[image.image_id] = image

    def _add(self, image: ImageAggregate):
        self._images[image.image_id] = image

    def _get(self, image_id: str) -> ImageAggregate | None:
        return self._images.get(image_id, None)


class FakeUnitOfWork(AbstractUnitOfWork):
    """A fake unit of work for testing purposes."""

    def __init__(self):
        self.images = FakeImageRepository()
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        """Rollback the current transaction."""


def test_register_image_stores_file():
    """Test that registering an image stores it in the file store.

    The registered image should be stored in the raw directory under
    <session_id>/<image_id>.fits
    """
    files = FakeFileStore(Path("fake_store"))
    uow = FakeUnitOfWork()
    cmd = commands.RegisterImage(
        image_id="fake0001", session_id="session1", src_path="path/to/fake.fits"
    )

    handlers.register_image(
        cmd=cmd,
        uow=uow,
        files=files,
    )

    assert files.exists("raw/session1/fake0001.fits")


def test_register_image_updates_image_aggregate():
    """Test that registering an image updates the image aggregate."""
    files = FakeFileStore(Path("fake_store"))
    uow = FakeUnitOfWork()

    image_id = "fake0001"
    session_id = "session1"
    src_path = "path/to/fake.fits"

    cmd = commands.RegisterImage(
        image_id=image_id, session_id=session_id, src_path=src_path
    )

    handlers.register_image(
        cmd=cmd,
        uow=uow,
        files=files,
    )

    expected_raw_path = "fake_store/raw/session1/fake0001.fits"
    updated_image = uow.images.get(image_id)
    assert updated_image is not None
    assert updated_image.image_id == image_id
    assert updated_image.raw_path == expected_raw_path
    assert updated_image.registered is True


def test_register_image_commits_transaction():
    """Test that registering an image commits the transaction."""
    files = FakeFileStore(Path("fake_store"))
    uow = FakeUnitOfWork()

    cmd = commands.RegisterImage(
        image_id="fake0001", session_id="session1", src_path="path/to/fake.fits"
    )
    handlers.register_image(
        cmd=cmd,
        uow=uow,
        files=files,
    )

    assert uow.committed is True
