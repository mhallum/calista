"""Handlers"""

from pathlib import Path

from calista.adapters.filestore import AbstractFileStore
from calista.domain.model import ImageAggregate
from calista.service_layer.uow import AbstractUnitOfWork


def register_image(
    image_id: str,
    session_id: str,
    src_path: str,
    uow: AbstractUnitOfWork,
    files: AbstractFileStore,
):
    """Register an image file for processing.

    Args:
        src_path (str): The source path of the image file.
        image_id (str): The ID to assign to the image.
        files (AbstractFileStore): The file store to use for storing the image.
    """

    dest_rel = f"raw/{session_id}/{image_id}.fits"
    files.put(Path(src_path), dest_rel)

    with uow:
        if not (image := uow.images.get(image_id)):
            image = ImageAggregate(image_id=image_id)
        image.register(
            session_id=session_id, file_path=files.uri(dest_rel), header_meta={}
        )
        uow.images.add(image)
        uow.commit()
