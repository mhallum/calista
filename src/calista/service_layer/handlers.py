"""Service layer handlers."""

import logging
from collections.abc import Callable

from calista.interfaces.catalog.errors import (
    InstrumentNotFoundError,
    SiteNotFoundError,
    TelescopeNotFoundError,
)
from calista.interfaces.catalog.facility_catalog import Facility
from calista.interfaces.catalog.instrument_catalog import (
    InstrumentPatch,
    InstrumentRevision,
)
from calista.interfaces.catalog.site_catalog import SitePatch, SiteRevision
from calista.interfaces.catalog.telescope_catalog import (
    TelescopePatch,
    TelescopeRevision,
)
from calista.interfaces.unit_of_work import AbstractUnitOfWork

from . import commands

# pylint: disable=consider-using-assignment-expr

logger = logging.getLogger(__name__)

# ============================================================================
#                   Site Catalog Management Handlers
# ============================================================================


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
        head = uow.catalogs.sites.get(site_code)

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
        head = uow.catalogs.sites.get(site_code)
        if head is None:
            raise SiteNotFoundError(site_code)

        revision = patch.apply_to(head)
        if revision.get_diff(head) is None:
            logger.debug("PatchSite %s: no changes; noop", site_code)
            return

        uow.catalogs.sites.publish(revision, expected_version=head.version)
        uow.commit()


# ============================================================================
#                Telescope Catalog Management Handlers
# ============================================================================


def publish_telescope_revision(
    cmd: commands.PublishTelescopeRevision, uow: AbstractUnitOfWork
) -> None:
    """Publish a telescope revision to the catalog (create-or-update, idempotent)."""

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
        uow.commit()


# ============================================================================
#                Instrument Catalog Management Handlers
# ============================================================================


def publish_instrument_revision(
    cmd: commands.PublishInstrumentRevision, uow: AbstractUnitOfWork
) -> None:
    """Publish an instrument revision to the catalog (create-or-update, idempotent)."""

    instrument_code = cmd.instrument_code.upper()
    rev = InstrumentRevision(
        instrument_code=instrument_code,
        name=cmd.name,
        source=cmd.source,
        mode=cmd.mode,
    )

    with uow:
        head = uow.catalogs.instruments.get(instrument_code)

        # If instrument exists and this would be a no-op, return idempotently.
        if head is not None and rev.get_diff(head) is None:
            logger.debug(
                "PublishInstrumentRevision %s: no changes; noop", instrument_code
            )
            return

        expected = 0 if head is None else head.version
        uow.catalogs.instruments.publish(rev, expected_version=expected)
        uow.commit()


def patch_instrument(cmd: commands.PatchInstrument, uow: AbstractUnitOfWork) -> None:
    """Apply a patch to the existing instrument head and publish a new revision."""
    instrument_code = cmd.instrument_code.upper()
    patch = InstrumentPatch(
        name=cmd.name,
        source=cmd.source,
        mode=cmd.mode,
    )

    with uow:
        head = uow.catalogs.instruments.get(instrument_code)
        if head is None:
            raise InstrumentNotFoundError(instrument_code)

        revision = patch.apply_to(head)
        if revision.get_diff(head) is None:
            logger.debug("PatchInstrument %s: no changes; noop", instrument_code)
            return

        uow.catalogs.instruments.publish(revision, expected_version=head.version)
        uow.commit()


# ============================================================================
#                Facility Catalog Management Handlers
# ============================================================================


def register_facility(cmd: commands.RegisterFacility, uow: AbstractUnitOfWork) -> None:
    """Register a new facility."""

    # This is technically redundant since the Facility model uppercases it,
    # but it's nice to have it here for logging and error messages.
    facility_code = cmd.facility_code.upper()  # pragma: no mutate

    facility = Facility(
        facility_code=facility_code,
        site_code=cmd.site_code,
        telescope_code=cmd.telescope_code,
        instrument_code=cmd.instrument_code,
    )

    with uow:
        if (
            registered_facility := uow.catalogs.facilities.get(facility_code)
        ) is not None and registered_facility == facility:
            logger.debug("RegisterFacility %s: already exists; noop", facility_code)
            return

        uow.catalogs.facilities.register(facility)
        uow.commit()


# ============================================================================
#                       Handler Registry
# ============================================================================


COMMAND_HANDLERS: dict[type, Callable[..., None]] = {
    commands.PublishSiteRevision: publish_site_revision,
    commands.PatchSite: patch_site,
    commands.PublishTelescopeRevision: publish_telescope_revision,
    commands.PatchTelescope: patch_telescope,
    commands.PublishInstrumentRevision: publish_instrument_revision,
    commands.PatchInstrument: patch_instrument,
    commands.RegisterFacility: register_facility,
}
