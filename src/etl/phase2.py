"""Phase 2 sources: registered here so the structure is in place, not implemented yet.

Each entry documents the source, its access method and what it would feed. `extract()` raises
until the source is implemented in its own module (src/etl/<key>.py), following the same
pattern as the phase 1 modules: dated raw cache, tidy frame, verified codes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingSource:
    key: str
    name: str
    access: str
    url: str
    feeds: str


PENDING = (
    PendingSource(
        "ivie_capital_stock", "Fundación BBVA-Ivie, El stock y los servicios del capital en España",
        "descarga de ficheros (Excel) sin API; URL exacta por verificar", "https://www.ivie.es/",
        "stock de capital público neto de España, por tipo de activo",
    ),
    PendingSource(
        "insee_capital_stock", "INSEE, comptes de patrimoine (stocks d'actifs non financiers des APU)",
        "API SDMX de INSEE (BDM) o ficheros de cuentas nacionales; serie exacta por verificar", "https://www.insee.fr/",
        "stock de capital público neto de Francia",
    ),
    PendingSource(
        "rail_safety", "Eurostat tran_sf_railac (accidentes ferroviarios por tipo)",
        "API Eurostat (código verificado el 2026-10-21: accident=TOTAL, COLLIS, DERAIL, LVLCROS…)",
        "https://ec.europa.eu/eurostat/databrowser/view/tran_sf_railac/default/table",
        "seguridad ferroviaria",
    ),
    PendingSource(
        "rail_reports", "ERA (Agencia Ferroviaria de la UE), Adif y SNCF Réseau: informes anuales",
        "PDF, extracción semiautomática", "https://www.era.europa.eu/",
        "inversión y mantenimiento ferroviario",
    ),
    PendingSource(
        "structures_inventory", "Inventarios públicos de puentes y presas (si existen)",
        "por determinar", "",
        "estado de puentes y presas",
    ),
)


def extract(key: str):
    raise NotImplementedError(f"{key} is a phase 2 source: see etl.phase2.PENDING")
