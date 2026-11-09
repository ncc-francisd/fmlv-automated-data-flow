"""Mini Freestyle (mini-freestyle.com) — very small pop-top caravans by Trigano VDL.

See `docs/adapters/mini-freestyle.md` for the survey. **The catalogue PDF is the only
source.** The model pages carry no figure at all and the site publishes no price, so a run
is two fetches: the home page, to rediscover the catalogue, and the catalogue itself.

**The manufacturer is `Trigano`, the display name `Mini Freestyle`.** Trigano is not a
unique `fmlv_manufacturer` — the NCC list also holds 187 Trigano/Silver and 278
Trigano/Atom, the last of which is already an adapter here. They coexist because the key is
`(manufacturer, display name, vehicle class)`, but a registry row saying `Mini Freestyle`
would find an empty baseline and propose every product as new.

**The home page read is the FRENCH one, and that is not an accident.** On 9 November 2026
the English home page stopped linking any catalogue: the 2026 English edition is still
served at its old address but is unlinked and superseded, and the 2027 edition is linked
from `/fr/` alone. French is also the edition the document itself makes authoritative —
*"en cas de version multilingue, c'est la langue française qui fait foi"* — so this reads
French labels by choice rather than as a stopgap, and an English edition appearing later
is no reason to switch.

**These are rigid caravans, not pop-ups**, settled by the requester on 7 October 2026. The
site calls them *pop top caravans* and describes a *pop-up roof*, and FMLV held
`type_pop_up` on all four rows — but FMLV's `Pop Up` means a folding camper, where a pop
*top* is a rigid caravan whose roof raises. Micro was considered and fails the naming half
of the two-part test: the word appears nowhere on the site.

**Each table names its own columns, which the 2026 edition did not.** A line of model
numbers sits immediately above `NOMBRE DE PLACES`, so a model is identified by its heading
rather than by matching its overall length against a table of known lengths. That removed
the single most fragile thing in this adapter — but the discriminator is *position*, not
shape: `380 442` and `270 320290` both appear earlier on the page as artwork captions, and
only the line directly above `NOMBRE DE PLACES` is a real heading.

**The Silver line is read and then held back**, pending two questions the requester owns —
see `SILVER_HELD_BACK`.

**Three parsing traps, all real:**

* **`Poids à vide` is a prefix of `Poids à vide en ordre de marche`**, and `PTAC` of
  `Modification Administrative PTAC`. Both are safe only because a row matches a label
  followed by *numbers*: `en ordre de marche` is not a number, so the short label cannot
  swallow the long row. Do not relax the cell pattern to accept any non-space.
* **Decimal commas** throughout, French-fashion: `3,95` is 3.95 m.
* **`695/807`** — a model may state two masses where the others state one. The lower is
  taken, which is the base-vehicle rule. `Modification Administrative PTAC` carries the
  same shape and is deliberately not read: the settled rule takes the standard mass, never
  the chassis upgrade.

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
    "HOME_PATH",
    "WITHDRAWN",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "RANGE_BY_MODEL",
    "SILVER_RANGE",
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

#: The page that links the catalogue. **French, deliberately** — see the module docstring.
HOME_PATH = "/fr/"

#: The Minis: 270, 290, 320.
FMLV_RANGE = "Mini"

#: The Silver line, which **is a range of Mini Freestyle and not a separate brand** —
#: settled 9 November 2026 on the requester's screenshot of `/en/exclusives.html` and
#: confirmed in the page source.
#:
#: This reverses the reading of 7 October, when `Silver` looked like a navigation heading
#: that would collide with NCC id 187 (`Trigano` / `Silver`, holding the archived Trend
#: 350, 380 and 442). It is not a collision. The site's "Our caravans" page offers two
#: range tiles, each captioned **MINI FREESTYLE** above its name — `Mini` and `Silver` —
#: and the 2027 catalogue heads its second table *"Les SILVER…"* inside a Mini Freestyle
#: document. The display name stays `Mini Freestyle`; this is its second range.
#:
#: The archived id 187 rows are an older, separately-branded thing and are not touched.
SILVER_RANGE = "Silver"

#: Which range each model belongs to. The 290 moved from the Silver line into the Minis
#: for 2027, keeping its dimensions, so this cannot be derived from the model number.
RANGE_BY_MODEL: dict[str, str] = {
    "270": FMLV_RANGE,
    "290": FMLV_RANGE,
    "320": FMLV_RANGE,
    "380": SILVER_RANGE,
    "442": SILVER_RANGE,
}

#: A model held back from collection, mapped to the reason, which is narrated on every run
#: — because a model sitting in the catalogue and not in the output looks like a parsing
#: failure unless the reason is said out loud.
WITHDRAWN: dict[str, str] = {
    "442": (
        "HELD BACK ON THE REQUESTER'S RULING OF 9 OCTOBER 2026, WHICH NEW EVIDENCE MAY "
        "OVERTURN. Mini Freestyle told him the 442 was no longer in the range, and on the "
        "evidence then — their word against a 2026 catalogue that still listed it "
        "— that settled it. Since then they have published a 2027 catalogue that "
        "specifies the 442 in full, and their site lists it as 'Silver 442' in the current "
        "navigation. That is newer and more specific than the email, and it is the "
        "requester's ruling to revisit, not this adapter's. The figures are parsed and "
        "narrated every run, so nothing is lost by waiting. Delete this entry to collect it"
    ),
}

#: Said on every Silver product, because the range name is a judgement a reviewer should
#: see the basis for rather than take on trust.
_SILVER_RANGE_NOTE = (
    "range 'Silver'. Mini Freestyle sell two ranges under this one brand: their 'Our "
    "caravans' page offers a 'Mini' tile and a 'Silver' tile, each captioned MINI "
    "FREESTYLE, and the 2027 catalogue heads its second specification table 'Les SILVER'. "
    "This is NOT NCC id 187 ('Trigano' / 'Silver'), whose archived Trend 350, 380 and 442 "
    "are an older and separately branded range, and nothing here touches them"
)

#: Both Silver models' pages carry this, and it is worth a reviewer's eye before the range
#: is listed: a line being sold out is not a line being sold.
_SILVER_RUN_OUT_NOTE = (
    "Mini Freestyle's English pages for both Silver models read 'Range available while "
    "stocks last', so the whole Silver line may be a run-out rather than a 2027 range"
)

#: Four collected: the three Minis and the Silver 380. The Silver 442 is parsed and then
#: held back by `WITHDRAWN`, so it is not counted here.
EXPECTED_LAYOUTS = 4

#: One range, so `--range` still works the way every other adapter allows.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("mini", FMLV_RANGE),
    ("silver", SILVER_RANGE),
)


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


#: `(label pattern, field, unit)`, in the French edition's own wording.
#:
#: Order does not matter — each row is found by its own anchored search — but two pairs
#: only stay apart because a value must be a **number**: `Poids à vide` would otherwise
#: swallow `Poids à vide en ordre de marche`, and `PTAC` would swallow
#: `Modification Administrative PTAC`, which is the chassis upgrade and never the mass.
#:
#: `Hauteur hors tout` is the towing height. The 2026 edition published a roof-open height
#: beside it and FMLV has been holding that figure; the 2027 edition publishes only the
#: one, and it is the roof-closed figure (1,98 m against the old pair of 1,98 and 2,33).
_ROWS: tuple[tuple[str, str, str], ...] = (
    (r"Nombre de places", "berths", "count"),
    # The apostrophe survives extraction as a straight quote in this row and a curly one in
    # the prose on the same page, so it is matched as "any single character".
    (r"Longueur hors tout avec l.attelage", "shipping_length_mm", "m"),
    (r"Longueur extérieure carrosserie", "exterior_body_length_mm", "m"),
    (r"Longueur intérieure", "internal_length_mm", "m"),
    (r"Hauteur hors tout", "height_mm", "m"),
    (r"Hauteur intérieure", "headroom_mm", "m"),
    (r"Largeur hors tout", "overall_width_mm", "m"),
    (r"Poids à vide en ordre de marche", "mro_kilograms", "kg"),
    (r"Poids à vide", "empty_weight_kilograms", "kg"),
    (r"PTAC", "mtplm_kilograms", "kg"),
    # The label carries its own tolerance, `Développé auvent + -5%`, and that
    # tolerance contains a digit — so the label has to swallow it explicitly rather than
    # being separated from its cells by "everything up to the first number". The group is
    # optional so that dropping the tolerance leaves the row readable.
    (r"Développé auvent(?:.*?%)?", "awning_length_mm", "m"),
)

#: One cell: `3,95`, `925*`, `695/807`. Anchored to a digit so a label cannot match a row
#: whose values are prose — which is what keeps the two prefix pairs above apart.
_CELL = r"[0-9][0-9,./]*\*?"

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


#: The line that starts a specification table. The line **immediately above** it carries
#: that table's model numbers, and that position is the only reliable discriminator: the
#: same digits appear earlier on the page as artwork captions (`380 442`, `270 320290`).
_TABLE_MARKER = "NOMBRE DE PLACES"


def _models_above(lines: list[str], index: int) -> tuple[str, ...]:
    """The model numbers heading the table whose marker is at `index`."""
    if index == 0:
        return ()
    heading = lines[index - 1].strip()
    if not re.fullmatch(r"(?:\d{3}\s*)+", heading):
        return ()
    return tuple(re.findall(r"\d{3}", heading))


def parse_specifications(page_text: str) -> list[Specification]:
    """Every model in every specification table on the page.

    The 2027 edition puts both tables — the Minis and the SILVER line — on one page, where
    the 2026 edition had one per page. So tables are split on their own marker rather than
    by page, and each one's columns are named by the line above that marker.

    **A row whose cell count disagrees with its heading is not read at all**, because the
    pattern demands exactly as many cells as the heading has models. That is the cardinality
    failure `docs/adapters/README.md` warns about: a short row silently shifts every value
    one model to the left, and the result is a set of caravans carrying each other's weights
    that reconciles perfectly.
    """
    lines = page_text.splitlines()
    markers = [i for i, line in enumerate(lines) if line.strip() == _TABLE_MARKER]

    found: list[Specification] = []
    for position, index in enumerate(markers):
        models = _models_above(lines, index)
        if not models:
            continue
        stop = markers[position + 1] - 1 if position + 1 < len(markers) else len(lines)
        body = "\n".join(lines[index:stop])

        cells: dict[str, list[str]] = {}
        for label, field, _unit in _ROWS:
            pattern = rf"^\s*{label}\s+({_CELL}(?:\s+{_CELL}){{{len(models) - 1}}})\s*$"
            match = re.search(pattern, body, re.M)
            if match:
                cells[field] = match.group(1).split()

        for column, model in enumerate(models):
            values: dict[str, int] = {}
            for _label, field, unit in _ROWS:
                raw = cells.get(field)
                if raw is None:
                    continue
                value = _value(raw[column], unit)
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
        manufacturer_range=RANGE_BY_MODEL[spec.model],
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
            source_url=source_url,
            # The range, not a hardcoded "Mini": a Silver 380 labelled "Mini 380" names a
            # vehicle Mini Freestyle do not sell.
            snippet=f"{RANGE_BY_MODEL[spec.model]} {spec.model} — {snippet}",
        )

    if caravan.manufacturer_range == SILVER_RANGE:
        record("manufacturer_range", _SILVER_RANGE_NOTE)
        record("model", f"{spec.model} \u2014 {_SILVER_RUN_OUT_NOTE}")
    else:
        record(
            "manufacturer_range",
            f'range "{FMLV_RANGE}", which is how FMLV files the Minis',
        )
    # The catalogue is French, so each snippet quotes the row a reader will actually find
    # in it. Translating the label into English would send the next person looking for a
    # row that is not there.
    for field, label in (
        ("berths", "Nombre de places"),
        ("shipping_length_mm", "Longueur hors tout avec l'attelage"),
        ("exterior_body_length_mm", "Longueur extérieure carrosserie"),
        ("internal_length_mm", "Longueur intérieure"),
        ("overall_width_mm", "Largeur hors tout"),
        ("mtplm_kilograms", "PTAC"),
        ("mro_kilograms", "Poids à vide en ordre de marche"),
    ):
        value = getattr(caravan, field)
        if value is not None:
            record(field, f"{value} from the catalogue's {label!r} row")
    if caravan.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"{caravan.mtplm_kilograms}kg from the catalogue's 'PTAC' row. **Not** the "
            f"'Modification Administrative PTAC' row beside it, which offers an upgrade to "
            f"1200kg or 1300kg: the settled rule takes the standard mass, never the "
            f"chassis upgrade",
        )
    if caravan.awning_length_mm is not None:
        record(
            "awning_length_mm",
            f"{caravan.awning_length_mm}mm from the catalogue's "
            f"'Développé auvent + -5%' row, stated by the maker to that tolerance",
        )
    if spec.height_mm is not None:
        record(
            "height_mm",
            f"{spec.height_mm}mm — the catalogue's 'Hauteur hors tout', the towing "
            f"height. The 2026 edition published a roof-open height of 2330mm beside it "
            f"and FMLV has been holding that figure; the 2027 edition publishes this one "
            f"alone",
        )
    if spec.headroom_mm is not None:
        record(
            "headroom_mm",
            f"{spec.headroom_mm}mm — the catalogue's 'Hauteur intérieure'. "
            f"**Not** the roof-open height, which FMLV has been holding in this field",
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
    home_url = f"{BASE_URL}{HOME_PATH}"
    home = http.fetch(home_url).file_path.read_text(encoding="utf-8", errors="replace")
    url = catalogue_url(home)
    if url is None:
        # Worth being precise about, because this exact sentence appeared once when the
        # document had not gone anywhere: on 9 November 2026 the *English* home page
        # stopped linking one while `/fr/` still did. If this fires, check the other
        # language homepages before believing it.
        msg = (
            f"no catalogue PDF linked from {home_url} — the only source is gone. Check the "
            f"other language homepages before concluding it has been withdrawn"
        )
        raise RuntimeError(msg)
    on_progress(f"reading the catalogue: {url}")

    result = http.fetch(url)
    if result.status_code != 200:
        msg = f"the catalogue at {url} returned {result.status_code}"
        raise RuntimeError(msg)
    # Page by page still, although the 2027 edition puts both tables on one page: a table
    # is now split on its own `NOMBRE DE PLACES` marker, so one page carrying two costs
    # nothing, and a future edition going back to one per page needs no change here.
    extracted = extract_text(result.file_path)

    results: list[ExtractedCaravan] = []
    seen: set[str] = set()
    announced: set[str] = set()
    for page in (p.text for p in extracted.pages):
        for spec in parse_specifications(page):
            if spec.model in seen:
                continue
            if spec.model in WITHDRAWN:
                if spec.model not in announced:
                    announced.add(spec.model)
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
        "NO MAXIMUM NOSE WEIGHT IS PUBLISHED, in this catalogue or anywhere on the site, so "
        "the column is left blank rather than carried over."
    )
    on_progress(
        f"THE SILVER LINE IS A RANGE OF MINI FREESTYLE, not NCC id 187. {_SILVER_RANGE_NOTE}"
    )
    on_progress(f"NOTE ON THE SILVER LINE: {_SILVER_RUN_OUT_NOTE}.")
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
