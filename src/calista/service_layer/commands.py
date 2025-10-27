"""Module defining Commands."""

from dataclasses import dataclass

from calista.interfaces.catalog.unsettable import UNSET, Unsettable

# pylint: disable=too-many-instance-attributes


@dataclass(frozen=True)
class Command:
    """Base class for all commands."""


@dataclass(frozen=True)
class PublishSiteRevision(Command):
    """Command to publish a site revision to the catalog."""

    site_code: str
    name: str
    source: str | None
    timezone: str | None
    lat_deg: float | None
    lon_deg: float | None
    elevation_m: float | None
    mpc_code: str | None


@dataclass(frozen=True)
class PatchSite(Command):
    """Command to publish a patch revision to an existing site head in the catalog."""

    site_code: str
    name: str | None | Unsettable = UNSET
    source: str | None | Unsettable = UNSET
    timezone: str | None | Unsettable = UNSET
    lat_deg: float | None | Unsettable = UNSET
    lon_deg: float | None | Unsettable = UNSET
    elevation_m: float | None | Unsettable = UNSET
    mpc_code: str | None | Unsettable = UNSET
