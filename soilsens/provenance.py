"""Provenance tags required by the synthesis doc (section 23.4).

Every number the app shows must say what kind of quantity it is.
"""

MEASURED = "measured"      # read directly from an instrument record (USCRN, Darmstadt)
SPECIFIED = "specified"    # taken from a datasheet / standard / user choice
ESTIMATED = "estimated"    # computed from a constitutive relation (e.g. Johansen)
FITTED = "fitted"          # learned from data (GBT, GRU)
SCENARIO = "scenario"      # an assumption chosen to explore "what if"
CALCULATED = "calculated"  # output of the physics model / search

ALL = [MEASURED, SPECIFIED, ESTIMATED, FITTED, SCENARIO, CALCULATED]


def tag(value, kind, source="", note=""):
    """Small helper so tables can show value + provenance side by side."""
    assert kind in ALL, kind
    return {"value": value, "provenance": kind, "source": source, "note": note}
