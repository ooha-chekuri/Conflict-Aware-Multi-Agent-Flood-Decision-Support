"""Conservative geographic matching without an implicit gazetteer."""
import re
from .models import Evidence

def normalize_place(value: str | None) -> str:
    if not value: return ""
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

def geographic_relevance(e: Evidence, requested_location: str | None, all_evidence: list[Evidence]):
    if requested_location is None:
        return 1.0, "unscoped_analysis", "No target location was supplied; evidence retains its own location and is not compared across places."
    target=normalize_place(requested_location); place=normalize_place(e.location)
    if place and place==target:
        return 1.0, "exact", "Evidence location exactly matches the requested location."
    hierarchy={normalize_place(k):normalize_place(v) for k,v in e.admin_hierarchy.items()}
    if target and target in hierarchy.values():
        return 0.75, "within_requested_area", "Evidence has an explicit administrative parent matching the requested area; it is broader or narrower evidence, not an exact match."
    # Location names alone do not establish village/block/district/basin containment.
    return 0.0, "uncertain", "No exact or explicitly declared administrative relationship establishes geographic relevance."
