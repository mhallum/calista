![logo](logo.png)

**C**CD **A**nalyis and **L**ogging **I**nfrastructure for **S**cientific **T**raceable **A**rchives

> A traceable pipeline for CCD photometry and spectroscopy

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/mhallum/calista/actions/workflows/tests.yml/badge.svg)](https://github.com/mhallum/calista/actions)
[![codecov](https://codecov.io/gh/mhallum/calista/branch/main/graph/badge.svg)](https://codecov.io/gh/mhallum/calista)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen)](https://pre-commit.com/)
[![Status: WIP](https://img.shields.io/badge/status-WIP-yellow)](#)

CALISTA is a Python-based pipeline for ingesting, processing, and analyzing astronomical CCD images.
It is designed for professional and amateur astronomers who need a reproducible, event-driven system for photometric measurements.

## 🚧 Work in Progress

This project is currently under active development. Features and structure are evolving rapidly, and things may break or change frequently.
Feel free to explore, but it is not yet ready for general use.

## Architecture
CALISTA uses an **event sourcing** and **CQRS-inspired** architecture:
1. **Adapters** – Handle the outside world (FITS readers, DB connectors, file storage).
2. **Core domain** – Defines images, calibrations, measurements, and events.
3. **Service layer** – Coordinates commands and events via a message bus.
4. **Database** – Stores both raw events and derived read models.

This makes CALISTA **auditable**, **reproducible**, and **extensible**.


## License

This project is licensed under the [MIT License](LICENSE).
