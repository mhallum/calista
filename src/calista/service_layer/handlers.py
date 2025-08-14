"""Handlers"""

from collections.abc import Callable
from pathlib import Path

from calista.adapters.filestore import AbstractFileStore
from calista.domain import commands
from calista.domain.model import ImageAggregate
from calista.service_layer.unit_of_work import AbstractUnitOfWork


def register_image(
    cmd: commands.RegisterImage,
    uow: AbstractUnitOfWork,
    files: AbstractFileStore,
):
    """Register an image file for processing."""

    dest_rel = f"raw/{cmd.session_id}/{cmd.image_id}.fits"
    files.put(Path(cmd.src_path), dest_rel)

    with uow:
        if not (image := uow.images.get(cmd.image_id)):
            image = ImageAggregate(image_id=cmd.image_id)
        image.register(
            session_id=cmd.session_id, file_path=files.uri(dest_rel), header_meta={}
        )
        uow.images.add(image)
        uow.commit()


COMMAND_HANDLERS: dict[type[commands.Command], Callable[..., None]] = {
    commands.RegisterImage: register_image,
}
