"""Interface for the Facility Catalog."""

from __future__ import annotations

import abc
from dataclasses import dataclass

# pylint: disable=too-many-instance-attributes


@dataclass(frozen=True, slots=True)
class Facility:
    """A facility is a site-telescope-instrument combination recognized by CALISTA.

    Conventions:
      - facility_code: canonical uppercase usually something like "SITE/TELESCOPE/INSTRUMENT",
        or "SITE/INSTRUMENT" or "TELESCOPE/INSTRUMENT" when both SITE and TELESCOPE would be
        redundant (e.g., "LDT/DEVENY").
      - site_code, telescope_code, instrument_code: uppercase codes.
    """

    facility_code: str
    site_code: str
    telescope_code: str
    instrument_code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "facility_code", self.facility_code.upper())
        object.__setattr__(self, "site_code", self.site_code.upper())
        object.__setattr__(self, "telescope_code", self.telescope_code.upper())
        object.__setattr__(self, "instrument_code", self.instrument_code.upper())


class FacilityCatalog(abc.ABC):
    """Interface for facility namespace lookups and registration."""

    @abc.abstractmethod
    def get(self, facility_code: str) -> Facility | None:
        """Get an facility by its code.

        Args:
            facility_code: The canonical code (e.g."LDT/DEVENY").

        Returns:
            The facility if found, otherwise None.

        Note:
            `facility_code` lookup is case-insensitive; implementers should uppercase it.
        """

    @abc.abstractmethod
    def register(self, facility: Facility) -> None:
        """Register a new facility in the catalog.

        Args:
            facility: The facility to register.

        Raises:
            DuplicateFacilityError: If a facility with the same code already exists.
            InvalidFacilityError: If the facility references unknown site, telescope, or instrument.
        """
