"""Campod: one small towed caravan sold in two editions, not four models.

## The range is two products, and that is the finding

Campod's site sells **one configurable caravan** plus a **Laura Ashley edition**. The
product page has exactly two dropdowns, `Colour scheme` and `MTPLM`, and the second
offers 800, 900 and 1000 kg with a price for each. The chassis rating is an option, not a
model.

FMLV instead holds the ratings as separate products — `M` at 900 kg and `N` at 1000 kg —
which is how they used to be sold. The requester settled it on 21 September 2026:

> *"M and N aren't sold as separate models anymore. They simply sell a Campod Caravan
> with slightly different options … take the lower end of the weight spectrum as the base
> for a Campod Caravan and then the lower option for the Laura Ashley version, which is
> the 900 kilogram, which would leave us just with two models."*

So two products, each at the bottom of its own range:

| | MTPLM | MiRO | payload |
|---|---|---|---|
| `Campod` | **800** (900 and 1000 are upgrades) | 750 | 50 |
| `Laura Ashley` | **900** (1000 is the upgrade) | 775 | 125 |

That is the settled base-vehicle rule, and the page states it in as many words:
*"800kg (upgrade to 900kg & 1,000kg available)"*.

## `M` becomes the Campod; `N` retires

`RENAMED_MODELS` maps the standard caravan onto `M`, the lower-rated of the two, so one
product id keeps its images and its hand-entered habitation flags. `N` is left unmatched
and disappears.

**This is a consolidation, not a rename discovery**, and the distinction matters. The
usual test — same mass in running order, therefore the same vehicle — does not apply:
all three FMLV rows already share one set of dimensions, and `M` and `N` differed only by
a chassis rating that is now an option. Choosing `M` preserves a row rather than
identifying one, and the run says so.

## What the site does not publish

**A mass in running order per chassis rating.** One figure, 750 kg, which is the base.
The only hint it varies is prose on the home page: *"a MiRO of 750kg's to 800kg's"*.
FMLV's `M` holds 790 and `N` 800 — both inside that range, neither derivable from
anything published, and both about to be superseded by the base figure anyway.

**A payload**, so it is derived. **A price for the Laura Ashley**, so none is proposed for
it. **Anything Campod call a micro**: the word appears only inside Wix's own JavaScript
(`microphone`, `microPop`), never in their copy, so the naming half of the micro test
fails while 800 kg passes the weight half easily. FMLV holds `type_micro` on all three
rows and emitting nothing leaves it standing — the same position as T@B and Mink.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.caravan import Caravan
from ..vehicle_class import VehicleClass
from .base import ExtractedCaravan, Provenance

__all__ = [
    "BASE_URL",
    "EXPECTED_LAYOUTS",
    "LAURA_ASHLEY_URL",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "PRODUCT_URL",
    "RENAMED_MODELS",
    "VEHICLE_CLASS",
    "CampodCaravan",
    "collect",
    "parse_laura_ashley",
    "parse_product_page",
    "visible_lines",
]

BASE_URL = "https://www.campodcaravans.com"
PRODUCT_URL = f"{BASE_URL}/product-page/campod-caravan"
LAURA_ASHLEY_URL = f"{BASE_URL}/laura-ashley-campod"

#: Byte-for-byte the export's `manufacturer`. **Two registry rows share this string** —
#: 130 and 253 — so the display name is what tells them apart and it is part of the
#: adapter key. The export carries `Campod` on every row, which is 253's.
MANUFACTURER = "Leisure Pods Ltd"
MANUFACTURER_DISPLAY_NAME = "Campod"

VEHICLE_CLASS = VehicleClass.CARAVAN

#: FMLV's range for every Campod row.
FMLV_RANGE = "O2"

#: Two, after the consolidation — see the module docstring.
EXPECTED_LAYOUTS = 2

#: The standard caravan takes over `M`'s row so its images and habitation flags survive.
#: `N` is deliberately left to disappear: it was the 1000 kg rating, which is now an
#: option on the one product rather than a product of its own.
RENAMED_MODELS: dict[tuple[str, str], tuple[str, str]] = {
    (FMLV_RANGE, "Campod"): (FMLV_RANGE, "M"),
}

_TAGS = re.compile(r"<[^>]+>")
_BLOCK_TAGS = re.compile(
    r"<(tr|/tr|li|/li|dt|dd|br|p|div|h\d|td|/td|th|/th|span)\b[^>]*>", re.I
)
_SCRIPTS = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)

#: `4305 mm`, `2340mm` — the space is not always there.
_MILLIMETRES = re.compile(r"^(\d{3,5})\s*mm\b", re.IGNORECASE)

#: `800kg (upgrade to 900kg & 1,000kg available)` and `900kg/1,000kg`. **The first figure
#: is the one recorded**: on both pages the alternatives that follow are upgrades, which
#: the product page spells out and the Laura Ashley page implies by listing the lower
#: first. Thousands separators are optional and stripped.
_KILOGRAMS = re.compile(r"^(\d{1,3}(?:,\d{3})?)\s*kg\b", re.IGNORECASE)

#: Every price on the product page. There are three, one per chassis rating, and the
#: **lowest** belongs to the 800 kg base this adapter records.
_PRICE = re.compile(r"£\s?(\d{1,3}(?:,\d{3})+)(?:\.\d{2})?")


def visible_lines(html: str) -> list[str]:
    """The page as the reader sees it, one text run per line.

    Both pages put a label on one line and its value on another, sometimes with blank or
    decorative runs between, so the parse is label-then-next-value throughout.
    """
    text = _SCRIPTS.sub(" ", html)
    text = _BLOCK_TAGS.sub("\n", text)
    text = _TAGS.sub(" ", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return [
        stripped
        for line in text.splitlines()
        if (stripped := re.sub(r"[ \t]+", " ", line).strip())
    ]


def _line_after(
    lines: list[str], label: str, pattern: re.Pattern[str], *, within: int = 6
) -> str | None:
    """The first line matching `pattern` within a few lines of an exact `label`.

    A **window** rather than the next line, because the Laura Ashley page puts two
    decorative runs between `MiRO` and `775kg`.

    And every occurrence of the label is tried, not just the first, because
    **`MTPLM` labels two different things on the product page**: the chassis dropdown,
    whose next line is the `*` marking it required, and the Weights block, which is the
    one wanted. Stopping at the first match reads the asterisk.
    """
    wanted = label.casefold()
    for index, line in enumerate(lines):
        if line.casefold().rstrip(":") != wanted:
            continue
        for candidate in lines[index + 1 : index + 1 + within]:
            if pattern.match(candidate):
                return candidate
    return None


def _value_after(
    lines: list[str], label: str, pattern: re.Pattern[str], *, within: int = 6
) -> int | None:
    """The figure out of `_line_after`, or `None`."""
    found = _line_after(lines, label, pattern, within=within)
    if found is None:
        return None
    match = pattern.match(found)
    return int(match.group(1).replace(",", "")) if match else None


@dataclass
class CampodCaravan:
    """One of the two products, as read."""

    model: str
    mtplm_kilograms: int | None
    mro_kilograms: int | None
    rrp_pounds: int | None = None
    #: The alternatives the page offers alongside the base, for the provenance to name.
    upgrades: str = ""
    shipping_length_mm: int | None = None
    overall_width_mm: int | None = None
    height_mm: int | None = None
    headroom_mm: int | None = None

    @property
    def label(self) -> str:
        return f"{FMLV_RANGE} {self.model}"

    @property
    def derived_payload_kilograms(self) -> int | None:
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def parse_product_page(lines: list[str]) -> CampodCaravan:
    """The standard Campod, with the dimensions every model shares.

    The `MTPLM` line reads `800kg (upgrade to 900kg & 1,000kg available)`, and 800 is
    what is recorded: the rating is a dropdown option and the base vehicle is the one
    FMLV holds.
    """
    # The Weights block's MTPLM line, not the dropdown's: see `_line_after`.
    mtplm_line = _line_after(lines, "MTPLM", _KILOGRAMS) or ""
    prices = [int(p.replace(",", "")) for p in _PRICE.findall(" ".join(lines))]
    return CampodCaravan(
        model="Campod",
        mtplm_kilograms=_value_after(lines, "MTPLM", _KILOGRAMS),
        mro_kilograms=_value_after(lines, "MiRO", _KILOGRAMS),
        # The lowest of the three, which is the 800kg base's.
        rrp_pounds=min(prices) if prices else None,
        upgrades=mtplm_line,
        shipping_length_mm=_value_after(lines, "Total length", _MILLIMETRES),
        overall_width_mm=_value_after(lines, "Total width", _MILLIMETRES),
        height_mm=_value_after(lines, "Total height", _MILLIMETRES),
        headroom_mm=_value_after(lines, "Standing height", _MILLIMETRES),
    )


def parse_laura_ashley(lines: list[str], shared: CampodCaravan) -> CampodCaravan:
    """The Laura Ashley edition. Its own masses; the standard caravan's dimensions.

    Its page states `MiRO 775kg` and `MTPLM 900kg/1,000kg` and no dimensions at all —
    it is the same shell, which FMLV confirms by holding one set across all three rows.
    """
    return CampodCaravan(
        model="Laura Ashley",
        mtplm_kilograms=_value_after(lines, "MTPLM", _KILOGRAMS),
        mro_kilograms=_value_after(lines, "MiRO", _KILOGRAMS),
        # Its page carries no price at all; FMLV's own stands.
        rrp_pounds=None,
        upgrades=_line_after(lines, "MTPLM", _KILOGRAMS) or "",
        shipping_length_mm=shared.shipping_length_mm,
        overall_width_mm=shared.overall_width_mm,
        height_mm=shared.height_mm,
        headroom_mm=shared.headroom_mm,
    )


def _reconciles(product: CampodCaravan) -> tuple[bool, str]:
    """Is the page coherent enough to propose?

    **A weak check, and worth saying so.** Campod publish no payload, so there is no
    arithmetic to test the parse against, and the whole specification is a dozen lines on
    one page. What is checked is that both masses are present, ordered, and in a band a
    towed pod could occupy.
    """
    mtplm, mro = product.mtplm_kilograms, product.mro_kilograms
    missing = [
        name for name, value in (("MTPLM", mtplm), ("MiRO", mro)) if value is None
    ]
    if missing:
        return False, f"its page states no {', '.join(missing)}"
    if not 400 <= mro < mtplm <= 1500:
        return False, (
            f"masses that cannot both be right: MTPLM {mtplm}kg and MiRO {mro}kg"
        )
    return True, (
        f"MTPLM {mtplm}kg minus MiRO {mro}kg, both read from the page's own Weights block"
    )


def build_extracted(product: CampodCaravan, *, source_url: str) -> ExtractedCaravan:
    """One product as a `Caravan` plus the provenance a reviewer sees beside it."""
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=FMLV_RANGE,
        model=product.model,
        mtplm_kilograms=product.mtplm_kilograms,
        mro_kilograms=product.mro_kilograms,
        personal_effects_payload_kilograms=product.derived_payload_kilograms,
        rrp_pounds=product.rrp_pounds,
        shipping_length_mm=product.shipping_length_mm,
        overall_width_mm=product.overall_width_mm,
        height_mm=product.height_mm,
        headroom_mm=product.headroom_mm,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    renamed = RENAMED_MODELS.get((FMLV_RANGE, product.model))
    moved = (
        f'; this takes over FMLV\'s "{renamed[1]}" row so its images and habitation '
        f"flags survive. M and N were the 900kg and 1000kg ratings, which Campod now "
        f"sell as a dropdown option on one caravan rather than as separate models, so "
        f"N is retired"
        if renamed
        else ""
    )
    record(
        "manufacturer_range",
        f'range "{FMLV_RANGE}", which is what FMLV holds for every Campod — accept with '
        f"the model, they are one name",
    )
    record(
        "model",
        f'model "{product.model}"{moved} — accept with the range, they are one name',
    )

    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"MTPLM: {product.upgrades or product.mtplm_kilograms} — the FIRST figure, "
            f"which is the base vehicle. The larger ratings are a dropdown option on the "
            f"same caravan and are not recorded",
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"MiRO (Mass In Running Order, or 'Factory Weight' as Campod gloss it): "
            f"{product.mro_kilograms}kg, the figure beside the base MTPLM. Campod publish "
            f"no MiRO per chassis rating — only prose saying it runs 750kg to 800kg",
        )
    if product.derived_payload_kilograms is not None:
        record(
            "personal_effects_payload_kilograms",
            f"{product.derived_payload_kilograms}kg, derived as MTPLM minus MiRO. Campod "
            f"publish no payload at all",
        )
        record(
            "optional_equipment_payload_kilograms",
            "Campod publish no payload split, so there is no separate "
            "optional-equipment payload. Left blank so the two columns sum to the derived "
            "figure",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"GBP {product.rrp_pounds:,}, the LOWEST of the three prices on the product "
            f"page — one per chassis rating — so it is the 800kg base's",
        )
    for field_name, label in (
        ("shipping_length_mm", "Total length"),
        ("overall_width_mm", "Total width"),
        ("height_mm", "Total height"),
    ):
        value = getattr(product, field_name)
        if value is not None:
            record(field_name, f"{label}: {value} mm")
    if product.headroom_mm is not None:
        record(
            "headroom_mm",
            f"Standing height: {product.headroom_mm} mm (6 ft 3\"), which Campod achieve "
            f"with a recessed footwell. NOTE FMLV holds 1930mm and the site and the "
            f"requester's own dimension diagram both say 1905",
        )

    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = (),  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Both Campod products: the standard caravan and the Laura Ashley edition."""
    on_progress(f"reading the product page: {PRODUCT_URL}")
    standard = parse_product_page(
        visible_lines(
            http.fetch(PRODUCT_URL).file_path.read_text(encoding="utf-8", errors="replace")
        )
    )

    on_progress(f"reading the Laura Ashley page: {LAURA_ASHLEY_URL}")
    laura = parse_laura_ashley(
        visible_lines(
            http.fetch(LAURA_ASHLEY_URL).file_path.read_text(
                encoding="utf-8", errors="replace"
            )
        ),
        standard,
    )

    extracted: list[ExtractedCaravan] = []
    for product, url in ((standard, PRODUCT_URL), (laura, LAURA_ASHLEY_URL)):
        reconciles, reason = _reconciles(product)
        if not reconciles:
            on_progress(f"dropping {product.label} — {reason}")
            continue
        extracted.append(build_extracted(product, source_url=url))
        on_progress(
            f"read {product.label}: MTPLM {product.mtplm_kilograms}kg, MiRO "
            f"{product.mro_kilograms}kg, payload {product.derived_payload_kilograms}kg, "
            + (f"GBP {product.rrp_pounds:,}" if product.rrp_pounds else "no price")
        )

    on_progress(
        "CAMPOD NOW SELL TWO CARAVANS, NOT FOUR MODELS. The product page has two "
        "dropdowns, Colour scheme and MTPLM, and the MTPLM one offers 800/900/1000kg with "
        "a price each — the chassis rating is an OPTION. FMLV's M and N were the 900 and "
        "1000 ratings sold as separate products; on the requester's ruling (21 September "
        "2026) the standard caravan is recorded once at the bottom of its range, 800kg, "
        "and the Laura Ashley once at the bottom of its own, 900kg."
    )
    on_progress(
        "M TAKES OVER AS THE STANDARD CAMPOD and N RETIRES. Mapping the caravan onto M "
        "keeps one product id with its images and hand-entered habitation flags; N is "
        "left unmatched and will show as disappeared. That is a CONSOLIDATION, not a "
        "rename discovery — all three FMLV rows already share one set of dimensions and "
        "M and N differed only by a rating that is now an option, so choosing M preserves "
        "a row rather than identifying one."
    )
    on_progress(
        "NOT PROPOSED: the BODY TYPE, because Campod never call these micros — the word "
        "appears only inside Wix's own JavaScript (microphone, microPop), so the naming "
        "half of the micro test fails though 800kg passes the weight half easily, and "
        "FMLV's type_micro stands. A PRICE FOR THE LAURA ASHLEY, whose page carries none. "
        "And the body length, internal length and awning length, which the site does not "
        "publish at all."
    )
    if len(extracted) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} products and collected {len(extracted)}"
        )
    on_progress(f"collected {len(extracted)} Campod caravan(s)")
    return extracted
