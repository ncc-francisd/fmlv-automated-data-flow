"""Mini Freestyle (mini-freestyle.com) — very small pop-top caravans by Trigano VDL.

See `docs/adapters/mini-freestyle.md` for the survey. **The catalogue PDF is the only
source.** The model pages carry no figure at all and the site publishes no price, so a run
is two fetches: the home page, to rediscover the catalogue, and the catalogue itself.

**The manufacturer is `Trigano`, the display name `Mini Freestyle`.** Trigano is not a
unique `fmlv_manufacturer` — the NCC list also holds 187 Trigano/Silver and 278
Trigano/Atom, the last of which is already an adapter here. They coexist because the key is
`(manufacturer, display name, vehicle class)`, but a registry row saying `Mini Freestyle`
would find an empty baseline and propose every product as new.

**These are rigid caravans, not pop-ups**, settled by the requester on 7 October 2026. The
site calls them *pop top caravans* and describes a *pop-up roof*, and FMLV held
`type_pop_up` on all four rows — but FMLV's `Pop Up` means a folding camper, where a pop
*top* is a rigid caravan whose roof raises. Micro was considered and fails the naming half
of the two-part test: the word appears nowhere on the site.

**The catalogue's columns carry no heading.** Each spec table lays two models side by side
under photographs, and nothing in the text says which is which — so they are identified by
their overall length, which is unique across the range. FMLV's own figures confirm every
pairing to the millimetre.

**Four parsing traps, all real:**

* **`LInternal length`** — a stray `L` prefixes that row, and only that row.
* **`695/807`** — one model states two masses in running order where the others state one.
  The lower is taken, which is the base-vehicle rule.
* **`925*`** — the Silver page marks its masses *"values subject to confirmation"*.
* **Decimal commas** throughout, French-fashion: `3,95` is 3.95 m.

**No price is ever proposed.** There is none in the catalogue and none on the site; FMLV's
three prices came from somewhere else and this adapter cannot maintain them.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.adapters.base import ExtractedCaravan, Provenance
from src.fetch.browser import BrowserFetcher
from src.fetch.http import Fetcher
from src.fetch.pdf import extract_text
from src.product_model.caravan import Caravan
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_LAYOUTS",
    "FMLV_RANGE",
    "WITHDRAWN",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MODELS_BY_LENGTH",
    "VEHICLE_CLASS",
    "Specification",
    "catalogue_url",
    "collect",
    "parse_specifications",
]

BASE_URL = "https://www.mini-freestyle.com"
MANUFACTURER = "Trigano"
MANUFACTURER_DISPLAY_NAME = "Mini Freestyle"
VEHICLE_CLASS = VehicleClass.CARAVAN

#: FMLV files all four under one range. The site groups them as `Minis` and `Silver`, but
#: those are navigation headings — and `Silver` is a *different manufacturer* in the NCC
#: list (id 187), so borrowing the word would be worse than unhelpful.
FMLV_RANGE = "Mini"

#: The catalogue's columns are unlabelled, so a model is identified by its overall length
#: in metres, which is unique across the range. Confirmed against FMLV's own figures:
#: shipping, body, internal, width, berths and MTPLM all match on the three live products.
MODELS_BY_LENGTH: dict[str, str] = {
    "3,95": "270",
    "4,42": "300",   # on the Minis page
    "5,91": "442",
}

#: `4,42` appears on both pages — the 300 among the Minis and the 290 on the Silver page —
#: so the page decides, and only for that length.
SILVER_PAGE_LENGTHS: dict[str, str] = {"4,42": "290"}

#: A model the maker says is **out of the range, while still publishing it**. Mapped to
#: the reason, which is narrated on every run — because the evidence for dropping it is a
#: sentence in an email and the evidence against it is right there in the catalogue, so
#: the next person to look will see a model being thrown away for no visible cause.
#:
#: `docs/adapters/README.md`: the manufacturer's own word outranks their website.
WITHDRAWN: dict[str, str] = {
    "442": (
        "Mini Freestyle told the requester on 9 October 2026 that the 442 is no longer in "
        "the range. It is still on their website and still in the catalogue this adapter "
        "reads, so the contradiction is theirs — but what they say about their own range "
        "settles it, and it is not to be uploaded as a 2027 model"
    ),
}

EXPECTED_LAYOUTS = 3

#: One range, so `--range` still works the way every other adapter allows.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (("mini", FMLV_RANGE),)


def catalogue_url(home_html: str) -> str | None:
    """The catalogue's address, **read from the page and never constructed**.

    Its folder carries a year — `files/2026/` — and the file its own, so the two disagree
    already and both will move. The hrefs on this site are **relative**, which is the trap:
    dropping the `files/` prefix gives a URL that returns a 404 page rather than a PDF.
    """
    hrefs = [
        htmllib.unescape(h) for h in re.findall(r'href="([^"]+\.pdf)"', home_html, re.I)
    ]
    if not hrefs:
        return None
    # The site links exactly one PDF, so any of them is the catalogue. Where several ever
    # appear, prefer the one that says so rather than whichever came first in the markup.
    href = next((h for h in hrefs if "catalog" in h.lower()), hrefs[0])
    if href.startswith("http"):
        return href
    return f"{BASE_URL}/{href.lstrip('/')}"


@dataclass(frozen=True)
class Specification:
    """One model's column of the catalogue's spec table."""

    model: str
    berths: int | None = None
    shipping_length_mm: int | None = None
    exterior_body_length_mm: int | None = None
    internal_length_mm: int | None = None
    overall_width_mm: int | None = None
    #: The roof **closed**, which is the towing height — the figure Freedom settled on.
    height_mm: int | None = None
    #: The internal height. FMLV held the roof-*open* height here on all four rows, which
    #: is a different measurement entirely.
    headroom_mm: int | None = None
    awning_length_mm: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    empty_weight_kilograms: int | None = None

    @property
    def derived_payload_kilograms(self) -> int | None:
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


#: `(label, field, unit)`. The `LInternal` row really does carry a stray `L`.
_ROWS: tuple[tuple[str, str, str], ...] = (
    (r"BERTHS", "berths", "count"),
    (r"Overall length", "shipping_length_mm", "m"),
    (r"External body length", "exterior_body_length_mm", "m"),
    (r"L?Internal length", "internal_length_mm", "m"),
    (r"Internal height", "headroom_mm", "m"),
    (r"Overall width", "overall_width_mm", "m"),
    (r"Overall height \(roof closed\)", "height_mm", "m"),
    (r"Awning length [^\n]*?", "awning_length_mm", "m"),
    (r"Empty weight", "empty_weight_kilograms", "kg"),
    (r"Mass in running order", "mro_kilograms", "kg"),
    (r"Max authori[sz]ed weight", "mtplm_kilograms", "kg"),
)


def _value(raw: str, unit: str) -> int | None:
    """One cell. `3,95` is metres; `925*` is kilograms; `695/807` takes the lower."""
    cleaned = raw.strip().rstrip("*").strip()
    if not cleaned or cleaned == "-":
        return None
    # Two figures for one model: the base vehicle, which is the lower.
    if "/" in cleaned:
        cleaned = min(cleaned.split("/"), key=lambda part: float(part.replace(",", ".")))
    cleaned = cleaned.strip().rstrip("*")
    try:
        number = float(cleaned.replace(",", "."))
    except ValueError:
        return None
    if unit == "m":
        return round(number * 1000)
    return round(number)


def parse_specifications(page_text: str, *, silver: bool) -> list[Specification]:
    """The two models on one catalogue page, read column by column.

    `silver` tells the `4,42` column apart: it is the 300 on the Minis page and the 290 on
    the Silver one, and nothing in the text distinguishes them.
    """
    cells: dict[str, list[str]] = {}
    for label, field, unit in _ROWS:
        match = re.search(rf"^\s*{label}\s+(\S+)\s+(\S+)\s*$", page_text, re.M)
        if match:
            cells[field] = [match.group(1), match.group(2)]

    lengths = cells.get("shipping_length_mm")
    if not lengths:
        return []

    found: list[Specification] = []
    for column, raw_length in enumerate(lengths):
        key = raw_length.strip()
        model = (SILVER_PAGE_LENGTHS if silver else {}).get(key) or MODELS_BY_LENGTH.get(key)
        if model is None:
            continue
        values: dict[str, int] = {}
        for _label, field, unit in _ROWS:
            raw = cells.get(field, [None, None])[column]
            if raw is None:
                continue
            value = _value(raw, unit)
            if value is not None:
                values[field] = value
        found.append(Specification(model=model, **values))
    return found


def _reconciles(spec: Specification) -> tuple[bool, str]:
    """What little redundancy the catalogue offers.

    **There is no published payload**, so `mtplm - miro` cannot be checked against
    anything — this is the weakest self-check of any adapter here and the survey says so.
    What *is* checkable is that the three masses are ordered and the payload is positive:
    an empty weight below the mass in running order, which is below the authorised maximum.
    A column read off by one breaks that ordering immediately.
    """
    empty, miro, mtplm = (
        spec.empty_weight_kilograms,
        spec.mro_kilograms,
        spec.mtplm_kilograms,
    )
    if miro is None or mtplm is None:
        return False, "no mass in running order or no maximum authorised weight"
    if mtplm <= miro:
        return False, f"MTPLM {mtplm} is not above the mass in running order {miro}"
    if empty is not None and empty > miro:
        return False, f"the empty weight {empty} exceeds the mass in running order {miro}"
    return (
        True,
        f"empty {empty} <= running order {miro} < authorised {mtplm}, "
        f"giving a payload of {mtplm - miro}kg",
    )


def build_extracted(spec: Specification, source_url: str, basis: str) -> ExtractedCaravan:
    """One Mini Freestyle caravan, with provenance on everything it proposes."""
    payload = spec.derived_payload_kilograms
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=FMLV_RANGE,
        model=spec.model,
        berths=spec.berths,
        # Published nowhere — not in the catalogue, not on the site.
        rrp_pounds=None,
        mtplm_kilograms=spec.mtplm_kilograms,
        mro_kilograms=spec.mro_kilograms,
        personal_effects_payload_kilograms=payload,
        optional_equipment_payload_kilograms=None,
        shipping_length_mm=spec.shipping_length_mm,
        exterior_body_length_mm=spec.exterior_body_length_mm,
        internal_length_mm=spec.internal_length_mm,
        overall_width_mm=spec.overall_width_mm,
        height_mm=spec.height_mm,
        headroom_mm=spec.headroom_mm,
        awning_length_mm=spec.awning_length_mm,
        body_type=CaravanBodyType.RIGID,
        twin_axle=False,
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(
            source_url=source_url, snippet=f"Mini {spec.model} — {snippet}"
        )

    record("manufacturer_range", f'range "{FMLV_RANGE}", which is how FMLV files all four')
    for field, label in (
        ("berths", "BERTHS"),
        ("shipping_length_mm", "Overall length"),
        ("exterior_body_length_mm", "External body length"),
        ("internal_length_mm", "Internal length"),
        ("overall_width_mm", "Overall width"),
        ("awning_length_mm", "Awning length"),
        ("mtplm_kilograms", "Max authorized weight"),
        ("mro_kilograms", "Mass in running order"),
    ):
        value = getattr(caravan, field)
        if value is not None:
            record(field, f"{value} from the catalogue's '{label}'")
    if spec.height_mm is not None:
        record(
            "height_mm",
            f"{spec.height_mm}mm — the catalogue's 'Overall height (roof closed)', the "
            f"towing height. It also states a roof-open height of 2330mm, which is a "
            f"different measurement",
        )
    if spec.headroom_mm is not None:
        record(
            "headroom_mm",
            f"{spec.headroom_mm}mm — the catalogue's 'Internal height'. **Not** the "
            f"roof-open height, which FMLV has been holding in this field",
        )
    if payload is not None:
        record(
            "personal_effects_payload_kilograms",
            f"{payload}kg — {basis}. The catalogue publishes no payload, so this is the "
            f"arithmetic, which is what FMLV holds for this brand",
        )
        record(
            "optional_equipment_payload_kilograms",
            "the catalogue publishes one payload and no optional-equipment allowance, so "
            "the whole of it is recorded as personal effects",
        )
    record(
        "body_type",
        "a rigid caravan. The maker calls these pop top caravans and the roof does raise, "
        "but FMLV's 'Pop Up' means a folding camper — a different vehicle. Micro fails the "
        "naming half of the test: the word appears nowhere on the site",
    )
    record("twin_axle", "single axle — every model is under 1100kg")
    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def collect(
    http: Fetcher,
    browser: BrowserFetcher,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every Mini Freestyle caravan, from the catalogue linked on the home page."""
    home = http.fetch(f"{BASE_URL}/en/").file_path.read_text(encoding="utf-8", errors="replace")
    url = catalogue_url(home)
    if url is None:
        msg = f"no catalogue PDF linked from {BASE_URL}/en/ — the only source is gone"
        raise RuntimeError(msg)
    on_progress(f"reading the catalogue: {url}")

    result = http.fetch(url)
    if result.status_code != 200:
        msg = f"the catalogue at {url} returned {result.status_code}"
        raise RuntimeError(msg)
    # **Page by page, never the whole document.** The two spec tables share every row
    # label, so a search across the joined text finds only the first table's — which
    # silently gave the 290 the 300's masses and lost two models entirely.
    extracted = extract_text(result.file_path)

    results: list[ExtractedCaravan] = []
    seen: set[str] = set()
    withdrawn_seen: set[str] = set()
    for page in (p.text for p in extracted.pages):
        if "Max authorized weight" not in page and "Max authorised weight" not in page:
            continue
        # Only the Silver page carries an awning row, and it is what tells the two `4,42`
        # columns apart — the 300 among the Minis, the 290 here.
        silver = "Awning length" in page
        for spec in parse_specifications(page, silver=silver):
            if spec.model in seen:
                continue
            if spec.model in WITHDRAWN:
                if spec.model not in withdrawn_seen:
                    withdrawn_seen.add(spec.model)
                    on_progress(f"{spec.model} — NOT COLLECTED: {WITHDRAWN[spec.model]}")
                continue
            reconciles, basis = _reconciles(spec)
            if not reconciles:
                on_progress(f"{spec.model} — DROPPED: {basis}")
                continue
            seen.add(spec.model)
            results.append(build_extracted(spec, url, basis))
            on_progress(
                f"{spec.model} — read: {spec.shipping_length_mm}mm over the hitch, "
                f"{spec.mtplm_kilograms}kg, {spec.berths} berth, "
                f"{spec.derived_payload_kilograms}kg payload"
            )

    on_progress(
        "NO PRICE IS PROPOSED. There is none in the catalogue and none on the site; FMLV's "
        "figures came from somewhere else and this adapter cannot maintain them."
    )
    on_progress(
        "THE SELF-CHECK IS WEAK AND THAT IS WORTH KNOWING. The catalogue publishes no "
        "payload, so there is no arithmetic to test a parse against — only that the empty "
        "weight, the mass in running order and the authorised maximum are in that order."
    )
    if len(results) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} models and collected {len(results)} — check "
            f"whether the range has changed"
        )
    on_progress(f"collected {len(results)} Mini Freestyle caravan(s)")
    return results
