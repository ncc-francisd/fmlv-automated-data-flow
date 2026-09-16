"""Atom — four VW Crafter campervans, and the first brand FMLV holds nothing for.

`docs/adapters/atom.md` is the survey; this is what it decided.

**Every other adapter diffs against an FMLV export with rows in it.** Atom launched in
September 2026 and FMLV had none, so the baseline is empty and all four products are
correctly new until the first upload — see `config/manufacturers.csv`, which also records
that `Trigano` is not a unique manufacturer name.

The brand is Trigano's and the factory is Auto-Trail's, which is why the naming follows the
NCC's own `264, Swift Group Ltd, Ace Motorhomes` row: the legal manufacturer is the name and
the brand is the display name.

Three things are worth knowing:

* **it is a Vite single-page app.** Plain HTTP returns three kilobytes and the word "Atom",
  so this is one of the few adapters that genuinely needs `BrowserFetcher`;
* **the comparison table on `/models` is the source**, and the four model pages are the
  cross-check — one of which they fail, deliberately. See `_HEIGHT_FROM_THE_TABLE`;
* **the on-the-road price is not published anywhere on the site**, so it is carried here and
  has to be re-checked by hand. See `OTR_PRICES`.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.browser import BrowserFetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

#: Trigano own the brand; Auto-Trail build it. The NCC list already files a brand this way —
#: `264, Swift Group Ltd, Ace Motorhomes` — legal manufacturer as the name, brand as the
#: display name, its own id. Settled with the requester on 16 September 2026.
MANUFACTURER = "Trigano"
MANUFACTURER_DISPLAY_NAME = "Atom"

BASE_URL = "https://atommotorhomes.com"

#: The comparison table: every layout and every published figure, on one page.
MODELS_URL = f"{BASE_URL}/models"

#: The configurator, which is the only place the mass in running order appears.
CONFIG_URL = f"{BASE_URL}/atom-config"

#: Every launch model is a `VW Crafter 140PS FWD 6 speed Manual`. `VW`, never `Volkswagen` —
#: one name per company per role, for the filters.
BASE_VEHICLE = "VW"

#: 2710 mm clears the settled 2300 mm high-top threshold, and the requester confirmed it from
#: the photographs on 16 September 2026.
BODY_TYPE = BodyType.CAMPERVAN_HIGH_TOP

#: `(range, model)` for every layout, in the order the comparison table lists them.
#:
#: **FMLV renders a listing as display name + range + model**, which is why `pilote.py` names
#: its panel vans `Van` rather than `Pilote Van` — see commit `be7bf49`. So `Core` + `B`
#: renders as "Atom Core B", which is what the requester asked for on 16 September 2026.
#:
#: The letters are the layout, from the press pack: *"2 different layouts — rear bench seat
#: models and rear garage models"*. **B is bench and G is garage**, and the ranges are the
#: specification level — *"CORE — standard specification, ELEMENT — enhanced specification"*.
LAYOUTS: tuple[tuple[str, str], ...] = (
    ("Core", "B"),
    ("Core", "G"),
    ("Element", "B"),
    ("Element", "G"),
)

#: The comparison table's column heading for each layout, in the same order.
COLUMN_HEADINGS: tuple[str, ...] = ("Core B", "Core G", "Element B", "Element G")

#: The configurator's name for each layout, which is not the one FMLV uses.
#:
#: `Core 600B`, where the 600 is the 5.986 m length. The requester ruled this naming out on
#: 16 September 2026, but the configurator is still where the masses come from, so the two
#: have to be mapped.
CONFIG_NAMES: dict[tuple[str, str], str] = {
    ("Core", "B"): "Core 600B",
    ("Core", "G"): "Core 600G",
    ("Element", "B"): "Element 600B",
    ("Element", "G"): "Element 600G",
}

#: The on-the-road price, **which the website does not publish**.
#:
#: The configurator gives two figures and neither is this one: its headline is the launch
#: promotion the press pack describes, and its "Winter Sale Price" is the *ex works* price
#: mislabelled, which is why that one appears above the headline rather than below it. Only
#: page 14 of `ATOM - Press Presentation - Sept. 2026` carries the on-the-road column, and
#: the settled rule is that FMLV holds the manufacturer's headline OTR figure.
#:
#: **So these are typed in and cannot be checked by a run.** `_reconciles` cannot see them
#: and no fetch confirms them; they must be re-checked by hand whenever Atom move prices.
#: The pack promises *"a complete price brochure will be available to download from the ATOM
#: Motorhomes website"* — when that appears it becomes the source and this comes out.
#:
#: Supplied by the requester 16 September 2026. **The B costs more than the G in both
#: ranges**, which reads as inverted and is not.
OTR_PRICES: dict[tuple[str, str], int] = {
    ("Core", "B"): 62_600,
    ("Core", "G"): 61_940,
    ("Element", "B"): 68_925,
    ("Element", "G"): 68_260,
}

#: What the roster should come to.
#:
#: Stated three ways: the comparison table's four columns, `/manufacture`'s *"4 MODELS TO
#: CHOOSE FROM"*, and the press pack's two ranges times two layouts. The pack also promises
#: *"4 seat belt 4 berth models"* within a year and a 6.8 m wheelbase after the 6 m one, so
#: this count is expected to change — and will surface here rather than silently.
EXPECTED_LAYOUTS = 4

#: `(slug key, label)` for `--range`, matched against the FMLV range.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (("Core", "Core"), ("Element", "Element"))

_TAGS = re.compile(r"(?is)<(script|style)\b.*?</\1>")


def plain_text(page: str) -> str:
    """The page as one line, tags replaced by a single space and entities resolved."""
    stripped = re.sub(r"<[^>]+>", " ", _TAGS.sub(" ", page))
    return re.sub(r"\s+", " ", html.unescape(html.unescape(stripped))).strip()


#: The comparison table's own heading row, which is the roster.
TABLE_HEADER = re.compile(
    r"Specification\s+" + r"\s+".join(re.escape(head) for head in COLUMN_HEADINGS), re.I
)

#: A layout's entry in the configurator: its name, then its mass in running order.
#:
#: `Core 600B Length: 5.986m · Weight: 2720kg Engine: 140 PS` — the `Weight` is the mass in
#: running order, and `GVM 3,500 kg` beside it is the MTPLM the comparison table also gives.
CONFIG_WEIGHT = re.compile(
    r"(?P<name>(?:Core|Element)\s+600[BG])\b[^£]*?Weight:\s*(?P<mro>\d+)\s*kg", re.I
)

#: The configurator's gross vehicle mass, a second source for the MTPLM.
CONFIG_GVM = re.compile(r"GVM(?:\s+Limit)?\s+(?P<gvm>[\d,]+)\s*kg", re.I)


def _row(text: str, label: str, unit: str) -> list[int]:
    """One row of the comparison table: its label, then one figure per layout.

    Every row carries exactly `EXPECTED_LAYOUTS` figures, and that is the structural check
    — the four layouts publish identical dimensions, so a misaligned column would otherwise
    be invisible. A row that yields a different count means the table's shape has changed.

    **Exactly, not at least.** The trailing lookahead is what makes a *fifth* column fail
    rather than being quietly ignored, and Atom have said in writing that a fifth is coming:
    the press pack promises four-belt four-berth models within the year and a 6.8 m
    wheelbase after the 6 m one. Without it the run would collect the same four for ever and
    the roster count — the main defence here — would never fire.
    """
    pattern = re.compile(
        re.escape(label)
        + r"\s+"
        + r"\s*".join([rf"(\d+)\s*{unit}"] * EXPECTED_LAYOUTS)
        + rf"(?!\s*\d+\s*{unit})",
        re.I,
    )
    match = pattern.search(text)
    return [int(figure) for figure in match.groups()] if match else []


#: The rows read from the comparison table, as `field -> (label, unit)`.
#:
#: **`Height` comes from here and nowhere else.** The Core model pages print `2170mm` —
#: transposed digits — and the Element model pages print no height at all, putting a
#: `Wheel base, mm 3640` row where it would be. See `_HEIGHT_FROM_THE_TABLE`.
TABLE_ROWS: dict[str, tuple[str, str]] = {
    "berths": ("Berths", ""),
    "seats": ("Seatbelts", ""),
    "mh_length_mm": ("Length", "mm"),
    "mh_width_mm": ("Width", "mm"),
    "mh_height_mm": ("Height", "mm"),
    "mtplm_kilograms": ("Max Authorised Weight", "kg"),
}

#: Why the model pages are not consulted for the height.
_HEIGHT_FROM_THE_TABLE = (
    "the comparison table says 2710mm; the two Core model pages say 2170mm and the two "
    "Element pages publish no height at all. Transposed digits, and not cosmetic — 2170mm "
    "would file these below the 2300mm high-top threshold. The requester confirmed 2710mm "
    "from the photographs on 16 September 2026"
)


#: The model-page rows that must agree with the comparison table, as `field -> (row, unit)`.
#:
#: This is the real self-check, and it was not there until the requester pointed at the
#: `Living Space` and `Technical Data` panels on 16 September 2026: two independently
#: rendered sources for the same three figures, one per layout against one for all four.
#:
#: **Height is deliberately absent.** The two Core pages print 2170 mm against the table's
#: 2710 mm and the two Element pages print none at all, so checking it would warn every run
#: about a disagreement already settled. See `_HEIGHT_FROM_THE_TABLE`.
CROSS_CHECKED: dict[str, tuple[str, str]] = {
    "mh_length_mm": ("Length", "mm"),
    "mh_width_mm": ("Width (excl. door mirrors)", "mm"),
    "mtplm_kilograms": ("Max. authorised weight", "kg"),
}


def cross_check(product: AtomProduct, rows: dict[str, str]) -> list[str]:
    """Where a layout's own page disagrees with the comparison table it came from.

    Returns one sentence per disagreement, for `on_progress`. A model page that is simply
    missing the row says nothing — the Element pages omit their height, and an absent row
    is not a contradiction.
    """
    notes: list[str] = []
    for field, (label, unit) in CROSS_CHECKED.items():
        published = rows.get(label)
        if published is None:
            continue
        figure = re.match(rf"\s*(\d+)\s*{unit}", published)
        if figure is None:
            continue
        table = getattr(product, field)
        if table is not None and int(figure.group(1)) != table:
            notes.append(
                f"the comparison table gives {table}{unit} for {field} and its own page "
                f"gives {figure.group(1)}{unit}. The table is taken; check which is right"
            )
    return notes


@dataclass(frozen=True)
class AtomProduct:
    """One layout, from the comparison table plus the configurator."""

    manufacturer_range: str
    model: str
    source_url: str
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    copy_lines: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def rrp_pounds(self) -> int | None:
        return OTR_PRICES.get((self.manufacturer_range, self.model))

    @property
    def mh_payload_kilograms(self) -> int | None:
        """Derived: MTPLM minus the mass in running order. Atom publish no payload."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def read_comparison_table(page: str) -> list[AtomProduct]:
    """Every layout on the comparison table, in the order it lists them."""
    text = plain_text(page)
    if not TABLE_HEADER.search(text):
        return []

    rows = {
        field: _row(text, label, unit) for field, (label, unit) in TABLE_ROWS.items()
    }
    if any(len(values) != EXPECTED_LAYOUTS for values in rows.values()):
        return []

    return [
        AtomProduct(
            manufacturer_range=manufacturer_range,
            model=model,
            source_url=MODELS_URL,
            mh_passenger_seats_inc_driver=rows["seats"][index],
            berths=rows["berths"][index],
            mh_length_mm=rows["mh_length_mm"][index],
            mh_width_mm=rows["mh_width_mm"][index],
            mh_height_mm=rows["mh_height_mm"][index],
            mtplm_kilograms=rows["mtplm_kilograms"][index],
        )
        for index, (manufacturer_range, model) in enumerate(LAYOUTS)
    ]


def read_running_order(page: str) -> dict[str, int]:
    """`configurator name -> mass in running order`, from the configurator's first step."""
    text = plain_text(page)
    return {
        re.sub(r"\s+", " ", match.group("name")).strip(): int(match.group("mro"))
        for match in CONFIG_WEIGHT.finditer(text)
    }


def read_gross_vehicle_mass(page: str) -> int | None:
    """The configurator's `GVM`, which is a second source for the MTPLM."""
    match = CONFIG_GVM.search(plain_text(page))
    return int(match.group("gvm").replace(",", "")) if match else None


def _reconciles(product: AtomProduct) -> tuple[bool, str]:
    """`(ok, why not)` — what little arithmetic this source allows.

    **Atom publish no payload**, so `MTPLM - MRO` is the only route to one rather than a
    check on it, and the identity `payload == MTPLM - MRO` is true by construction. That is
    the same weak position `mobilvetta.py` records, and it is stated rather than glossed.

    The real check is not arithmetic but corroboration, and it lives in `cross_check`: each
    layout's own page renders `Length`, `Width (excl. door mirrors)` and `Max. authorised
    weight` independently of the comparison table, so the two must agree.

    What is checkable here:

    * **the payload must be positive and sane.** A mass in running order read from the wrong
      layout, or a GVM read as a running order, shows up here immediately;
    * **every figure the table publishes must be present.** The four layouts share every
      dimension, so a column misalignment is invisible — but a row that failed to parse is
      not, and `read_comparison_table` refuses the whole table rather than half of it.

    The structural defences are stronger than the arithmetic: the roster is four, the
    comparison table's header names all four columns, and every row must carry four figures.
    """
    missing = [
        field
        for field, value in (
            ("length", product.mh_length_mm),
            ("width", product.mh_width_mm),
            ("height", product.mh_height_mm),
            ("MTPLM", product.mtplm_kilograms),
            ("berths", product.berths),
            ("seatbelts", product.mh_passenger_seats_inc_driver),
        )
        if value is None
    ]
    if missing:
        return False, f"the comparison table yielded no {', '.join(missing)}"

    if product.mro_kilograms is None:
        return True, ""
    payload = product.mh_payload_kilograms
    if payload is None or payload <= 0:
        return False, (
            f"its mass in running order ({product.mro_kilograms}kg) is not below its MTPLM "
            f"({product.mtplm_kilograms}kg), so one of the two has been read wrongly"
        )
    if payload > 1500:
        return False, (
            f"MTPLM {product.mtplm_kilograms}kg minus running order "
            f"{product.mro_kilograms}kg leaves {payload}kg of payload, which is too much "
            f"for a 3.5 tonne panel van and means a figure has been misread"
        )
    return True, ""


def _build_extracted_motorhome(product: AtomProduct) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field."""
    features = habitation.features_from(product.copy_lines)
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(BASE_VEHICLE),
        rrp_pounds=product.rrp_pounds,
        mro_kilograms=product.mro_kilograms,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_payload_kilograms=product.mh_payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        berths=product.berths,
        body_type=BODY_TYPE,
        # Habitation, from the layout's own page. Findings, never proposals.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        shower_toilet_separated=(
            features["shower_toilet_separated"].value
            if "shower_toilet_separated" in features
            else None
        ),
        bed_types=features["bed_types"].value if "bed_types" in features else [],
        microwave=features["microwave"].value if "microwave" in features else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str, url: str = MODELS_URL) -> None:
        provenance[field] = Provenance(
            source_url=url, snippet=f"{product.label} — {snippet}"
        )

    if product.mh_length_mm is not None:
        record("mh_length_mm", f"the comparison table's 'Length {product.mh_length_mm}mm'")
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"the comparison table's 'Width {product.mh_width_mm}mm'. The model pages label "
            f"it '(excl. door mirrors)', so this is the body and needs no adjustment",
        )
    if product.mh_height_mm is not None:
        record("mh_height_mm", f"'Height {product.mh_height_mm}mm' — {_HEIGHT_FROM_THE_TABLE}")
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"the comparison table's 'Seatbelts "
            f"{product.mh_passenger_seats_inc_driver}'. Two is right and low: the FAQ says "
            f"'two designated travelling seats', and the press pack promises four-belt "
            f"models only next year",
        )
    if product.berths is not None:
        record("berths", f"the comparison table's 'Berths {product.berths}'")
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"'Max Authorised Weight {product.mtplm_kilograms}kg', which the configurator "
            f"repeats as its GVM. Maximum authorised mass is the MTPLM",
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"the configurator's 'Weight: {product.mro_kilograms}kg' for the "
            f"{CONFIG_NAMES[(product.manufacturer_range, product.model)]}. It is the only "
            f"place Atom publish a running order",
            CONFIG_URL,
        )
    if product.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"derived as MTPLM {product.mtplm_kilograms}kg minus running order "
            f"{product.mro_kilograms}kg. Atom publish no payload, so nothing corroborates "
            f"this",
            CONFIG_URL,
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"£{product.rrp_pounds:,} on the road, from page 14 of Atom's September 2026 "
            f"press pack. **Not from the website**, which publishes only the ex works price "
            f"and a launch promotion — so this figure is carried in the adapter and has to "
            f"be re-checked by hand",
            BASE_URL,
        )
    record("body_type", f"a campervan at {product.mh_height_mm}mm, above the 2300mm high top")
    record("base_vehicle_manufacturer", "every launch model is a VW Crafter 140PS FWD")

    for field_name, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field_name] = Provenance(
            source_url=f"{BASE_URL}/models",
            snippet=f"{product.label} — its own page says {feature.snippet!r}{detail}",
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


#: One row of a model page's `Engine & Performance`, `Living Space` or `Technical Data` panel.
#:
#: **Atom render their specification as divs, not lists**, so `habitation.list_items` finds
#: only the twelve navigation entries and no equipment at all — which is how the first run
#: produced zero findings. The rows are properly structured underneath, though:
#:
#: ```html
#: <div class="spec-row"><span class="spec-row-l">Heating &amp; Hot Water</span>
#:                       <span class="spec-row-v ">Truma Combi Neo 4E</span></div>
#: ```
#:
#: So each row is recovered as `label value` — a clean line for `habitation`, and the
#: `Technical Data` rows double as the cross-check against the comparison table.
SPEC_ROW = re.compile(
    r'<div class="spec-row">\s*<span class="spec-row-l">(?P<label>.*?)</span>\s*'
    r'<span class="spec-row-v[^"]*">(?P<value>.*?)</span>',
    re.S,
)

#: One sentence of a model page's prose, which carries what the rows do not — the beds, and
#: the washroom being combined rather than separate.
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _flatten(fragment: str) -> str:
    return plain_text(fragment)


def spec_rows(page: str) -> dict[str, str]:
    """Every `label -> value` row on a model page, across all four of its panels."""
    return {
        _flatten(match.group("label")): _flatten(match.group("value"))
        for match in SPEC_ROW.finditer(page)
    }


def copy_lines_from(page: str) -> list[str]:
    """A model page as lines `habitation` can read: its spec rows, then its prose.

    The rows carry the fittings — *"Heating & Hot Water: Truma Combi Neo 4E"*, *"70ltr
    compressor fridge: Included"* — and the prose carries what no row states: that the
    washroom is combined rather than separate, and what the beds are.
    """
    rows = [f"{label} {value}".strip() for label, value in spec_rows(page).items()]
    prose = [
        sentence.strip()
        for sentence in _SENTENCE.split(plain_text(page))
        if sentence.strip()
    ]
    return rows + prose


#: A layout's own page, which carries the equipment prose the comparison table does not.
MODEL_PAGES: dict[tuple[str, str], str] = {
    ("Core", "B"): "coreb",
    ("Core", "G"): "coreg",
    ("Element", "B"): "element-b",
    ("Element", "G"): "element-g",
}


def collect(
    http: object,  # noqa: ARG001 - the site is a single-page app; plain HTTP returns nothing
    browser: BrowserFetcher,
    snapshot_dir: Path,  # noqa: ARG001 - the fetcher owns the snapshot directory
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every current Atom layout, from the comparison table and the configurator."""
    wanted = {key for key, _label in ranges}

    on_progress(f"fetching the comparison table: {MODELS_URL}")
    models = browser.fetch(MODELS_URL)
    if models.status_code != 200:
        message = f"{MODELS_URL} returned {models.status_code}; it is the roster"
        raise RuntimeError(message)

    products = read_comparison_table(
        models.file_path.read_text(encoding="utf-8", errors="replace")
    )
    if not products:
        message = (
            f"{MODELS_URL} yielded no comparison table. Either the page no longer renders "
            f"one, or a row stopped carrying {EXPECTED_LAYOUTS} figures — check it before "
            f"assuming Atom have changed their range"
        )
        raise RuntimeError(message)
    on_progress(f"the comparison table lists {len(products)} layout(s)")

    on_progress(f"fetching the configurator for the running orders: {CONFIG_URL}")
    config = browser.fetch(CONFIG_URL)
    running_orders: dict[str, int] = {}
    if config.status_code == 200:
        config_page = config.file_path.read_text(encoding="utf-8", errors="replace")
        running_orders = read_running_order(config_page)
        gvm = read_gross_vehicle_mass(config_page)
        stated = {product.mtplm_kilograms for product in products}
        if gvm is not None and stated != {gvm}:
            on_progress(
                f"WARNING: the comparison table gives {sorted(stated)}kg as the maximum "
                f"authorised weight and the configurator gives {gvm}kg. They are the same "
                f"figure and should agree"
            )
    else:
        on_progress(
            f"WARNING: {CONFIG_URL} returned {config.status_code}, so no mass in running "
            f"order was collected and no payload can be derived"
        )

    results: list[ExtractedMotorhome] = []
    for product in products:
        if wanted and product.manufacturer_range not in wanted:
            continue
        key = (product.manufacturer_range, product.model)
        mro = running_orders.get(CONFIG_NAMES[key])
        if mro is None:
            on_progress(
                f"[{product.label}] WARNING: the configurator names no "
                f"{CONFIG_NAMES[key]!r}, so it goes forward without a running order or a "
                f"payload"
            )

        page = browser.fetch(f"{BASE_URL}/model/{MODEL_PAGES[key]}")
        copy_lines: tuple[str, ...] = ()
        if page.status_code == 200:
            model_page = page.file_path.read_text(encoding="utf-8", errors="replace")
            copy_lines = tuple(copy_lines_from(model_page))
            for note in cross_check(product, spec_rows(model_page)):
                on_progress(f"[{product.label}] WARNING: {note}")
        else:
            on_progress(
                f"[{product.label}] its own page returned {page.status_code}, so no "
                f"habitation findings were read"
            )

        complete = AtomProduct(
            **{**product.__dict__, "mro_kilograms": mro, "copy_lines": copy_lines}
        )
        reconciles, why_not = _reconciles(complete)
        if not reconciles:
            on_progress(f"SKIPPED [{complete.label}]: {why_not}")
            continue
        results.append(_build_extracted_motorhome(complete))

    if not wanted or wanted == {key for key, _label in DEFAULT_RANGES}:
        if len(results) != EXPECTED_LAYOUTS:
            on_progress(
                f"WARNING: collected {len(results)} layout(s) where the survey found "
                f"{EXPECTED_LAYOUTS}. Atom have said they will add four-belt models and a "
                f"6.8m wheelbase, so a change here may be real — check the range page"
            )
    on_progress(f"collected {len(results)} product(s)")
    return results
