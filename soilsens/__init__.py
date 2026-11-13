"""SoilSens Phase 2 backend.

Layers (each can be replaced without touching the others or the UI):

    data       -> load USCRN hourly station arrays
    forecast   -> get_forecast(): 72 h background soil temperature + moisture, 5 depths
    physics    -> soil properties, cable catalogue, transient radial ground model
    rating     -> whole-horizon permissible current search
    pipeline   -> assess(): one call that runs a full case and returns tagged outputs

Every output value carries a provenance tag (see soilsens.provenance).
"""

__version__ = "0.2.0-phase2-skeleton"
