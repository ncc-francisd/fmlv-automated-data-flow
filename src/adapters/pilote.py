"""Pilote — 43 layouts across seven ranges, from a specification behind a button.

`docs/adapters/pilote.md` is the survey; this is what it decided.

**One URL is one vehicle**, so there is no column to align. What makes this source
unusual is that its numbers are in no server-rendered HTML at all: the figures live in a
popup that Pilote's own JavaScript fills from Airtable when a visitor presses *Technical
information*. `BrowserFetcher`'s `click_selector` exists for this — see
`docs/adapters/README.md`.

Five things drive the whole module:

* **The slug carries the FMLV range name, in two halves.** The site navigates by body
  type and never shows a range name; `/<body-type>/<layout>-<offer>/` gives both. See
  `DEFAULT_RANGES`.
* **`Berth` on this site means a belted seat.** The summary strip's `Berth`, `Meal place`
  and `Sleeping place` are seats, dining places and berths respectively. Reading `Berth`
  as berths would put the seat count in the berth column on all 43 and look plausible,
  because both are usually 4. See `_SUMMARY_STRIP`.
* **Payload is published in two different places.** Panel vans print `Load capacity in kg`
  in the popup table; coachbuilts print none there and carry `Payload 485 kg` in the
  summary strip instead. See `_payload_for`.
* **MAM is MTPLM.** Pilote publish maximum authorised mass and never use the letters
  MTPLM; the two are the same figure. `le_voyageur.py` makes the same mapping.
* **Width is deliberately not collected.** The only two widths published are the interior
  measurement and the mirrors-open measurement, and FMLV wants neither. See the module's
  `mh_width_mm` note in `_build_extracted_motorhome`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from ..fetch.browser import BrowserFetcher
from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

BASE_URL = "https://www.pilote-motorhome.uk"
MANUFACTURER = "Pilote"
MANUFACTURER_DISPLAY_NAME = "Pilote"

#: The roster. 44 entries, of which one is a broken `%taxo%` placeholder.
SITEMAP_URL = f"{BASE_URL}/vehicule-sitemap.xml"

#: `(<body-type>/<offer>, FMLV manufacturer_range)`.
#:
#: **The site never shows a range name.** It navigates by body type — A-class, low
#: profile, compact low profile, panel van — which is the trap the requester flagged at
#: the outset. But the slug carries the offer as well, and the *pair* maps exactly onto
#: FMLV's seven live ranges, 43 pages for 43 rows.
#:
#: `ATLAS` is upper-case because FMLV holds it that way.
#:
#: **The panel vans are `Van`, not `Pilote Van`.** FMLV renders a listing as manufacturer
#: + range + model + base vehicle, so `Van` displays as *"Pilote Van V630S Fiat"* while
#: `Pilote Van` would display as *"Pilote Pilote Van V630S Fiat"*. The requester spotted
#: it on the live site, 11 September 2026. `joa.py` already follows the same convention
#: for the same reason — its vans are `Van` and display as "Joa by Pilote Van 54G".
#:
#: Three FMLV rows still read `Pilote Van`. `MATCH_THRESHOLD` is set so they still match
#: and keep their ids and photographs — but the run cannot rename them, because
#: `manufacturer_range` is an identity field the pipeline matches on rather than asks
#: about. They need renaming in Nova.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("a-class/expression", "Galaxy Expression"),
    ("a-class/evidence", "Galaxy Evidence"),
    ("low-profile/expression", "Pacific Expression"),
    ("low-profile/evidence", "Pacific Evidence"),
    ("compact-low-profile/atlas", "ATLAS"),
    ("panel-van/pilote", "Van"),
    ("panel-van/evidence", "Van Vega Evidence"),
)
_FMLV_RANGES = dict(DEFAULT_RANGES)

#: The control that opens the specification popup.
#:
#: **Not a text selector.** The popup contains its own `<h3>Technical information</h3>`,
#: so `text=Technical information` matches the heading rather than the button — and
#: clicking a heading neither fails nor times out, so the miss is silent and the figures
#: simply never appear. The button's `id` is the layout's own product code
#: (`P26I6900LHF1ST`), so the class is the stable half.
CLICK_SELECTOR = "button.btn-popup"

#: How long to let the popup's Airtable call land after the click.
SETTLE_MS = 8000

#: How long to wait for the button to become clickable. Three times the shared default,
#: because these pages are heavy and a merely slow one should not cost a product its
#: weights.
#:
#: It is **not** what fixes `LAYOUTS_WITHOUT_A_POPUP` — raising it from 5s to 15s changed
#: nothing for those two, which is what proved the cause was not timing.
CLICK_TIMEOUT_MS = 15_000

#: The layouts whose page carries no popup button at all, checked 11 September 2026.
#:
#: Run #79 lost the popup on these two and run #80 lost it again at three times the
#: timeout, so a plain HTTP fetch was used to settle it: `p740gj-expression` and
#: `p740c-expression` contain **no `button.btn-popup` element**, where
#: `p740fc-expression` beside them has exactly one. Pilote have not published a technical
#: panel for them.
#:
#: So this is a gap in the source, not a fault in the click, and the right behaviour is
#: what already happens: the length, height and both masses come back empty and reach a
#: reviewer as fields not found, while the seats, berths, price and body type — which do
#: not depend on the popup — are still collected. The list exists so the warning can say
#: which of the two it is, and so a page that *gains* a button later stops being narrated.
LAYOUTS_WITHOUT_A_POPUP = frozenset({("Pacific Expression", "P740GJ"), ("Pacific Expression", "P740C")})

#: Pilote's identities collide at the 0.5 default, on two separate axes, so the
#: per-manufacturer threshold `docs/adapters/README.md` describes is mandatory here.
#:
#: | pair | score | |
#: |---|---|---|
#: | the same layout in the same range | **1.000** | must match |
#: | `Van V600G` against FMLV's `Pilote Van V600G` | **0.667** | must match — a rename |
#: | `Galaxy Expression G740FC` against `Galaxy Evidence G740FC` | 0.500 | must **not** |
#: | `Galaxy Expression G720FGJ` against `Galaxy Selection G720FGJ` | 0.500 | must **not** |
#: | `Van V540G` against `Van Vega Evidence V540G` | 0.500 | must **not** |
#: | `Pacific Expression P720U` against `Pacific Evidence P720U` | 0.500 | must **not** |
#:
#: **Every 0.500 row is two real vehicles that are not each other.** The offer is part of
#: the identity — G740FC is £86,900 as Expression and £94,900 as Evidence — and Sélection
#: is a separate limited edition again. Run #79 proved the danger rather than predicting
#: it: at the 0.5 default the newly-listed `Galaxy Expression G720FGJ` claimed the `Galaxy
#: Selection G720FGJ` row, because Selection has no page of its own for a true pair to
#: beat the impostor.
#:
#: **0.6 sits in the gap, and the gap is what saves the three `Pilote Van` rows.** At 0.75
#: they would arrive as new alongside three disappearances, losing their product ids and
#: their photographs; at 0.6 they match at 0.667 and keep both. Nothing that must not
#: match gets above 0.500, so the margin is real rather than lucky.
#:
#: **Matching is all it does — the range itself is not corrected by the run.**
#: `manufacturer_range` is in `store.changes._IDENTITY_FIELDS`, the set the pipeline
#: matches *on* rather than asks about, so no rename is proposed for a matched product
#: and run #81 proposed none. The three rows keep reading `Pilote Van` in FMLV until
#: someone renames them in Nova, which is a data tidy-up rather than anything this
#: adapter can do.
MATCH_THRESHOLD = 0.6

#: How far the published length may sit from the one its model code implies.
#:
#: Pilote name every layout after its length in decimetres, and against the *site's* own
#: figures it holds closely — 0mm on the A630G, 10mm on the V540G, 50mm on the P720U,
#: 170mm on the G690GJ. The band is set above the worst of those with room to spare. The
#: survey's Atlas exemption was withdrawn once the site was read: it rested on the
#: brochure, which gives the A630G as 6.99m against the site's and FMLV's 6.30m.
LENGTH_TOLERANCE_MM = 300

#: Base vehicle by body type. Atlas is the Ford; everything else is Fiat. Both go through
#: `fmlv_base_vehicle`, which is what keeps a chassis maker out of the column.
_BASE_VEHICLES = {"compact-low-profile": "Ford"}
_DEFAULT_BASE_VEHICLE = "Fiat"

#: A campervan taller than this is a high top — the shared NCC threshold. Every Pilote
#: panel van is 2670mm, so all six clear it.
HIGH_TOP_ABOVE_MM = 2300

#: **A manually sourced constant table**, from the 2027 UK vehicle price list. No Pilote
#: page carries a price — checked across all 43 — and the list is on no website, so it
#: arrives by email and cannot be refreshed by a run. Basis: "Public price incl. VAT
#: excluding transport", which is *not* Joa's basis and not Le Voyageur's.
PRICES: dict[tuple[str, str], int] = {
    ("Galaxy Expression", "G690D"): 85_900,
    ("Galaxy Expression", "G690GJ"): 85_900,
    ("Galaxy Expression", "G720FC"): 86_400,
    ("Galaxy Expression", "G720FGJ"): 86_400,
    ("Galaxy Expression", "G740C"): 86_900,
    ("Galaxy Expression", "G740GJ"): 86_900,
    ("Galaxy Expression", "G740FC"): 86_900,
    ("Galaxy Expression", "G740FGJ"): 86_900,
    ("Galaxy Expression", "G741FC"): 95_900,
    ("Galaxy Expression", "G741FGJ"): 95_900,
    ("Galaxy Expression", "G781FC"): 99_900,
    ("Galaxy Expression", "G781FGJ"): 99_900,
    ("Galaxy Evidence", "G690GJ"): 89_500,
    ("Galaxy Evidence", "G740FC"): 94_900,
    ("Galaxy Evidence", "G740FGJ"): 94_900,
    ("Galaxy Evidence", "G781FC"): 104_900,
    ("Galaxy Evidence", "G781FGJ"): 104_900,
    ("Pacific Expression", "P690GJ"): 72_900,
    ("Pacific Expression", "P690D"): 74_900,
    ("Pacific Expression", "P720FC"): 73_900,
    ("Pacific Expression", "P720FGJ"): 73_900,
    ("Pacific Expression", "P720U"): 75_900,
    ("Pacific Expression", "P740FC"): 74_900,
    ("Pacific Expression", "P740FGJ"): 74_900,
    ("Pacific Expression", "P740C"): 74_900,
    ("Pacific Expression", "P740GJ"): 74_900,
    ("Pacific Evidence", "P690D"): 82_500,
    ("Pacific Evidence", "P720U"): 83_500,
    ("Pacific Evidence", "P740FC"): 82_500,
    ("Pacific Evidence", "P740FGJ"): 82_500,
    ("ATLAS", "A630G"): 73_400,
    ("ATLAS", "A690G"): 73_900,
    ("ATLAS", "A690GJ"): 73_900,
    ("ATLAS", "A650D"): 75_400,
    ("Van", "V540G"): 65_400,
    ("Van", "V600G"): 66_400,
    ("Van", "V630J"): 68_400,
    ("Van", "V630B"): 68_400,
    ("Van", "V630S"): 68_400,
    ("Van", "V633M"): 71_000,
    ("Van Vega Evidence", "V600G"): 73_700,
    ("Van Vega Evidence", "V630J"): 75_700,
    ("Van Vega Evidence", "V633M"): 81_900,
}
PRICE_LIST_SOURCE = "the 2027 UK vehicle price list, valid from 1 June 2026"

# --- Reading the roster ----------------------------------------------------------------

#: A layout page in the sitemap: `/<body-type>/<layout>-<offer>/`. The `%taxo%`
#: placeholder the sitemap also carries fails this, which is how it is dropped.
_MODEL_URL = re.compile(
    re.escape(BASE_URL)
    + r"/(?P<body>a-class|low-profile|compact-low-profile|panel-van)"
    + r"/(?P<code>[a-z]\d{3}[a-z]*)-(?P<offer>expression|evidence|atlas|pilote)/"
)

_TAGS = re.compile(r"(?is)<(script|style)\b.*?</\1>")


def plain_text(html: str) -> str:
    """The page as one line, tags replaced by a single space.

    A single space and not a marker: this site splits a value from its unit across
    elements, so anything else welds `7,07` onto `m`.
    """
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _TAGS.sub(" ", html))).strip()


def find_model_urls(sitemap_xml: str, ranges: Iterable[str]) -> list[str]:
    """Every layout page in the sitemap, for the body-type/offer pairs asked for."""
    wanted = {key.lower() for key in ranges}
    urls: list[str] = []
    for match in _MODEL_URL.finditer(sitemap_xml):
        if f"{match.group('body')}/{match.group('offer')}" not in wanted:
            continue
        url = match.group(0)
        if url not in urls:
            urls.append(url)
    return urls


# --- Reading one page ------------------------------------------------------------------

#: The summary strip above the button, matched **as one whole block**.
#:
#: Anchoring on the entire run is not fussiness. Every page also carries a filter sidebar
#: reading `Sleeping places 2 berths 3 berths 4 berths`, and a pattern that looks for
#: `Berth` followed by a number *anywhere* finds that instead — which silently gave all
#: four sampled layouts 2 seats and 2 berths, every one wrong, in the first parse.
#:
#: **`Berth` here means a belted seat, not a berth**: the G690GJ's `Berth 4 / Meal place 5
#: / Sleeping place 4` is the brochure's `Seats with safety belts 4 / Dining seats 5 /
#: Sleeping berths 4`. The seat count is taken from the popup's own labelled row rather
#: than from this strip, but the naming is recorded because it is the trap. `Meal place`
#: is dining seats, which FMLV does not hold.
_SUMMARY_STRIP = re.compile(
    r"Length\s*(?P<lm>\d+),(?P<lcm>\d+)\s*m\s*"
    r"Width\s*[\d,]+\s*m\s*Height\s*[\d,]+\s*m\s*"
    r"Berth\s*(?P<seats>\d+)\s*Meal place\s*(?P<meal>\d+)\s*"
    r"Sleeping place\s*(?P<berths>\d+)"
    r"(?:\s*Payload\s*(?P<payload>\d+)\s*kg)?",
    re.I,
)

#: The popup's own seat row, which is the unambiguous one and the one used.
#:
#: Anchored at both ends so `Seats with safety belts - optional` — the fifth belt, a paid
#: option — is never taken instead. The settled three-point-belt rule wants the standard
#: count.
_SEATS_LABEL = re.compile(r"^Seats with safety belts$", re.I)

#: A row of the popup's technical table, once the click has filled it.
_TABLE_ROW = re.compile(r"<tr>\s*<td>(?P<label>.*?)</td>\s*<td>(?P<value>.*?)</td>\s*</tr>", re.S)

#: Where the popup's table lives. It is empty until the click.
_POPUP = "content-popup-techdata"

#: The maximum authorised mass of the **base** model.
#:
#: Two spellings, by body type — `(kg) on basic models` on a panel van and `(kg) - base
#: models` on a coachbuilt — so the stem is matched and the qualifier is not. The
#: coachbuilt table also carries four chassis-variant MAM rows (`"Light" light vehicle`,
#: `"Light" heavy vehicle`, `"Heavy" 4,25 T`, `"Heavy" 4,4 T/4,5 T`); those are the paid
#: uprates and the base-models row is the one the settled base-vehicle rule wants, so the
#: match is anchored to the start of the label.
_MAM_LABEL = re.compile(r"^Maximum authorised mass \(MAM\) \(kg\)", re.I)

#: The panel vans' payload row. Coachbuilts do not have one — see `_payload_for`.
_LOAD_CAPACITY_LABEL = re.compile(r"^Load capacity in kg", re.I)

_LENGTH_LABEL = re.compile(r"^Vehicle length \(cm\)$", re.I)
_HEIGHT_LABEL = re.compile(r"^Vehicle height \(cm\)$", re.I)


def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).strip()


def _first_int(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"-?\d+", value.replace(" ", ""))
    return int(match.group(0)) if match else None


def popup_rows(page: str) -> dict[str, str]:
    """Every `label -> value` row of the technical table, in page order.

    The table is injected into `div.content-popup-techdata`, which is empty on a page
    that was fetched without the click — so an empty result means the click did not
    happen rather than that the vehicle has no data, and `collect` says so.

    **A row labelled literally `undefined` appears on the panel vans**, value 411. A
    label that failed to render is not a figure to record under a guess; it is kept in
    the mapping under that key and never read.
    """
    start = page.find(_POPUP)
    if start < 0:
        return {}
    rows: dict[str, str] = {}
    for match in _TABLE_ROW.finditer(page[start:]):
        label = _clean(match.group("label"))
        if label and label not in rows:
            rows[label] = _clean(match.group("value"))
    return rows


def _matching(rows: dict[str, str], pattern: re.Pattern[str]) -> str | None:
    for label, value in rows.items():
        if pattern.search(label):
            return value or None
    return None


@dataclass(frozen=True)
class PiloteProduct:
    """One layout, from its page and the popup its button opens."""

    source_url: str
    manufacturer_range: str
    model: str
    body_segment: str
    #: The decimal the model code encodes, as a length in mm. See `_reconciles`.
    implied_length_mm: int
    mh_length_mm: int | None = None
    mh_height_mm: int | None = None
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    mtplm_kilograms: int | None = None
    mh_payload_kilograms: int | None = None
    #: Where the payload came from, for the provenance — the two body types differ.
    payload_source: str = ""
    #: The strip's own length, kept as a cross-check on the popup's.
    strip_length_mm: int | None = None

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def mro_kilograms(self) -> int | None:
        """Derived: MAM minus payload. Pilote publish no mass in running order.

        True by construction, so it is a derivation and not a check — the same position
        as Joa, Murvi and Le Voyageur. The model-code length check is this brand's
        self-check.
        """
        if self.mtplm_kilograms is None or self.mh_payload_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mh_payload_kilograms

    @property
    def body_type(self) -> BodyType | None:
        """A-class, low profile, or a high-top campervan for the panel vans.

        The compact low profile is a low profile: `compact` describes its width, not a
        different body. The vans are 2670mm against the shared 2300mm threshold.
        """
        if self.body_segment == "a-class":
            return BodyType.A_CLASS
        if self.body_segment in {"low-profile", "compact-low-profile"}:
            return BodyType.COACH_BUILT_LOW_PROFILE
        if self.mh_height_mm is None:
            return None
        return (
            BodyType.CAMPERVAN_HIGH_TOP
            if self.mh_height_mm > HIGH_TOP_ABOVE_MM
            else BodyType.CAMPERVAN
        )


def _payload_for(rows: dict[str, str], strip_payload: int | None) -> tuple[int | None, str]:
    """`(payload, where it came from)`. The two body types publish it in different places.

    Panel vans carry `Load capacity in kg (on basic models)` in the popup table and no
    payload in the summary strip. Coachbuilts do the reverse: no load-capacity row in
    their 57-row table, and `Payload 485 kg` in the strip. Both are the same quantity —
    the mass available on a base model — so either one answers the field.
    """
    load_capacity = _first_int(_matching(rows, _LOAD_CAPACITY_LABEL))
    if load_capacity is not None:
        return load_capacity, "the popup table's 'Load capacity in kg (on basic models)'"
    if strip_payload is not None:
        return strip_payload, "the summary strip's 'Payload' figure"
    return None, ""


def parse_model_page(page: str, source_url: str) -> PiloteProduct | None:
    """One layout, from a page that has already been clicked. `None` if the URL is not one."""
    match = _MODEL_URL.fullmatch(source_url)
    if match is None:
        return None
    body, code, offer = match.group("body"), match.group("code"), match.group("offer")
    manufacturer_range = _FMLV_RANGES.get(f"{body}/{offer}")
    if manufacturer_range is None:
        return None

    text = plain_text(page)
    rows = popup_rows(page)
    strip = _SUMMARY_STRIP.search(text)
    strip_payload = int(strip.group("payload")) if strip and strip.group("payload") else None
    payload, payload_source = _payload_for(rows, strip_payload)
    length_cm = _first_int(_matching(rows, _LENGTH_LABEL))
    height_cm = _first_int(_matching(rows, _HEIGHT_LABEL))

    return PiloteProduct(
        source_url=source_url,
        manufacturer_range=manufacturer_range,
        model=code.upper(),
        body_segment=body,
        implied_length_mm=int(code[1:4]) * 10,
        mh_length_mm=length_cm * 10 if length_cm is not None else None,
        mh_height_mm=height_cm * 10 if height_cm is not None else None,
        # Seats from the popup's unambiguous labelled row; berths from the strip, which
        # is the figure Pilote lead with and the one the brochure agrees with.
        mh_passenger_seats_inc_driver=_first_int(_matching(rows, _SEATS_LABEL)),
        berths=int(strip.group("berths")) if strip else None,
        mtplm_kilograms=_first_int(_matching(rows, _MAM_LABEL)),
        mh_payload_kilograms=payload,
        payload_source=payload_source,
        strip_length_mm=(
            int(strip.group("lm")) * 1000 + int(strip.group("lcm")) * 10
            if strip
            else None
        ),
    )


# --- The self-checks -------------------------------------------------------------------


def _reconciles(product: PiloteProduct) -> tuple[bool, str]:
    """`(ok, why not)` — whether the popup's length agrees with the model's own code.

    Pilote name every layout after its length in decimetres. Against the site's own
    figures the convention holds closely, and it is *positional*: it catches a length
    read from the wrong row, which is the failure that otherwise produces plausible,
    internally consistent motorhomes carrying each other's dimensions.

    **A failure drops the length, not the product.** One URL is one vehicle here, so
    there is no alignment to have gone wrong and no reason to distrust the other figures
    on the page — the same reasoning as `joa.py` and `le_voyageur.py`.
    """
    if product.mh_length_mm is None:
        return True, ""
    gap = abs(product.mh_length_mm - product.implied_length_mm)
    if gap <= LENGTH_TOLERANCE_MM:
        return True, ""
    return False, (
        f"the popup states {product.mh_length_mm}mm but the model code implies "
        f"{product.implied_length_mm}mm, a {gap}mm gap against a "
        f"{LENGTH_TOLERANCE_MM}mm tolerance"
    )


def length_disagreement(product: PiloteProduct) -> str | None:
    """Where the summary strip's length contradicts the popup's, if it does.

    Both are on every page, under different labels, so this checks that the strip and
    the popup describe the same vehicle — the thing a page-structure change breaks first.
    """
    strip, popup = product.strip_length_mm, product.mh_length_mm
    if strip is None or popup is None or abs(strip - popup) <= 10:
        return None
    return (
        f"the summary strip says {strip}mm long and the popup table says {popup}mm; "
        f"the popup's figure is the one recorded"
    )


# --- What reaches the reviewer ---------------------------------------------------------


def _build_extracted_motorhome(product: PiloteProduct) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field.

    **`mh_width_mm` is deliberately absent.** The only widths Pilote publish are the
    interior measurement and the mirrors-open measurement, and FMLV wants the body width,
    which is neither — the mirrors-open figure overstates by 40-60cm. The requester's
    ruling, 11 September 2026, is to leave it blank; emitting nothing also preserves
    whatever FMLV already holds on a matched product, which is the same-outer-shell case
    he asked for.
    """
    source_url = product.source_url
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(
            _BASE_VEHICLES.get(product.body_segment, _DEFAULT_BASE_VEHICLE)
        ),
        rrp_pounds=PRICES.get((product.manufacturer_range, product.model)),
        mro_kilograms=product.mro_kilograms,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_payload_kilograms=product.mh_payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        berths=product.berths,
        body_type=product.body_type,
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    if product.mh_length_mm is not None:
        record("mh_length_mm", f"popup table, 'Vehicle length (cm) {product.mh_length_mm // 10}'")
    if product.mh_height_mm is not None:
        record("mh_height_mm", f"popup table, 'Vehicle height (cm) {product.mh_height_mm // 10}'")
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"summary strip, 'Berth {product.mh_passenger_seats_inc_driver}' — Pilote use "
            f"the word Berth for a seat with a safety belt, and 'Sleeping place' for a "
            f"berth",
        )
    if product.berths is not None:
        record(
            "berths",
            f"summary strip, 'Sleeping place {product.berths}' — not its 'Berth' row, "
            f"which is the belted-seat count",
        )
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"popup table, 'Maximum authorised mass (MAM) (kg)' on base models: "
            f"{product.mtplm_kilograms} kg. MAM and MTPLM are the same figure; Pilote "
            f"never use the letters MTPLM",
        )
    if product.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"{product.mh_payload_kilograms} kg, from {product.payload_source}",
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"derived as MAM {product.mtplm_kilograms} kg minus payload "
            f"{product.mh_payload_kilograms} kg = {product.mro_kilograms} kg. Pilote "
            f"publish no mass in running order anywhere",
        )
    if motorhome.rrp_pounds is not None:
        provenance["rrp_pounds"] = Provenance(
            source_url=None,
            snippet=(
                f"{product.label} — £{motorhome.rrp_pounds:,} from {PRICE_LIST_SOURCE}. "
                f"No Pilote page carries a price"
            ),
        )
    record(
        "body_type",
        f"from the site's own body-type path, '{product.body_segment}'"
        + (
            f", with a {product.mh_height_mm}mm height against the {HIGH_TOP_ABOVE_MM}mm "
            f"high-top threshold"
            if product.body_segment == "panel-van" and product.mh_height_mm
            else ""
        ),
    )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --- The run ---------------------------------------------------------------------------


def collect(
    http: Fetcher,
    browser: BrowserFetcher,
    snapshot_dir: Path,  # noqa: ARG001 - the fetchers own the snapshot directory
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every layout the sitemap lists, each read behind one click.

    **This is the slowest sweep in the project**, and deliberately so: 43 full browser
    renders with a click and an eight-second settle apiece. There is no cheaper route —
    the figures are in no server-rendered HTML at all.
    """
    on_progress(f"fetching the vehicle sitemap: {SITEMAP_URL}")
    sitemap = http.fetch(SITEMAP_URL)
    if sitemap.status_code != 200:
        message = f"{SITEMAP_URL} returned {sitemap.status_code}; it is the roster"
        raise RuntimeError(message)

    urls = find_model_urls(
        sitemap.file_path.read_text(encoding="utf-8", errors="replace"),
        (key for key, _label in ranges),
    )
    on_progress(
        f"{len(urls)} layout page(s) in the sitemap; each needs a browser render and a "
        f"click, so this sweep takes minutes rather than seconds"
    )

    results: list[ExtractedMotorhome] = []
    for url in urls:
        page_result = browser.fetch(
            url,
            click_selector=CLICK_SELECTOR,
            click_timeout_ms=CLICK_TIMEOUT_MS,
            settle_ms=SETTLE_MS,
            on_progress=lambda message, url=url: on_progress(f"{url}: {message}"),
        )
        if page_result.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page_result.status_code}")
            continue
        page = page_result.file_path.read_text(encoding="utf-8", errors="replace")

        product = parse_model_page(page, url)
        if product is None:
            on_progress(f"SKIPPED: {url} is not a layout page")
            continue

        if not popup_rows(page):
            known = (product.manufacturer_range, product.model) in LAYOUTS_WITHOUT_A_POPUP
            on_progress(
                f"[{product.label}] no technical popup, so the length, height and both "
                + (
                    "masses are left for FMLV's own figures. This layout's page carries "
                    "no button at all — a known gap in Pilote's own data, not a failed "
                    "click"
                    if known
                    else f"masses are missing. WARNING: this is new — check "
                    f"{CLICK_SELECTOR!r} still matches the button, because every other "
                    f"layout has one"
                )
            )

        reconciles, why_not = _reconciles(product)
        if not reconciles:
            on_progress(
                f"[{product.label}] LENGTH DISCARDED and left for FMLV's own figure: "
                f"{why_not}"
            )
            product = replace(product, mh_length_mm=None)

        if disagreement := length_disagreement(product):
            on_progress(f"[{product.label}] WARNING: {disagreement}")
        if (product.manufacturer_range, product.model) not in PRICES:
            on_progress(
                f"[{product.label}] WARNING: no price — the 2027 list has no row for it, "
                f"so {PRICE_LIST_SOURCE} needs re-reading"
            )

        results.append(_build_extracted_motorhome(product))

    on_progress(f"collected {len(results)} product(s)")
    return results
