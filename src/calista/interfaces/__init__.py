"""Interfaces (application boundary) for CALISTA.

Defines framework-free application contracts: protocols/ABCs and small DTOs
shared by the service layer and adapters (e.g., providers/clients/buses,
clocks, ID generators). Business rules stay out of this package.

Dependency rule: this package is independent—do not import from any
`calista.*` modules. It may be imported by `calista.service_layer`,
`calista.adapters`, and `calista.bootstrap`.
"""
