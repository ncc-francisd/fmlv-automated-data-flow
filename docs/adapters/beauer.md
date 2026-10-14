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

## To ask

1. **Is the `fully equipped` weight a mass in running order**, or an optioned figure? The
   footnote says it depends on the options selected.
2. **One product per model, or two** — the layouts share every figure but differ in fridge,
   shower and table.
3. **Is there any space heating?** Nothing on any page lists one.
4. **Does Beauer need an NCC id allocating**, and is River the exhibitor of record?
