<p align="center">
  <img src="images/logo.png" alt="CALISTA Logo" width="250"/>
</p>

**C**CD **A**nalyis and **L**ogging **I**nfrastructure for **S**cientific **T**raceable **A**rchives

> A traceable pipeline for CCD photometry and spectroscopy

**CALISTA** is a Python toolkit for processing CCD images and performing photometry, built on an **event-sourced** architecture.

- **Core ideas:** message bus (commands/events), Unit of Work, SQLAlchemy repositories, projections.
- **Use cases:** ingest FITS images, manage observing sessions, run aperture/PSF photometry, compare to catalog/comparison stars, export light curves.
