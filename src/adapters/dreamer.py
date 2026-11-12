"""Dreamer — nineteen French panel-van conversions, read one model page at a time.

`docs/adapters/dreamer.md` is the survey; this is what it decided.

**This adapter deliberately reads the model pages and NOT the specification table.**
That is the opposite of the obvious choice, and the reason matters:

* `fourgon-caracteristiques-techniques_dreamer.php` is a clean HTML `<table>` carrying
  masses, which is everything this project usually wants. **It is also last season's, and
  the FUN range only** — its own heading reads `Specifications Range FUN`. Every height in
  it is 40 mm short of what the model pages state now (fixed roof `2,59` against `2.63`,
  `UP` `2,72` against `2.76`, Camper Five `2,88` against `2.92`), it carries `ADDICT` and
  `EXCLUSIVE` trims no longer sold, it numbers the vans `D42`/`D53`/`D60` where the site now
  says `D43`/`D55`/`D68`, and it has **no Camper Sport column at all**. Reading masses out
  of it would attach one generation's weights to another's vehicles, and every figure would
  still look like a plausible figure for a Dreamer.

* So **no mass is emitted** — no MIRO, no MTPLM, no payload — because Dreamer publish none
  for the vans they currently sell. Emitting an empty one would propose deleting the figure
  on all sixteen live FMLV rows. This is the same choice `rapido.py` makes about price, and
  `docs/adapters/README.md` has the rule under "A figure that could not be found must be
  visible, and must never be inherited".

* **No price either** (FMLV already holds one on every row) and **no base vehicle**: the
  site names three engines on a range-wide equipment list with no attribution to a model,
  and guessing which van gets the Ford would be the same error in a different column.

What is left is still most of a product, and it is safe in a way the table never was:
**each model has its own URL and names itself in its own `<h1>`**, so the check is an
identity check rather than a column mapping. `_check_identity` is the guard.

Four more things worth knowing before changing anything here.

* **`UP` means a pop-up roof, and it is standard.** The `UP` models are 130 mm taller than
  their twins, publish `2+2` berths where the twin publishes `2 (O : 2 + 1)`, and carry a
  bullet reading *"Extra sleeping area for 2 adults (2000 x 1300 mm)"*. `_check_roof`
  verifies that bullet every run rather than trusting `_Model.elevating_roof`.

* **A footnoted seat count can be a ceiling.** City Camp Select publishes `6(p) people`,
  and `(p)` is *"Maximum number of authorised registered seats as defined by the chassis"*
  — a permitted figure, not a fitted one. `SEAT_FOOTNOTE_IS_A_CEILING` drops it.

* **Never run the equipment pages through `gearbox.automatic_available_from` whole.** The
  Select list contains `Adaptive cruise control - manual transmission only`, which reads as
  an automatic being ruled out and is nothing of the kind — the very next line offers
  lane-keeping *"automatic transmission only"*. `_transmission_lines` keeps only lines that
  state what engine and gearbox are offered.

* **Several models look renamed rather than new.** FMLV holds `LIVING VAN` against the
  site's `LIFT VAN`, `D62` against `D64`, and `FAMILY` against `FAMILY VAN`. None is matched
  automatically, because the rule is to match a rename on a mass and this adapter has no
  mass to match on. `_narrate_rename_candidates` puts them in front of the reviewer instead.
"""

from __future__ import annotations

import html as html_module
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import gearbox, habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "AMBIGUOUS_IDENTITY",
    "BELT_ROW_DISAGREES",
    "CATALOGUE_AUTOMATIC",
    "BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_PRODUCTS",
    "FUN",
    "HIGH_TOP_ABOVE_MM",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MODELS",
    "RENAME_CANDIDATES",
    "ROOF_UNSTATED",
    "SELECT",
    "SPECIFICATION_2027",
    "SELECT_WITHOUT_AUTOMATIC",
    "DreamerProduct",
    "collect",
    "parse_model_page",
    "parse_tiles",
]

BASE_URL = "https://www.dreamer-van.co.uk"

#: Byte-for-byte the `manufacturer` value in FMLV's export, and the NCC manufacturer list's
#: name at id 127. Not capitalised, unlike its sister brand `ITINEO`.
MANUFACTURER = "Dreamer"
MANUFACTURER_DISPLAY_NAME = "Dreamer"

#: The two range names, spelled as FMLV's export spells them — `Fun` and `Select`, title
#: case, where the website shouts `DREAMER FUN` and suffixes every Select model's name with
#: ` Select`. The suffix is the range and is stripped from the model; see `_Model.model`.
FUN = "Fun"
SELECT = "Select"

HOME_URL = f"{BASE_URL}/index.php"
FUN_RANGE_URL = f"{BASE_URL}/fourgon-dreamer-fun.php"
SELECT_RANGE_URL = f"{BASE_URL}/fourgon-dreamer-select.php"

#: The two equipment lists, one per range. Read **only** for the transmission — see
#: `_transmission_lines` for why they cannot be read whole.
FUN_EQUIPMENT_URL = f"{BASE_URL}/fourgon-dreamer-equipements.php"
SELECT_EQUIPMENT_URL = f"{BASE_URL}/dreamer-select-equipements.php"

#: The last-season table. **Not fetched, not parsed** — named here so that anyone who comes
#: looking for it finds the reason rather than the URL. See the module docstring.
SUPERSEDED_SPECIFICATION_TABLE = (
    f"{BASE_URL}/fourgon-caracteristiques-techniques_dreamer.php"
)

EXPECTED_PRODUCTS = 19

#: The settled campervan threshold, shared with `aura`, `auto_sleepers`, `auto_trail` and
#: `robeta`.
HIGH_TOP_ABOVE_MM = 2300


@dataclass(frozen=True)
class _Model:
    """One model: its page, the name FMLV holds, its range, and whether it has a pop-top."""

    path: str
    #: The model name **without** the ` Select` suffix, upper-cased, as FMLV holds it.
    model: str
    manufacturer_range: str
    #: Whether a pop-up roof is standard, as **three** states rather than two. `True` and
    #: `False` are verified against the page every run by `_check_roof` rather than
    #: trusted; `None` means the question is genuinely open and **no body type is emitted
    #: at all**, which leaves FMLV's own value standing. See `ROOF_UNSTATED`.
    elevating_roof: bool | None = False
    #: The name the page's own `<h1>` carries, where it is not simply `model` plus the
    #: range suffix. Used by `_check_identity`.
    page_name: str | None = None

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.path}"

    @property
    def expected_heading(self) -> str:
        if self.page_name is not None:
            return self.page_name
        return self.model if self.manufacturer_range == FUN else f"{self.model} SELECT"


MODELS: tuple[_Model, ...] = (
    # --- DREAMER FUN -------------------------------------------------------
    _Model("fourgon-dreamer-d43.php", "D43", FUN),
    _Model("fourgon-dreamer-d43-up.php", "D43 UP", FUN, elevating_roof=True, page_name="D43"),
    _Model("fourgon-dreamer-d55.php", "D55", FUN),
    _Model("fourgon-dreamer-d55-up.php", "D55 UP", FUN, elevating_roof=True, page_name="D55"),
    _Model("fourgon-dreamer-d68.php", "D68", FUN),
    _Model("fourgon-dreamer-d68-up.php", "D68 UP", FUN, elevating_roof=True, page_name="D68"),
    _Model("fourgon-dreamer-campersport.php", "CAMPER SPORT", FUN),
    _Model("fourgon-dreamer-camperfive.php", "CAMPER FIVE", FUN),
    # --- DREAMER SELECT ----------------------------------------------------
    _Model("fourgon-dreamer-capeasy-select.php", "CAP EASY", SELECT, elevating_roof=True),
    _Model("fourgon-dreamer-d43-select.php", "D43", SELECT),
    _Model("fourgon-dreamer-d55-select.php", "D55", SELECT),
    _Model("fourgon-dreamer-citycamp-select.php", "CITY CAMP", SELECT, elevating_roof=None),
    _Model("fourgon-dreamer-d64-select.php", "D64", SELECT),
    _Model("fourgon-dreamer-d68-select.php", "D68", SELECT),
    _Model("fourgon-dreamer-capland-select.php", "CAP LAND", SELECT, elevating_roof=True),
    _Model("fourgon-dreamer-lift-van-select.php", "LIFT VAN", SELECT),
    _Model(
        "fourgon-dreamer-lift-van-up-select.php",
        "LIFT VAN UP",
        SELECT,
        elevating_roof=True,
    ),
    _Model("fourgon-dreamer-campervan-xl-select.php", "CAMPER VAN XL", SELECT),
    _Model("fourgon-family-select.php", "FAMILY VAN", SELECT),
)

#: `(slug, label)` for `--range`. The two ranges, because `D55` and `D68` exist in both and
#: a model name alone does not identify a product here.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (("fun", FUN), ("select", SELECT))

#: Models FMLV holds whose name the site no longer uses, and the current model each one is
#: most likely to be. **Narrated, never applied** — the settled rule is that a rename is
#: evidenced on a mass in running order, and this adapter collects no mass. See
#: `_narrate_rename_candidates`.
RENAME_CANDIDATES: dict[str, str] = {
    "D62": (
        "D64 (Select) — the site badges D64 as new for 2027 and no longer lists a D62, "
        "and the two share a length of 6,360mm"
    ),
}

#: The one case the first run showed cannot be reasoned out from names at all, stated in
#: full because the automatic matcher resolves it one way and the evidence points the other.
#:
#: FMLV's Select range holds **`D68 UP`** (4 berths, 2,720mm) and **`LIVING VAN`** (4
#: berths, 2,880mm). The site's Select range now holds **`LIFT VAN`** (2 berths, 2,630mm)
#: and **`LIFT VAN UP`** (4 berths, 2,760mm), and has moved a `D68 UP` into **FUN**, badged
#: new. Two readings fit:
#:
#: * the matcher's: the FUN `D68 UP` *is* FMLV's Select `D68 UP` moved between ranges, and
#:   `LIFT VAN UP` is a new product; or
#: * on the heights: FMLV's Select `D68 UP` at 2,720mm is **`LIFT VAN UP`** at 2,760mm, the
#:   same +40mm shift every other model shows between the superseded table and the model
#:   pages, and the FUN `D68 UP` is the genuinely new one.
#:
#: The second reading is the better fit, and it cannot be confirmed, because the settled
#: way to evidence a rename is to match the mass in running order and this adapter collects
#: no mass. So it is said rather than applied.
AMBIGUOUS_IDENTITY: tuple[str, ...] = (
    "FMLV Select 'D68 UP' (3,165kg) and Select 'LIVING VAN' (3,105kg) against the site's "
    "Select 'LIFT VAN' (3,025kg) and 'LIFT VAN UP' (3,145kg), with a D68 UP now in FUN "
    "(3,135kg) badged new. NOW THAT THE SPECIFICATION DOCUMENT GIVES MASSES, the settled "
    "rename test can finally be applied — and it does not settle this one. Both readings "
    "agree that FMLV's LIVING VAN is the site's LIFT VAN (3,105 -> 3,025kg). They differ "
    "on FMLV's Select D68 UP: the automatic matcher reads it as the FUN D68 UP "
    "(3,165 -> 3,135kg, 30kg apart), and the LIFT VAN UP is the closer fit "
    "(3,165 -> 3,145kg, 20kg apart). TEN kilograms is not a margin to decide a product's "
    "identity on. Ask Dreamer which of the two the old D68 UP became",
)

#: Models whose roof this adapter refuses to decide, and why. A model named here emits
#: **no `body_type` at all**, so FMLV's existing value survives the run.
#:
#: The default everywhere else is that silence means the elevating roof is an option and
#: therefore not part of the standard specification — the settled rule in
#: `docs/adapters/README.md`, and the right default, because a maker who fits a pop-top as
#: standard says so. It is the right default precisely because it is usually safe to say
#: "no roof mentioned, so no roof". Here it is not:
#:
#: * **City Camp Select publishes four berths in a van 2,040 mm tall.** There is nowhere
#:   for the second pair to sleep but a roof, and its own twin — Cap Land Select, the same
#:   height, the same chassis, the same four berths — states *"4 adult berths with pop-up
#:   roof"* in so many words. FMLV holds it as `campervan_elevating_roof`.
#:
#: Downgrading it to a plain `campervan` on the strength of one page's silence would be a
#: correction made against the evidence rather than from it, so the question goes to a
#: person instead.
ROOF_UNSTATED: dict[str, str] = {
    "CITY CAMP": (
        "the page never mentions a roof, but it publishes '2 + 2' berths on a van 2,040mm "
        "tall, and its twin the Cap Land Select — same height, same four berths — says "
        "'4 adult berths with pop-up roof' outright. FMLV holds this as "
        "campervan_elevating_roof. Too strong a case to overturn on silence, so NO body "
        "type is proposed and FMLV's own value stands"
    ),
}

#: `automatic_available` evidence that exists **only in the 2027 catalogue**, which sits
#: behind a name-and-email form and so cannot be fetched by a run.
#:
#: The website's own equipment list settles the FUN range — `FIAT 140 hp automatic
#: transmission, 3.5T - LIGHT DUTY` — and settles nothing for Select, where the only
#: engine lines name a Ford and a Renault, both manual. Select therefore came through
#: blank, which is the correct reading of silence but is not the whole story.
#:
#: The catalogue says it twice. In the Select section, the **SAPHIR finish** is listed as
#: including *"140 hp engine with automatic transmission"* (p.33), and in the FUN section
#: *"The automatic gearbox is available across the entire range"* (p.13). An automatic
#: cited as part of a finish is cited, and the settled rule counts a cited option as a
#: `Yes`.
#:
#: Recorded as a constant rather than parsed, because the document cannot be re-fetched.
#: A run that could read it would not need this.
CATALOGUE_AUTOMATIC: dict[str, tuple[bool, str]] = {
    SELECT: (
        True,
        "the 2027 catalogue's SAPHIR finish for the Select range includes '140 hp engine "
        "with automatic transmission' (p.33), and the catalogue states 'The automatic "
        "gearbox is available across the entire range' (p.13)",
    ),
}

#: Select models the SAPHIR finish does not cover, and which therefore get **no** automatic
#: from `CATALOGUE_AUTOMATIC`.
#:
#: This is not a guess from their size. `dreamer-select-equipements.php` lays its table out
#: in **four** columns — `SELECT RANGE STANDARD`, `SELECT RANGE FINISH SAPHIR`,
#: `CAP LAND SELECT / CITY CAMP SELECT`, and `CAP EASY SELECT` — so Dreamer themselves
#: hold these three apart from the finish that carries the automatic. Their base-vehicle
#: entries name the only engines they are offered with, and both are manual:
#: `FORD EcoBlue 2.0-litre 136 hp engine with manual transmission` and `RENAULT Trafic
#: Blue 130 hp engine with manual transmission`.
#:
#: So for these three the answer is **silence, not denial** — nothing states an automatic
#: is unavailable — and silence is a blank. See `docs/adapters/README.md`.
SELECT_WITHOUT_AUTOMATIC: dict[str, str] = {
    "CAP EASY": "on the Renault Trafic, offered only with a manual transmission",
    "CAP LAND": "on the Ford, offered only with a manual transmission",
    "CITY CAMP": "on the Ford, offered only with a manual transmission",
}

@dataclass(frozen=True)
class _Specification:
    """One model's row from Dreamer's 2027 specification document."""

    mro_kilograms: int
    payload_kilograms: int
    #: The **base** gross vehicle weight. Where Dreamer offer a choice — `3.5 T / 4.25 T`
    #: on most of the range — this is the lower, which is the base vehicle.
    mtplm_kilograms: int
    #: Dreamer's own chassis wording, normalised at output by `fmlv_base_vehicle`.
    base_vehicle: str
    #: Dreamer's own words for the heater, read by `habitation.heating_from`.
    heating: str
    #: The document's own height and length, held **only** to check it against the live
    #: site — see `_check_specification`. Neither is emitted from here.
    height_mm: int
    length_mm: int


#: Dreamer's **2027 specification document**, base finish only, for all nineteen models.
#:
#: `COM_DRE_CT_Dreamer_EXPORT_2027_220x285_BD_EN.pdf`, obtained 12 November 2026. This is
#: the source that was missing when the adapter was written: it carries the masses, the
#: chassis and the heater for every model, none of which appears anywhere on the website.
#:
#: **It is stored rather than fetched, because a run cannot reach it.** It sits behind a
#: name-and-email form that posts to itself, so the PDF's URL only exists after a human
#: submits the form, and it is not publicly indexed. That is the whole reason this is a
#: constant and not a parser.
#:
#: **Two things make a stored table safer here than it sounds.**
#:
#: * **It checks against itself.** `MIRO + payload == GVW` on all nineteen, and not
#:   trivially: the three non-Fiat vans have their own gross weights and land on them
#:   exactly — City Camp on 3,300 kg, Cap Land on 3,175 kg, Cap Easy on 3,070 kg.
#:   `_check_specification` re-runs that arithmetic every time rather than trusting it.
#: * **The live site can tell when it has gone stale.** Every model page publishes its own
#:   height and the range tile its own length, so the document's figures are compared
#:   against the site each run and a divergence is narrated. A stored table that cannot
#:   notice it has rotted is a liability; one the live site audits is not.
#:
#: **Only the base finish is recorded.** The document gives each model twice — `D43 FUN`
#: and `D43 FUN +`, `D43 SELECT` and `D43 SELECT SAPHIR` — and the second is a trim level
#: carrying extra equipment and, usually, five more kilos. FMLV holds one row per model,
#: and the settled rule takes the base vehicle rather than the optioned variant.
SPECIFICATION_2027: dict[tuple[str, str], _Specification] = {
    # --- DREAMER FUN, all Fiat Ducato, all Webasto ------------------------------
    (FUN, "D43"): _Specification(2835, 665, 3500, "FIAT DUCATO", "WEBASTO 4 kW DIESEL", 2630, 5410),
    (FUN, "D43 UP"): _Specification(2925, 575, 3500, "FIAT DUCATO", "WEBASTO 4 kW DIESEL", 2760, 5410),
    (FUN, "D55"): _Specification(2960, 540, 3500, "FIAT DUCATO", "WEBASTO 4 kW DIESEL", 2630, 5990),
    (FUN, "D55 UP"): _Specification(3050, 450, 3500, "FIAT DUCATO", "WEBASTO 4 kW DIESEL", 2760, 5990),
    (FUN, "D68"): _Specification(3025, 475, 3500, "FIAT DUCATO", "WEBASTO 4 kW DIESEL", 2630, 6360),
    (FUN, "D68 UP"): _Specification(3135, 365, 3500, "FIAT DUCATO", "WEBASTO 4 kW DIESEL", 2760, 6360),
    (FUN, "CAMPER FIVE"): _Specification(3055, 445, 3500, "FIAT DUCATO", "WEBASTO 4 kW DIESEL", 2920, 6360),
    # The one place the document and the website disagree — see `_check_specification`.
    (FUN, "CAMPER SPORT"): _Specification(3020, 480, 3500, "FIAT DUCATO", "WEBASTO 4 kW DIESEL", 2920, 6360),
    # --- DREAMER SELECT, Fiat Ducato on Truma ----------------------------------
    (SELECT, "D43"): _Specification(2850, 650, 3500, "FIAT DUCATO", "Truma Combi 4 DIESEL CP PLUS", 2630, 5410),
    (SELECT, "D55"): _Specification(3025, 475, 3500, "FIAT DUCATO", "Truma Combi 4 DIESEL CP PLUS", 2630, 5990),
    (SELECT, "D68"): _Specification(3025, 475, 3500, "FIAT DUCATO", "Truma Combi 4 DIESEL CP PLUS", 2630, 6360),
    # The D64 is the one Fiat Select model on a Webasto rather than a Truma.
    (SELECT, "D64"): _Specification(3025, 475, 3500, "FIAT DUCATO", "WEBASTO 4 KW DIESEL", 2630, 6360),
    (SELECT, "LIFT VAN"): _Specification(3025, 475, 3500, "FIAT DUCATO", "Truma Combi 4 DIESEL CP PLUS", 2630, 6360),
    (SELECT, "LIFT VAN UP"): _Specification(3145, 355, 3500, "FIAT DUCATO", "Truma Combi 4 DIESEL CP PLUS", 2760, 6360),
    (SELECT, "FAMILY VAN"): _Specification(3055, 445, 3500, "FIAT DUCATO", "Truma Combi 4 DIESEL CP PLUS", 2880, 5990),
    (SELECT, "CAMPER VAN XL"): _Specification(3125, 375, 3500, "FIAT DUCATO", "Truma Combi 4 DIESEL CP PLUS", 2920, 6360),
    # --- DREAMER SELECT, the three that are neither Fiat nor 3.5 tonnes ---------
    (SELECT, "CITY CAMP"): _Specification(2715, 585, 3300, "FORD TRANSIT CUSTOM", "EBERSPAECHER 2200 W", 2040, 5050),
    (SELECT, "CAP LAND"): _Specification(2730, 445, 3175, "FORD TRANSIT CUSTOM", "EBERSPAECHER 2200 W", 2040, 5450),
    (SELECT, "CAP EASY"): _Specification(2589, 481, 3070, "RENAULT TRAFIC", "WEBASTO 2500 W", 1990, 5480),
}

#: What the specification document says about three-point belts, which is **not** the same
#: as its registered-seat count on two models.
#:
#: Its `3-point retractable safety belts (cab and living space)` row reads `2+2` — four —
#: for every Fiat model, including the **Camper Five** and the **Family Van**, whose
#: `Registered (driving) seats` row reads **5**. FMLV holds 5 for both, and the settled
#: rule counts three-point belts only.
#:
#: **Nothing is changed on the strength of this.** Reducing two live products' seat counts
#: is a decision for a person, and `2+2` may describe the two rows of belts rather than
#: every belt in the vehicle — the Camper Five's fifth seat is a fold-down the document
#: lists separately. `_narrate_findings` puts it in front of the reviewer each run instead.
BELT_ROW_DISAGREES: dict[tuple[str, str], str] = {
    (FUN, "CAMPER FIVE"): (
        "the specification lists 5 registered (driving) seats but gives its 3-point "
        "retractable safety belts as '2+2', which is four"
    ),
    (SELECT, "FAMILY VAN"): (
        "the specification lists 5 registered (driving) seats but gives its 3-point "
        "retractable safety belts as '2+2', which is four"
    ),
}

#: Products FMLV holds that have no counterpart on the site at all.
NOT_ON_THE_SITE: dict[str, str] = {
    "CITY CAMP HYBRIDE": (
        "the Select range lists City Camp with no hybrid variant beside it, and no model "
        "page mentions one"
    ),
}


# --------------------------------------------------------------------------- #
# Reading a page
# --------------------------------------------------------------------------- #

_TAG = re.compile(r"<[^>]+>")
_SVG = re.compile(r"(?is)<svg.*?</svg>")

#: One spec picto: an icon div naming the field, then a text div carrying the value. The
#: Select pages use the same two classes with a `-select` suffix and nothing else changed.
_PICTO = re.compile(
    r'(?is)newpicto-icon-section(?:-select)?"?>(?P<icon>.*?)</div>\s*'
    r'<div class="newpicto-text-section[^"]*"?>(?P<value>.*?)</div>'
)
_PICTO_FIELD = re.compile(r'class="(svg__[a-zA-Z0-9_-]+)')

_HEADING = re.compile(r"(?is)<h1[^>]*>(?P<name>.*?)</h1>")

#: The "advantages" block: a subtitle and a short bulleted list, and the only prose on the
#: page that describes the vehicle rather than the brand.
_ADVANTAGES = re.compile(r'(?is)id="lesPlus"(?P<block>.*?)</div>')
_SUBTITLE = re.compile(r'(?is)class="subtitlePlus"[^>]*>(?P<text>.*?)</h3>')
_BULLET = re.compile(r"(?is)<li[^>]*>(?P<text>.*?)</li>")

#: `(H) 2.63 M (W) 2.05 m`. Anchored on the letter so that Cap Land's
#: `(H) 2.04 M O : 2.00 m* (W) 2.03 M` cannot hand back the optional lowered figure — the
#: `2.00` belongs to a rear-suspension option and the base vehicle's height is `2.04`.
_DIMENSION = re.compile(r"\((?P<axis>[HLW])\)\s*(?P<metres>\d+[.,]\d+)\s*m\b", re.I)

#: `4 people`, `5(e) people`, `6(p) people`.
_SEATS = re.compile(r"^(?P<count>\d+)\s*(?:\((?P<footnote>[a-z])\))?\s*(?:people|person)", re.I)

#: The footnote letters that mark a seat count as a **permitted maximum** rather than the
#: seats the vehicle is built with. `(p)` is Dreamer's own wording: *"Maximum number of
#: authorised registered seats as defined by the chassis"*. A ceiling is not a figure FMLV
#: records — see `docs/adapters/README.md`, "A 'permitted' figure is a ceiling".
SEAT_FOOTNOTE_IS_A_CEILING: frozenset[str] = frozenset({"p"})

#: The bullet that proves a pop-up roof is fitted as standard rather than offered.
_ROOF_BED = re.compile(
    r"extra sleeping area|pop[-\s]?up roof|roof bed|berths with pop", re.I
)

#: A line from an equipment list that states what engine and gearbox are **offered**. Every
#: such line names a make, which is what separates it from `Adaptive cruise control -
#: manual transmission only`, a caveat on a driver-assistance feature that happens to use
#: the same two words.
_TRANSMISSION_OFFER = re.compile(
    r"\b(fiat|ford|peugeot|citro[eë]n|renault|mercedes|man|vw)\b.*?"
    r"\b(transmission|gearbox)\b",
    re.I,
)


def _read(path: Path) -> str:
    """One page's text, honouring the fact that this site is **not** UTF-8.

    Every page declares `charset=iso-8859-1`, and means it: the heater on Cap Easy Select
    is written `WEBASTO 2500\xa0W FUEL HEATING` with a real non-breaking space, which is a
    single byte `0xA0` and not valid UTF-8 at all. Reading it as UTF-8 with
    `errors="replace"` turns that byte into U+FFFD, which then cannot be written back out
    to a Windows console and takes the whole run down with it.

    Strict UTF-8 first rather than trusting the declaration, because a page can be
    mislabelled in either direction and UTF-8 that decodes cleanly is almost never
    accidental. cp1252 is used for the fallback rather than iso-8859-1 proper: it is a
    superset, it cannot fail, and French copy that reaches for a curly quote lands in the
    range where the two differ.
    """
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def _text(fragment: str) -> str:
    return " ".join(html_module.unescape(_TAG.sub(" ", _SVG.sub(" ", fragment))).split())


def _metres_to_mm(metres: str) -> int:
    return round(float(metres.replace(",", ".")) * 1000)


def _standard_count(value: str) -> int | None:
    """The berths a buyer gets without paying, from Dreamer's own notation.

    They write the standard figure first and put everything optional in brackets behind an
    `O`, so `2 (O : 2 + 1)` is two berths with an optional third, and `2+2` is four. Only
    the part before the bracket counts, which is the settled berth rule: the figure recorded
    is the vehicle as built.
    """
    standard = value.split("(")[0]
    numbers = [int(number) for number in re.findall(r"\d+", standard)]
    return sum(numbers) if numbers else None


@dataclass
class DreamerProduct:
    """One model as its own page describes it, before it becomes a `Motorhome`."""

    model: str
    manufacturer_range: str
    source_url: str
    elevating_roof: bool

    #: The page's own `<h1>`, for the identity check.
    page_heading: str | None = None

    mh_length_mm: int | None = None
    mh_height_mm: int | None = None
    mh_width_mm: int | None = None
    berths: int | None = None
    mh_passenger_seats_inc_driver: int | None = None

    #: Dreamer's raw strings, kept so provenance can quote them.
    berths_note: str | None = None
    seats_note: str | None = None
    seats_ceiling_note: str | None = None
    dimensions_note: str | None = None

    #: The remaining pictos — fridge, heater, fresh and waste water — which are findings for
    #: a person to type in rather than fields this adapter proposes.
    pictos: dict[str, str] = field(default_factory=dict)

    #: The advantages subtitle and bullets, which is the habitation source.
    prose: list[str] = field(default_factory=list)

    automatic: tuple[bool, str] | None = None

    #: This model's row from `SPECIFICATION_2027`, where there is one. The masses, the
    #: chassis and the heater come from here and from nowhere else.
    specification: _Specification | None = None

    @property
    def label(self) -> str:
        return f"{MANUFACTURER_DISPLAY_NAME} {self.manufacturer_range} {self.model}"


def parse_tiles(page: str) -> dict[str, int]:
    """`{model page path: overall length in mm}` from a range page's model tiles.

    **The length is published here and nowhere else.** A model page states its height and
    its width but never its length, so the tile is not a convenience — it is the only
    source, and a model whose tile cannot be found gets no length at all.

    A tile is an `<h2>` naming the model, a link to its page, and a `<span class="dim">`
    carrying `5.41 m` and sometimes a `New` badge.
    """
    lengths: dict[str, int] = {}
    for block in re.split(r"(?i)<h2\b", page)[1:]:
        link = re.search(r'href="(?P<path>fourgon[a-z0-9_-]*\.php)"', block, re.I)
        if link is None:
            continue
        # A generous window rather than a closing tag. A model badged `New` carries an
        # extra `<span class="nouveau">New</span>` INSIDE the `dim` span and before the
        # figure, so stopping at the first `</span>` loses the length on exactly the six
        # models most worth collecting. The badge contributes no digits, so taking the
        # first metres figure out of the window's text is safe.
        dim = re.search(r'(?is)class="dim"[^>]*>(?P<dim>.{0,400})', block)
        if dim is None:
            continue
        metres = re.search(r"(?P<metres>\d+[.,]\d+)\s*m\b", _text(dim.group("dim")))
        if metres is None:
            continue
        lengths.setdefault(link.group("path").lower(), _metres_to_mm(metres.group("metres")))
    return lengths


def parse_model_page(page: str, model: _Model, *, length_mm: int | None = None) -> DreamerProduct:
    """Everything one model page publishes about its vehicle.

    The figures live in a block of eight pictos, each labelled by the class of its icon
    rather than by any visible word — `svg__dimension_ext` for the exterior dimensions,
    `svg__places` for the registered seats, `svg__lit` for the berths. That is why this
    reads classes and not text.
    """
    product = DreamerProduct(
        model=model.model,
        manufacturer_range=model.manufacturer_range,
        source_url=model.url,
        elevating_roof=model.elevating_roof,
        mh_length_mm=length_mm,
    )

    heading = _HEADING.search(page)
    if heading is not None:
        product.page_heading = _text(heading.group("name")).upper()

    for match in _PICTO.finditer(page):
        icon = _PICTO_FIELD.search(match.group("icon"))
        if icon is None:
            continue
        value = _text(match.group("value"))
        if not value:
            continue
        product.pictos[icon.group(1)] = value

    exterior = product.pictos.get("svg__dimension_ext")
    if exterior:
        product.dimensions_note = exterior
        for match in _DIMENSION.finditer(exterior):
            millimetres = _metres_to_mm(match.group("metres"))
            axis = match.group("axis").upper()
            if axis == "H" and product.mh_height_mm is None:
                product.mh_height_mm = millimetres
            elif axis == "W" and product.mh_width_mm is None:
                product.mh_width_mm = millimetres

    berths = product.pictos.get("svg__lit")
    if berths:
        product.berths_note = berths
        product.berths = _standard_count(berths)

    seats = product.pictos.get("svg__places")
    if seats:
        match = _SEATS.match(seats)
        if match is not None:
            footnote = (match.group("footnote") or "").lower()
            if footnote in SEAT_FOOTNOTE_IS_A_CEILING:
                product.seats_ceiling_note = seats
            else:
                product.mh_passenger_seats_inc_driver = int(match.group("count"))
                product.seats_note = seats

    advantages = _ADVANTAGES.search(page)
    if advantages is not None:
        block = advantages.group("block")
        subtitle = _SUBTITLE.search(block)
        if subtitle is not None:
            product.prose.append(_text(subtitle.group("text")))
        product.prose.extend(
            line for line in (_text(b) for b in _BULLET.findall(block)) if line
        )

    return product


# --------------------------------------------------------------------------- #
# The checks
# --------------------------------------------------------------------------- #


def _check_identity(product: DreamerProduct, model: _Model) -> tuple[bool, str]:
    """Whether the page reached is the model it was asked for.

    This is what stands in for the arithmetic self-check that a mass table would give. It
    is a weaker instrument but it answers the question that actually matters here: the risk
    with a per-model source is not a misread figure, it is a figure landing on the wrong
    vehicle, and a page that names itself cannot do that silently.
    """
    if product.page_heading is None:
        return False, "the page carries no heading, so there is nothing to identify it by"
    expected = model.expected_heading.upper()
    if product.page_heading != expected:
        return False, (
            f"{model.url} is headed {product.page_heading!r} where {expected!r} was "
            f"expected — the model behind this URL has changed"
        )
    return True, f"the page is headed {product.page_heading!r}, as expected"


#: The pictos every model page has been seen to carry. A page yielding fewer than this has
#: changed shape, and whatever was read off it is not trustworthy either.
REQUIRED_PICTOS: tuple[str, ...] = ("svg__dimension_ext", "svg__places", "svg__lit")


def _check_shape(product: DreamerProduct) -> tuple[bool, str]:
    """Whether the page yielded the pictos all nineteen have been seen to carry."""
    missing = [name for name in REQUIRED_PICTOS if name not in product.pictos]
    if missing:
        return False, (
            f"the specification block is missing {', '.join(missing)} — the page has "
            f"changed shape"
        )
    return True, f"{len(product.pictos)} specification pictos read"


def _check_roof(product: DreamerProduct) -> str | None:
    """Narrate a disagreement between this adapter's roof constant and the page.

    `_Model.elevating_roof` is a standing claim about the vehicle, and standing claims rot.
    Dreamer say it three ways at once on an `UP` model — the name, a height 130 mm above the
    twin, and a bullet reading *"Extra sleeping area for 2 adults (2000 x 1300 mm)"* — so
    the bullet's absence is worth saying out loud rather than quietly keeping the body type.
    """
    if product.elevating_roof is None:
        return None
    says_roof = any(_ROOF_BED.search(line) for line in product.prose)
    if product.elevating_roof and not says_roof:
        return (
            f"{product.label} is held here as having a pop-up roof as standard, but the "
            f"page no longer says so — nothing on it mentions a roof bed or an extra "
            f"sleeping area. The body type may now be wrong"
        )
    if not product.elevating_roof and says_roof:
        matched = next(line for line in product.prose if _ROOF_BED.search(line))
        return (
            f"{product.label} is held here as having NO standard pop-up roof, but the page "
            f"says {matched!r}. The body type may now be wrong"
        )
    return None


#: The make inside a chassis name. Dreamer write the model as well as the maker —
#: `FIAT DUCATO`, `FORD TRANSIT CUSTOM`, `RENAULT TRAFIC` — and FMLV's base-vehicle
#: column holds the make alone. Passing the whole string to `fmlv_base_vehicle` gets it
#: back unchanged, because that function returns an unrecognised make rather than
#: blanking it, so `FIAT DUCATO` would have been proposed against FMLV's `Fiat` on all
#: nineteen products.
_CHASSIS_MAKE = re.compile(
    "(FIAT|FORD|PEUGEOT|CITRO[EË]N|RENAULT|MERCEDES(?:-BENZ)?|MAN|VW|IVECO)", re.I
)


def _base_vehicle_of(specification: _Specification | None) -> str | None:
    """The chassis make as FMLV spells it, from Dreamer's fuller chassis name."""
    if specification is None:
        return None
    match = _CHASSIS_MAKE.search(specification.base_vehicle)
    if match is None:
        return None
    return fmlv_base_vehicle(match.group(1))


def _check_specification(product: DreamerProduct) -> list[str]:
    """Audit the stored specification row against its own arithmetic and the live site.

    A table of figures typed out of a PDF cannot notice that the PDF has been superseded.
    This is what stops that being true here, and it has two independent halves:

    * **The arithmetic.** `MIRO + payload` must equal the gross weight Dreamer publish for
      the model. On the 2027 document it does for all nineteen, and the three non-Fiat
      vans land on their own distinct weights — 3,300, 3,175 and 3,070 kg — which is what
      makes the agreement meaningful rather than a coincidence of everything being 3.5 T.
    * **The live site.** Every model page publishes its own height and every range tile
      its own length, so the document's two dimensions are checked against figures read
      fresh this run. A model that has changed shape will diverge here first.

    Returns a list of complaints, empty when all is well. Nothing is dropped on a
    complaint: a disagreement about a height does not make a mass wrong, and silently
    withholding the only masses Dreamer publish would be the worse failure. It is said
    out loud instead.
    """
    specification = product.specification
    if specification is None:
        return []

    complaints: list[str] = []
    total = specification.mro_kilograms + specification.payload_kilograms
    if total != specification.mtplm_kilograms:
        complaints.append(
            f"the stored specification does not add up: MIRO "
            f"{specification.mro_kilograms:,}kg plus payload "
            f"{specification.payload_kilograms:,}kg is {total:,}kg, not the "
            f"{specification.mtplm_kilograms:,}kg gross weight recorded beside them"
        )

    if product.mh_height_mm is not None and product.mh_height_mm != specification.height_mm:
        complaints.append(
            f"the model page now publishes a height of {product.mh_height_mm:,}mm where "
            f"the 2027 specification says {specification.height_mm:,}mm — the stored "
            f"document may have been superseded, and with it this model's masses"
        )
    if product.mh_length_mm is not None and product.mh_length_mm != specification.length_mm:
        complaints.append(
            f"the range tile publishes a length of {product.mh_length_mm:,}mm where the "
            f"2027 specification says {specification.length_mm:,}mm. THE WEBSITE'S FIGURE "
            f"IS THE ONE RECORDED, on the requester's instruction of 12 November 2026 — "
            f"but the two disagreeing is worth knowing about"
        )
    return complaints


def _body_type(product: DreamerProduct) -> tuple[BodyType | None, str | None]:
    """Which of the four campervan body types this van is.

    Every Dreamer is a panel-van conversion — their own prose calls each one *"the converted
    van"* — so the prior question is settled and only the 2x2 is left: high top or not,
    elevating roof or not.

    The height decides the first and **only** the first. The roof decides the second, and it
    is the standard specification that counts: `UP` models carry the pop-up and say so, the
    rest are silent, and silence means option.

    **Except where silence is not evidence.** A model listed in `ROOF_UNSTATED` returns
    nothing at all, so FMLV's own body type survives the run rather than being overturned
    by a page that simply does not say.
    """
    height = product.mh_height_mm
    if height is None or product.elevating_roof is None:
        return None, None
    high_top = height > HIGH_TOP_ABOVE_MM
    if high_top and product.elevating_roof:
        body = BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF
    elif high_top:
        body = BodyType.CAMPERVAN_HIGH_TOP
    elif product.elevating_roof:
        body = BodyType.CAMPERVAN_ELEVATING_ROOF
    else:
        body = BodyType.CAMPERVAN
    shape = (
        f"{height:,}mm, above the {HIGH_TOP_ABOVE_MM}mm high-top threshold"
        if high_top
        else f"{height:,}mm, below the {HIGH_TOP_ABOVE_MM}mm high-top threshold"
    )
    roof = (
        "and the pop-up roof is standard on this model, which the page states as an extra "
        "sleeping area for two"
        if product.elevating_roof
        else "and no elevating roof is included in the standard specification"
    )
    return body, f"{shape}, {roof}"


def _transmission_lines(lines: list[str]) -> list[str]:
    """Only the equipment lines that say which engine and gearbox are offered.

    The whole list must never go through `gearbox.automatic_available_from`. The Select
    range's includes `Adaptive cruise control - manual transmission only`, which that
    function reads — correctly, on its own terms — as an automatic being ruled out. It is
    not: it is a caveat on a driver-assistance feature, and the line directly below it
    offers lane-keeping *"automatic transmission only"*, which proves an automatic exists.

    A line that states an offering names the make. That is the whole filter, and it is
    enough: `FIAT 140 hp automatic transmission, 3.5T - LIGHT DUTY` survives it and the
    cruise-control caveat does not.
    """
    return [line for line in lines if _TRANSMISSION_OFFER.search(line)]


# --------------------------------------------------------------------------- #
# Building the product
# --------------------------------------------------------------------------- #

#: The pictos that are **not** proposed as fields: quoted into the run so that whoever
#: types habitation in has Dreamer's own words, with the FMLV-ish meaning beside each.
_FINDING_PICTOS: tuple[tuple[str, str], ...] = (
    ("svg__frigo", "refrigerator"),
    ("svg__chauffage", "heating"),
    ("svg__eaux-propres", "fresh water"),
    ("svg__goutte", "waste water"),
    ("svg__dimension_int", "storage area H/L/W"),
)


def _habitation_lines(product: DreamerProduct) -> list[str]:
    """What the habitation module reads: the page's prose, plus the heater's own name.

    The heater is included because Dreamer name the unit rather than describe it, and the
    module knows a `TRUMA COMBI` is blown air. It is **not** paraphrased into a sentence
    first: a `WEBASTO 4 kW DIESEL` yields nothing, which is the right answer, because the
    fuel does not say whether the heat arrives as air or as water.
    """
    lines = list(product.prose)
    heater = product.pictos.get("svg__chauffage")
    if heater:
        lines.append(heater)
    # The specification document names the heater too, and more precisely than the model
    # page does: it is `WEBASTO 4 kW DIESEL` on the page and the same there, but the D64
    # is the one Select model on a Webasto rather than a Truma and only the document says
    # so. Both are offered to the habitation module; it reads whichever it understands.
    if product.specification is not None:
        lines.append(product.specification.heating)
    return lines


def _build_extracted_motorhome(product: DreamerProduct) -> ExtractedMotorhome:
    """One model as a `Motorhome`, with the provenance a reviewer reads beside each field.

    **The masses, the chassis and the heater come from `SPECIFICATION_2027`**, Dreamer's
    own 2027 specification document, and not from the website — which publishes none of
    them. Everything else is read live: the dimensions, the berths, the seats and the
    body type.

    **`rrp_pounds` is still deliberately absent.** Dreamer publish no price anywhere and
    FMLV holds one on all sixteen live rows, so emitting an empty one would propose
    deleting every one of them. It is left unset rather than emitted empty.

    **Where the document and the website disagree on a dimension, the website wins.**
    Requester's instruction, 12 November 2026: *"on Dreamer let the length stated on the
    website take precedent if there's a conflict like that."* The website is re-read every
    run and the document cannot be, so the website is the fresher of the two by
    construction. `_check_specification` still says when they diverge.
    """
    features = habitation.features_from(_habitation_lines(product))
    body_type, body_type_note = _body_type(product)
    specification = product.specification
    # Only used where the website gave no length at all; it never overrides one.
    specification_length = specification.length_mm if specification else None

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        berths=product.berths,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        body_type=body_type,
        # The website's dimensions, always — see the docstring. A length the document
        # disagrees with is narrated, not substituted.
        mh_length_mm=product.mh_length_mm or specification_length,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        mro_kilograms=specification.mro_kilograms if specification else None,
        mtplm_kilograms=specification.mtplm_kilograms if specification else None,
        mh_payload_kilograms=specification.payload_kilograms if specification else None,
        base_vehicle_manufacturer=_base_vehicle_of(specification),
        automatic_available=product.automatic[0] if product.automatic else None,
        # Habitation: findings, never proposals — see `docs/adapters/README.md`.
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

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=product.source_url,
            snippet=f"{product.label} — {snippet}",
        )

    record(
        "manufacturer_range",
        f"the {product.manufacturer_range} range. The website suffixes every Select "
        f"model's name with ' Select'; that suffix is the range and is not part of the "
        f"model, which is how FMLV holds it",
    )
    if product.mh_length_mm is not None:
        record(
            "mh_length_mm",
            f"{product.mh_length_mm:,}mm, from the range page's tile for this model. The "
            f"model page states a height and a width but never a length, so the tile is "
            f"the only place Dreamer publish it",
        )
    if product.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"{product.mh_height_mm:,}mm, from the specification block's exterior "
            f"dimensions, {product.dimensions_note!r}",
        )
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"{product.mh_width_mm:,}mm, from the specification block's exterior "
            f"dimensions, {product.dimensions_note!r} — a body width, mirrors excluded",
        )
    if product.berths is not None:
        record(
            "berths",
            f"the specification block states the standard and the options separately, "
            f"{product.berths_note!r}, so {product.berths} berths as built. Anything "
            f"behind the 'O' is a paid extra",
        )
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"the specification block's registered (driving) seats, "
            f"{product.seats_note!r}",
        )
    if specification is not None:
        source = (
            "Dreamer's 2027 specification document "
            "(COM_DRE_CT_Dreamer_EXPORT_2027_220x285_BD_EN.pdf), base finish. It is not "
            "on the website: it sits behind a name-and-email form, so this adapter holds "
            "a stored copy and audits it against the live site every run"
        )
        reconciles = (
            f"MIRO {specification.mro_kilograms:,}kg plus payload "
            f"{specification.payload_kilograms:,}kg is exactly the "
            f"{specification.mtplm_kilograms:,}kg gross weight published beside them"
        )
        record(
            "mro_kilograms",
            f"{specification.mro_kilograms:,}kg, from {source} — and it reconciles: "
            f"{reconciles}",
        )
        record(
            "mh_payload_kilograms",
            f"{specification.payload_kilograms:,}kg, from {source} — and it reconciles: "
            f"{reconciles}",
        )
        record(
            "mtplm_kilograms",
            f"{specification.mtplm_kilograms:,}kg, from {source}. Where Dreamer offer a "
            f"CHOICE of gross weight — most of the range is published as '3.5 T / 4.25 T' "
            f"— this is the lower, which is the base vehicle",
        )
        record(
            "base_vehicle_manufacturer",
            f"the specification's chassis row names {specification.base_vehicle!r}. From "
            f"{source}; the website names its three bases on a range-wide list with no "
            f"attribution to a model, which is why this could not be collected before",
        )

    if body_type is not None and body_type_note is not None:
        record("body_type", f"a converted van at {body_type_note}")
    if product.automatic is not None:
        record("automatic_available", gearbox.provenance_note(product.automatic))

    for field_name, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field_name] = Provenance(
            source_url=product.source_url,
            snippet=f"{product.label} — the specification says {feature.snippet!r}{detail}",
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #


def _feature_value(value: object) -> str:
    """One habitation value as a reviewer would type it into FMLV."""
    if isinstance(value, list):
        return ";".join(_feature_value(item) for item in value) or "none"
    return getattr(value, "value", str(value))


def _narrate_findings(product: DreamerProduct, on_progress: Callable[[str], None]) -> None:
    """Put everything this adapter will not propose in front of the reviewer."""
    quoted = [
        f"{label} {product.pictos[key]!r}"
        for key, label in _FINDING_PICTOS
        if key in product.pictos
    ]
    if quoted:
        on_progress(f"{product.label} — habitation, as Dreamer state it: " + " | ".join(quoted))

    features = habitation.features_from(_habitation_lines(product))
    if features:
        on_progress(
            f"{product.label} — read as: "
            + " | ".join(
                f"{name} = {_feature_value(feature.value)}"
                for name, feature in sorted(features.items())
            )
            + ". These are findings, so the review shows them on a NEW product only"
        )

    if product.elevating_roof is None:
        on_progress(
            f"{product.label} — body type NOT proposed: "
            f"{ROOF_UNSTATED.get(product.model, 'the roof could not be established')}"
        )

    belts = BELT_ROW_DISAGREES.get((product.manufacturer_range, product.model))
    if belts is not None:
        on_progress(
            f"{product.label} — SEATS WORTH A SECOND LOOK: {belts}. FMLV holds "
            f"{product.mh_passenger_seats_inc_driver}, which is what is proposed, and the "
            f"settled rule counts THREE-POINT belts only. Nothing is changed here because "
            f"reducing a live product's seat count is a decision for a person, and '2+2' "
            f"may describe the two rows of belts rather than every belt in the vehicle"
        )

    if product.seats_ceiling_note is not None:
        on_progress(
            f"{product.label} — travel seats NOT proposed: Dreamer publish "
            f"{product.seats_ceiling_note!r}, and the '(p)' footnote reads 'Maximum number "
            f"of authorised registered seats as defined by the chassis'. That is a ceiling "
            f"the chassis permits, not the seats the van is built with, so it is not a "
            f"figure FMLV records"
        )


def _narrate_absences(on_progress: Callable[[str], None]) -> None:
    """Say, once a run, which columns Dreamer no longer publish and why none is emitted."""
    on_progress(
        "The masses, the chassis and the heater come from Dreamer's 2027 SPECIFICATION "
        "DOCUMENT, a stored copy, because they appear nowhere on the website. It sits "
        "behind a name-and-email form that posts to itself, so a run cannot fetch it. "
        "Every row is audited each run: MIRO plus payload must equal the published gross "
        "weight, and the document's height and length must still match what the live site "
        "publishes. Divergences are narrated per model"
    )
    on_progress(
        f"The weights table that IS on the site, {SUPERSEDED_SPECIFICATION_TABLE}, is "
        "still ignored and still should be. It is LAST SEASON'S and covers the FUN range "
        "alone: every height in it is 40mm short of what the model pages state now, it "
        "lists ADDICT and EXCLUSIVE trims no longer sold, it numbers the vans D42/D53/D60 "
        "where the site now says D43/D55/D68, and it has no Camper Sport column at all"
    )
    on_progress(
        "NO PRICE is collected. Dreamer publish none anywhere, and FMLV holds one on all "
        "sixteen live rows, so emitting an empty one would propose deleting every one of "
        "them. The base vehicle DOES come through now, from the specification document — "
        "the website names its three bases on a range-wide list with no attribution to a "
        "model, which is why it could not be collected before"
    )


def _narrate_rename_candidates(on_progress: Callable[[str], None]) -> None:
    """Warn, before the diff does, that some of the 'new' products are probably renames."""
    on_progress(
        "BEFORE ACCEPTING ANY NEW PRODUCT: the site lists 19 models against FMLV's 16, and "
        "some of the difference is almost certainly renaming. Normally a rename is "
        "evidenced by matching the mass in running order, and this adapter collects no "
        "mass, so these cannot be settled here: "
        + "; ".join(f"FMLV {held!r} is probably {now}" for held, now in RENAME_CANDIDATES.items())
    )
    for note in AMBIGUOUS_IDENTITY:
        on_progress(f"IDENTITY NOT SETTLED — {note}")
    for held, why in NOT_ON_THE_SITE.items():
        on_progress(f"FMLV holds {held!r} and the site no longer lists it — {why}")


def _collect_tiles(http: Fetcher, on_progress: Callable[[str], None]) -> dict[str, int]:
    """Every model tile's length, from the home page and both range pages."""
    lengths: dict[str, int] = {}
    for url in (HOME_URL, FUN_RANGE_URL, SELECT_RANGE_URL):
        result = http.fetch(url)
        if result.status_code != 200:
            on_progress(f"{url} returned HTTP {result.status_code}")
            continue
        page = _read(result.file_path)
        for path, millimetres in parse_tiles(page).items():
            lengths.setdefault(path, millimetres)
    return lengths


def _check_roster(lengths: dict[str, int], on_progress: Callable[[str], None]) -> None:
    """Narrate a model page the range pages link that this adapter does not know."""
    known = {model.path.lower() for model in MODELS}
    for path in sorted(lengths):
        if path not in known:
            on_progress(f"NEW MODEL linked from a range page that this adapter does not know: {path}")
    for model in MODELS:
        if model.path.lower() not in lengths:
            on_progress(
                f"{model.model} ({model.manufacturer_range}) is no longer linked from a "
                f"range page, so it has no length this run and may have been withdrawn"
            )


def _collect_transmission(
    http: Fetcher, url: str, on_progress: Callable[[str], None]
) -> tuple[bool, str] | None:
    """Whether a range's equipment list offers an automatic."""
    result = http.fetch(url)
    if result.status_code != 200:
        on_progress(f"{url} returned HTTP {result.status_code}, so the gearbox is blank this run")
        return None
    page = _read(result.file_path)
    lines = [" ".join(line.split()) for line in gearbox.lines_from_page(page)]
    offers = _transmission_lines(lines)
    if not offers:
        on_progress(
            f"{url} states no engine-and-gearbox offering, so the website settles nothing "
            f"for that range. Silence is blank, never 'no'"
        )
        return None
    return gearbox.automatic_available_from(offers)


def _automatic_for(
    model: _Model, from_the_site: dict[str, tuple[bool, str] | None]
) -> tuple[bool, str] | None:
    """Whether this model is offered with an automatic, the site first.

    The live equipment list wins wherever it says anything, because it is re-read every
    run and the catalogue is not. It settles the FUN range and says nothing about Select,
    and that is where `CATALOGUE_AUTOMATIC` comes in — for the Select models the SAPHIR
    finish covers, which is all of them bar the three in `SELECT_WITHOUT_AUTOMATIC`.
    """
    live = from_the_site.get(model.manufacturer_range)
    if live is not None:
        return live
    if model.model in SELECT_WITHOUT_AUTOMATIC:
        return None
    return CATALOGUE_AUTOMATIC.get(model.manufacturer_range)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 - the whole site is static HTML
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` snapshots every request already
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Dreamer panel van the UK site lists, read one model page at a time."""
    wanted = {entry[-1] for entry in ranges}

    _narrate_absences(on_progress)

    lengths = _collect_tiles(http, on_progress)
    if not lengths:
        raise RuntimeError(
            f"neither {HOME_URL} nor either range page yielded a single model tile, and the "
            f"tile is the only place Dreamer publish a length"
        )
    on_progress(f"the range pages link {len(lengths)} model page(s)")
    _check_roster(lengths, on_progress)
    _narrate_rename_candidates(on_progress)

    transmission: dict[str, tuple[bool, str] | None] = {}
    for range_name, url in ((FUN, FUN_EQUIPMENT_URL), (SELECT, SELECT_EQUIPMENT_URL)):
        if range_name not in wanted:
            continue
        transmission[range_name] = _collect_transmission(http, url, on_progress)
        if transmission[range_name] is None and range_name in CATALOGUE_AUTOMATIC:
            _, why = CATALOGUE_AUTOMATIC[range_name]
            on_progress(
                f"automatic_available for the {range_name} range comes from the 2027 "
                f"CATALOGUE, not the website: {why}. The catalogue sits behind a "
                f"name-and-email form so a run cannot re-read it — if Dreamer change "
                f"this, nothing here will notice. NOT applied to "
                f"{', '.join(sorted(SELECT_WITHOUT_AUTOMATIC))}, which Dreamer's own "
                f"equipment table holds in separate columns from the SAPHIR finish and "
                f"which are offered only with a manual"
            )

    extracted: list[ExtractedMotorhome] = []
    for model in MODELS:
        if model.manufacturer_range not in wanted:
            continue
        result = http.fetch(model.url)
        if result.status_code != 200:
            on_progress(
                f"DROPPED {model.manufacturer_range} {model.model}: HTTP "
                f"{result.status_code} for {model.url}"
            )
            continue
        page = _read(result.file_path)
        product = parse_model_page(
            page, model, length_mm=lengths.get(model.path.lower())
        )

        identified, identity_note = _check_identity(product, model)
        if not identified:
            on_progress(f"DROPPED {product.label}: {identity_note}")
            continue
        intact, shape_note = _check_shape(product)
        if not intact:
            on_progress(f"DROPPED {product.label}: {shape_note}")
            continue

        roof_warning = _check_roof(product)
        if roof_warning is not None:
            on_progress(roof_warning)

        product.automatic = _automatic_for(model, transmission)
        product.specification = SPECIFICATION_2027.get(
            (model.manufacturer_range, model.model)
        )
        if product.specification is None:
            on_progress(
                f"{product.label} — NO MASS, NO CHASSIS and NO HEATER: this model has no "
                f"row in the stored 2027 specification document, so there is nothing to "
                f"take them from. A model Dreamer have added since 12 November 2026 will "
                f"land here, and the document needs re-requesting"
            )
        for complaint in _check_specification(product):
            on_progress(f"{product.label} — {complaint}")

        extracted.append(_build_extracted_motorhome(product))
        length = f"{product.mh_length_mm:,}mm" if product.mh_length_mm else "NO LENGTH"
        seats = (
            f"{product.mh_passenger_seats_inc_driver} belted seats"
            if product.mh_passenger_seats_inc_driver is not None
            else "seats not recorded"
        )
        masses = (
            f"MIRO {product.specification.mro_kilograms:,}kg, MTPLM "
            f"{product.specification.mtplm_kilograms:,}kg, payload "
            f"{product.specification.payload_kilograms:,}kg, "
            f"{product.specification.base_vehicle}"
            if product.specification is not None
            else "NO MASS and NO CHASSIS"
        )
        on_progress(
            f"{product.label}: {length} x {product.mh_width_mm or '?'}mm x "
            f"{product.mh_height_mm or '?'}mm, {product.berths} berths, {seats}, {masses}"
            f" — {identity_note}, {shape_note}. NO price, by design"
        )
        _narrate_findings(product, on_progress)

    expected = sum(1 for model in MODELS if model.manufacturer_range in wanted)
    if len(extracted) != expected:
        on_progress(
            f"collected {len(extracted)} products where the site lists {expected} for "
            f"{', '.join(sorted(wanted))}"
        )
    return extracted
