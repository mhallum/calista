"""Service layer handlers."""

import logging
from collections.abc import Callable

from calista.interfaces.catalog.errors import SiteNotFoundError, TelescopeNotFoundError
from calista.interfaces.catalog.site_catalog import SitePatch, SiteRevision
from calista.interfaces.catalog.telescope_catalog import (
    TelescopePatch,
    TelescopeRevision,
)
from calista.interfaces.unit_of_work import AbstractUnitOfWork

from . import commands

# pylint: disable=consider-using-assignment-expr

logger = logging.getLogger(__name__)


def publish_site_revision(
    cmd: commands.PublishSiteRevision, uow: AbstractUnitOfWork
) -> None:
    """Publish a site revision to the catalog (create-or-update, idempotent)."""

    site_code = cmd.site_code.upper()
    rev = SiteRevision(
        site_code=site_code,
        name=cmd.name,
        source=cmd.source,
        timezone=cmd.timezone,
        lat_deg=cmd.lat_deg,
        lon_deg=cmd.lon_deg,
        elevation_m=cmd.elevation_m,
        mpc_code=cmd.mpc_code,
    )

    with uow:
        head = uow.catalogs.sites.get(cmd.site_code)

        # If site exists and this would be a no-op, return idempotently.
        if head is not None and rev.get_diff(head) is None:
            logger.debug("PublishSiteRevision %s: no changes; noop", site_code)
            return

        expected = 0 if head is None else head.version
        uow.catalogs.sites.publish(rev, expected_version=expected)
        uow.commit()


def patch_site(cmd: commands.PatchSite, uow: AbstractUnitOfWork) -> None:
    """Apply a patch to the existing site head and publish a new revision."""

    site_code = cmd.site_code.upper()
    patch = SitePatch(
        name=cmd.name,
        source=cmd.source,
        timezone=cmd.timezone,
        lat_deg=cmd.lat_deg,
        lon_deg=cmd.lon_deg,
        elevation_m=cmd.elevation_m,
        mpc_code=cmd.mpc_code,
    )

    with uow:
        head = uow.catalogs.sites.get(cmd.site_code)
        if head is None:
            raise SiteNotFoundError(cmd.site_code)

        revision = patch.apply_to(head)
        if revision.get_diff(head) is None:
            logger.debug("PatchSite %s: no changes; noop", site_code)
            return

        uow.catalogs.sites.publish(revision, expected_version=head.version)


def publish_telescope_revision(
    cmd: commands.PublishTelescopeRevision, uow: AbstractUnitOfWork
) -> None:
    """Publish a telescope revision to the catalog (create-or-update, idempotent)."""
    # Implementation would go here

    telescope_code = cmd.telescope_code.upper()
    rev = TelescopeRevision(
        telescope_code=telescope_code,
        name=cmd.name,
        source=cmd.source,
        aperture_m=cmd.aperture_m,
    )
    with uow:
        head = uow.catalogs.telescopes.get(cmd.telescope_code)

        # If telescope exists and this would be a no-op, return idempotently.
        if head is not None and rev.get_diff(head) is None:
            logger.debug(
                "PublishTelescopeRevision %s: no changes; noop", telescope_code
            )
            return

        expected = 0 if head is None else head.version
        uow.catalogs.telescopes.publish(rev, expected_version=expected)
        uow.commit()


def patch_telescope(cmd: commands.PatchTelescope, uow: AbstractUnitOfWork) -> None:
    """Apply a patch to the existing telescope head and publish a new revision."""

    telescope_code = cmd.telescope_code.upper()
    patch = TelescopePatch(
        name=cmd.name,
        source=cmd.source,
        aperture_m=cmd.aperture_m,
    )

    with uow:
        head = uow.catalogs.telescopes.get(cmd.telescope_code)
        if head is None:
            raise TelescopeNotFoundError(cmd.telescope_code)

        revision = patch.apply_to(head)
        if revision.get_diff(head) is None:
            logger.debug("PatchTelescope %s: no changes; noop", telescope_code)
            return

        uow.catalogs.telescopes.publish(revision, expected_version=head.version)


COMMAND_HANDLERS: dict[type, Callable[..., None]] = {
    commands.PublishSiteRevision: publish_site_revision,
    commands.PatchSite: patch_site,
    commands.PublishTelescopeRevision: publish_telescope_revision,
    commands.PatchTelescope: patch_telescope,
}
