# Beauer — survey, 14 October 2026

French expanding caravans, sold in the UK by **River Motorhomes**, who this repo already
reads as the importer for Mink Campers. The source is their own site,
`https://www.rivermotorhomes.co.uk/beauer-new/<model>/`.

**Not in `resources/manufacturers-full-list.csv`, and not on FMLV.** So this is a genuinely
new brand and needs the three-step bootstrap in [`README.md`](README.md) — a manufacturer
row with an NCC-allocated id, the products from a first upload against `fmlv
empty-baseline`, and a **separate supplier/exhibitor record** that the upload cannot
create.

## Three models, and the prices are on the importer's site

| | price | MTPLM | fully equipped | payload |
|---|---|---|---|---|
| **X4** | £39,990 | 1350 | 1200 | 150 |
| **X6** | £74,990 | 1800 | 1700 | 100 |
| **X8** | £109,990 | 2700 | 2600 | 100 |

The `/beauer/` index links all three and carries all three prices, so the roster is
rediscoverable rather than written in. Note the index links `/beauer-new/<model>/` while
the older `/beauer/<model>/` path also still resolves — follow the index.

## There is a published self-check, and it holds on all three

`Weight of the fully equipped trailer` + `Payload` = `Gross Vehicle Weight Rating`:

```
X4   1,200 + 150 = 1,350 ✓
X6   1,700 + 100 = 1,800 ✓
X8   2,600 + 100 = 2,700 ✓
```

Three terms published for every model and the arithmetic closes exactly, which is as good
a check as any manufacturer surveyed gives.

**Two cautions on reading it.** `Gross Vehicle Weight Rating` is the MTPLM. The *fully
equipped* figure is footnoted *"depending on the options selected"*, so it is not plainly a
mass in running order — it may be an optioned weight, which is the thing the base-vehicle
rule exists to refuse. And the payload is the **total**, not the personal-effects half, so
it must not go into `personal_effects_payload_kilograms` without checking.

## The trap: every model publishes two widths

These caravans telescope, and the page gives both states:

| | closed W × L × H | **extended** |
|---|---|---|
| X4 | 1950 × 3850 × 2650 | W 4600, H 2000 |
| X6 | 2150 × 7200 × 2670 | W 3600 |
| X8 | 2050 × 6650 × 2900 | W 4800, H 2000 |

**The travelling (closed) figures are the ones FMLV wants.** Recording an extended width
would put 4600mm in a column where 1950mm belongs — a caravan wider than a motorway lane.
The extended *height* is lower than the closed height on the X4 and X8 (2000 against 2650),
so a naive "take the larger" or "take the smaller" rule gets it wrong in opposite
directions on different fields. The reading has to be anchored on the
`Dimensions when extended` heading and everything under it discarded.

Everything is in **millimetres**, which is better than most sources manage.

## Two layouts per model, which may or may not be two products

The equipment lists are footnoted `* Layout 1 / ** Layout 2` and the page has `Interior
Design 1` and `Interior Design 2` tabs. They differ in real ways — the X4's Layout 1 has a
130L fridge and a shower, Layout 2 a 91L fridge and a large shower with a retractable sink.

Whether that is one FMLV product or two is a question for the requester, not a derivation.
Both layouts share one price, one MTPLM and one set of dimensions, which argues for one
product; the differing equipment argues for two.

## The habitation findings are unusually well served

The accordion carries a full equipment list per model: `Dometic 12V/220V 157L Compression
Refrigerator`, `Large shower, 70 × 80`, `Thetford Cassette Chemical Toilet`, `6-Liter
Electric Water Heater`, `Kitchen sink + 2-burner gas stove`, `AL-KO Chassis`, `AL-KO
Stabilizer`, bed sizes per room.

**No space heater is listed on any model** — a water heater is not heating. That is the one
gap worth checking rather than recording as `no_heating`.

## The body type needs the requester's eye

An expanding caravan is not one of the four caravan types. It is not folding (no canvas)
and not a pop-up, and the settled rule that *a lifting roof does not change a caravan's
body type* points at **rigid**. The micro test is satisfied anyway — the lightest is
1350kg, above the 1250kg ceiling, and Beauer call none of them a micro.

## Verdict

**Buildable, and a good candidate.** One importer who decides the range and the price, a
published self-check that closes on every model, dimensions in millimetres, and an
equipment list good enough for the habitation findings. Three products is small, but it is
a brand FMLV does not hold at all.

The work is mostly in the two traps: discarding the extended dimensions, and deciding
whether the fully-equipped weight is a mass in running order.

---

# Built — 15 October 2026

`src/adapters/beauer.py`, **NCC id 280**, registered as a caravan brand. Four fetches: the
`/beauer/` index and the three model pages it links. Plain HTML throughout.

## The dealer-page rule is broken here on purpose, and the licence is checked every run

The settled rule says specifications are not read off a dealer page. This does, because it
was verified rather than assumed: **River have republished Beauer's own copy verbatim** —
the same wording and the same figures to the kilogram — while the factory's own pages do
not expose the dimensions to a plain fetch.

`FACTORY_WEIGHTS` holds Beauer's three published masses per model, and `_reconciles` tests
every page against them. **If River ever edit a number, the product is dropped and the run
says so**, so the licence to read a dealer lasts exactly as long as the dealer stays
faithful.

## Run #174 — the first one

```
baseline    0 products
scraped     3 products
classified  0 changed, 0 unchanged, 3 new, 0 disappeared
proposed    48 changes
findings    3 habitation readings
```

| | price | berths | MTPLM | MRO | travelling L×W×H | axle |
|---|---|---|---|---|---|---|
| **X4** | £39,990 | 4 | 1350 | 1200 | 3850 × 1950 × 2650 | single |
| **X6** | £74,990 | 6 | 1800 | 1700 | 7200 × 2150 × 2670 | single |
| **X8** | £109,990 | 8 | 2700 | 2600 | 6650 × 2050 × 2900 | **twin** |

### The baseline read zero, and that is correct

A mock X4 (product 9203, range `Traveler`) was placed in Nova to give the run something to
match against. It carries **`active: No`**, so the baseline scope excluded it and all three
models arrived as new. The pipeline did the right thing.

**There is no `Traveler` range.** `Travelers` on Beauer's page is the English word, used as
a capacity label — *"Designed for up to 4 travellers"*. Beauer give these models no range
name at all, so each is a one-name product carrying its name twice, and the display name is
fixed by hand after upload.

## The four traps

**1. Every model publishes two widths.** The body telescopes, and the page gives
`Dimensions` and `Dimensions when extended` under the same labels. The X4 is 1950mm closed
and **4600mm extended**.

The reading cannot be rescued by comparing magnitudes: the extended **width** is far larger
than the travelling one while the extended **height** is *smaller* (2000 against 2650), so
"take the larger" and "take the smaller" are each wrong on one field. `technical_data`
keys on the sub-heading, which is the only thing that separates them.

**2. All the heating is an option.** `Heating + 2,000 W Webasto gas or electric underfloor
water heater` and `Truma 1800W Eezy Electric Heater` sit in the `Options` accordion on all
three models, and neither line marks itself as an extra. Read whole, the page gives every
Beauer wet underfloor heating it has not got. Equipment is read **by section**.

A second-order version of the same thing: the only line that then mentions a heater is the
`6-Liter Electric Water Heater`, which heats water rather than the caravan. Reporting that
as "heating of an undetermined kind" would send a reviewer hunting for a system that is not
there, so the run names it for what it is.

**3. The cookie banner is an accordion.** Its container reuses `accordion-header`, so its
"heading" is several hundred words of consent copy and four branches' opening hours. Any
heading over 60 characters is furniture.

**4. The weight list's `<li>`s are unclosed.** Only the last one is terminated, so the item
pattern has to stop at the next `<li>` or the end of the list.

## Four things deliberately not recorded

* **The payload.** Beauer publish one figure and it is the **total**, not the
  personal-effects half FMLV's column holds, and a brand new to FMLV has no baseline to
  show which way it files them. Used for the self-check only.
* **The body length.** One length is published and Beauer do not say whether it includes
  the drawbar, so only the shipping length is proposed.
* **The second layout.** Each model offers Layout 1 and Layout 2, differing in fridge,
  shower and table. They share one price, one gross weight and one set of dimensions and
  carry **no name of their own**, so the settled rule makes them a choice rather than a
  second product.
* **Any heating**, for the reason above.

The mass in running order **is** recorded, but its provenance says plainly that Beauer
footnote it *"depending on the options selected"*, so it may include fitted options. It is
their only published mass and it matches their own site exactly.

## The price is recorded and flagged every run

Beauer price the X4 at **39.990 €** and River at **£39,990** — the same digits with the
symbol changed. At 1.15 euros per pound the French price is about **£34,774**.

Nothing in either source settles whether that is an ordinary import uplift or a currency
slip, so `price_note` prints the comparison on every run and the figure recorded is
River's: they are the UK seller and the price is theirs to state.

## Still to ask

1. **Is £39,990 right**, or has a euro figure been carried across? See above.
2. **Is the `fully equipped` weight a mass in running order**, or an optioned figure?
3. **One product per model, or two?** The layouts are recorded as one.

