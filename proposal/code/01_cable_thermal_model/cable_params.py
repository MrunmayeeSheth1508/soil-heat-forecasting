"""
cable_params.py — verified cable and installation parameters
All values traceable to full-text reads documented in proposal/notes/.
Tags: [V] = verified from source text; [I] = inferred.

Sources:
  - Bates 2021 PhD dissertation (notes/survey_bates_2021.md) [V]
  - Southwire SPEC 46319 rev 1.000.009 (standards_and_specs/) [V]
  - PG&E EDS 038193 / 062288 (standards_and_specs/) [V]
  - N-M Appendix A in Bates 2021 (Table A.1) [V]
"""
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Unit conventions throughout this module
# ---------------------------------------------------------------------------
# Lengths            : metres (m) unless noted
# Temperatures       : degrees Celsius (°C)
# Resistance         : Ω/m (electrical); thermal-Ω·m = K·m/W (thermal)
# Thermal resistivity: °C·cm/W  (industry convention; 1 °C·cm/W = 0.01 K·m/W)
# Current            : amperes (A)


def ohm_per_km_to_ohm_per_m(v): return v / 1000.0
def ft_per_kft_to_m(v):         return v * 0.3048          # 1 ft = 0.3048 m
def inches_to_m(v):             return v * 0.0254
def cm_per_W_to_Km_per_W(v):    return v * 0.01            # 1 °C·cm/W = 0.01 K·m/W


# ---------------------------------------------------------------------------
# Reference installation — PG&E primary in 4-inch PVC Sch 40
# [V] PG&E EDS 038193 / 062288
# ---------------------------------------------------------------------------
@dataclass
class PGEInstallation:
    """PG&E distribution primary, 4-inch PVC Schedule 40 conduit."""
    min_cover_m:       float = inches_to_m(30)    # 30" min cover [V EDS 038193]
    conduit_od_m:      float = inches_to_m(4.500) # 4" PVC Sch 40 OD [V EDS 062288]
    conduit_id_m:      float = inches_to_m(3.961) # 4" PVC Sch 40 ID [V EDS 062288]
    # Cable centre depth = cover + conduit_od/2
    @property
    def cable_centre_depth_m(self) -> float:
        return self.min_cover_m + self.conduit_od_m / 2.0   # ≈ 0.819 m [I]

    # FTB thermal resistivity [V EDS 038193]
    ftb_rho_at_3pct_MC_Kcm_per_W:  float = 60.0   # high-strength, ≤ 60 [V]
    ftb_rho_at_0pct_MC_Kcm_per_W:  float = 75.0   # high-strength, ≤ 75 [V]

    # Conduit material thermal resistivity [V Bates 2021 Table A.1 / N-M Table 6]
    pvc_rho_Ccm_per_W: float = 480.0   # fiber/PVC duct [V]

    # Design ambient assumptions (Black Books) [V Bates 2021 Ch 2]
    ambient_temp_black_books_C: float = 20.0
    # Design soil RHO (NEC default) [V Bates 2021 Ch 2]
    nec_default_rho_Ccm_per_W:  float = 90.0


# ---------------------------------------------------------------------------
# Southwire 350 kcmil Cu — reference cable
# [V] Southwire SPEC 46319 rev 1.000.009 (3 Oct 2025)
# ---------------------------------------------------------------------------
@dataclass
class Southwire350kcmil:
    """Southwire 350 kcmil compact-strand Cu, 15 kV, 133% insulation level."""

    # Conductor
    conductor_material:      str   = "Cu"
    conductor_strands:       int   = 35              # [V]
    conductor_od_m:          float = inches_to_m(0.616)   # [V]

    # Insulation (NL-EPR, 220 mil, 133% level)
    insulation_material:     str   = "NL-EPR"
    insulation_thickness_m:  float = inches_to_m(0.220)   # [V]
    od_over_insulation_m:    float = inches_to_m(1.102)   # [V]

    # Shield (copper tape, 5 mil, 25% overlap)
    shield_material:         str   = "Cu tape"
    shield_thickness_m:      float = inches_to_m(0.005)   # [V]
    od_over_shield_m:        float = inches_to_m(1.162)   # [V]

    # Jacket (PVC, 80 mil)
    jacket_material:         str   = "PVC"
    jacket_thickness_m:      float = inches_to_m(0.080)   # [V]
    overall_od_m:            float = inches_to_m(1.342)   # [V]

    # Electrical resistance [V]
    rdc_25C_ohm_per_m:  float = ohm_per_km_to_ohm_per_m(0.031 / 0.3048)
    # Southwire quotes 0.031 Ω/1000 ft at 25°C → convert to Ω/m
    # 0.031 Ω/1000ft ÷ 304.8 m/1000ft = 1.017e-4 Ω/m
    rac_90C_ohm_per_m:  float = ohm_per_km_to_ohm_per_m(0.043 / 0.3048)

    # Temperature limits [V]
    temp_normal_C:    float = 105.0
    temp_emergency_C: float = 140.0
    temp_shortckt_C:  float = 250.0

    # Thermal resistivities [V Bates 2021 Table A.1 / N-M Table 6]
    insulation_rho_Ccm_per_W: float = 350.0   # EPR [V]
    jacket_rho_Ccm_per_W:     float = 500.0   # PVC [V]

    # NEC ampacity (for reference) [V Southwire SPEC 46319]
    nec_ampacity_in_duct_90C_A:  float = 375.0
    nec_ampacity_in_duct_105C_A: float = 400.0
    nec_ampacity_in_air_90C_A:   float = 435.0
    nec_ampacity_in_air_105C_A:  float = 490.0


# ---------------------------------------------------------------------------
# Darmstadt MV150 Al trefoil cable
# [V] Verschaffel-Drefke et al. 2021, Energies 14, 7189 (paper text + Fig 2)
# ---------------------------------------------------------------------------
@dataclass
class DarmstadtMV150Al:
    """Darmstadt experiment MV150 Al trefoil cable (10 kV class)."""

    conductor_material:   str   = "Al"
    overall_od_m:         float = 0.034          # 34 mm [V]
    insulation_thickness_m: float = 0.0055       # 5.5 mm [V]
    sheath_thickness_m:   float = 0.0025         # 2.5 mm [V]

    rdc_20C_ohm_per_m:    float = ohm_per_km_to_ohm_per_m(0.206)   # [V]
    temp_limit_C:         float = 90.0           # MV limit [V]

    # Trefoil geometry — conductor centres (bundle bottom at 0.650 m)
    # Interpretation: 0.65 m = underside of upper-row trefoil bundle
    # [V figure-based, see notes/survey_darmstadt_2021.md — NOT an unambiguous
    # written definition; depth-reference sensitivity study required]
    bundle_bottom_depth_m:       float = 0.650
    lower_conductor_depth_m:     float = 0.650 - 0.017          # 0.633 m [I]
    upper_conductor_depth_m:     float = 0.650 - 0.017 - (3**0.5)*0.017  # 0.604 m [I]
    centroid_depth_m:            float = (2*0.633 + 0.604) / 3  # 0.623 m [I]


# ---------------------------------------------------------------------------
# Material thermal resistivities (Neher-McGrath Table 6 via Bates 2021)
# [V] Bates 2021 Appendix A Table A.1
# ---------------------------------------------------------------------------
class ThermalRho:
    """Thermal resistivity constants in °C·cm/W."""
    EPR_INSULATION   = 350.0   # EPR/XLPE insulation [V]
    PVC_JACKET       = 500.0   # PVC jacket [V]
    FIBER_PVC_DUCT   = 480.0   # Fiber or PVC conduit [V]
    NEC_DEFAULT_SOIL =  90.0   # NEC default soil [V]
    CONCRETE_DUCT_BANK = 90.0  # Concrete/earth [V Bates App A]


# ---------------------------------------------------------------------------
# Neher-McGrath Black Books design assumptions
# [V] Bates 2021 Ch 2, Ch 3
# ---------------------------------------------------------------------------
class BlackBooksAssumptions:
    AMBIENT_C        = 20.0    # °C ambient soil temp [V]
    MAX_CONDUCTOR_C  = 90.0    # °C conductor max [V]
    BURIAL_DEPTH_M   = inches_to_m(36)   # 36" depth [V]
    CABLE_SPACING_M  = inches_to_m(7.5)  # 7.5" spacing [V]
    SOIL_RHO_Ccm_W   = 90.0   # °C·cm/W [V]

class IEEE835Assumptions:
    AMBIENT_C        = 25.0    # °C [V]
    MAX_CONDUCTOR_C  = 90.0    # °C [V]
    BURIAL_DEPTH_M   = inches_to_m(36)
    CABLE_SPACING_M  = inches_to_m(7.5)
    SHIELDS          = "shorted"   # [V]
