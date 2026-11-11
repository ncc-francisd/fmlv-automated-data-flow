# Robeta — survey and adapter

**Surveyed and built 11 November 2026.** The adapter is `src/adapters/robeta.py`.

**NCC id 255**, `Robeta`.

Robeta d.o.o., Pohorska cesta 6b, 2380 Slovenj Gradec, **Slovenia** — `info@robeta.si`.
Premium panel-van conversions on Fiat and Mercedes, sold in the UK through **Cara
Motorhomes & Caravans**.

**The spelling is `Robeta`, one `t`, everywhere** — confirmed by the requester on
11 November 2026. The NCC manufacturer list at id 255, **the NCC supplier export
dropdown**, the FMLV export's `manufacturer` column, `caramotorhomes.co.uk/robeta-motorhomes/`
and `robeta-campervans.com` all agree. He says "Robetta" in conversation; none of the
systems does.

| | Robeta |
|---|---|
| JavaScript needed | **No** — both sites serve static HTML |
| Products | **6**, which is exactly what FMLV holds |
| Price | **Cara's sterling "Price from"**, matching FMLV to the pound |
| Weights | **MIRO, MTPLM and payload, for all six**, from Cara |
| Dimensions | **All three in millimetres, for all six**, from Cara |
| Berths / seats | Factory only, **and published as ranges** — the open question |
| Self-check | `payload == MTPLM − MIRO`, holds on all six |

## Two sources, importer first

The requester's instruction, 11 November 2026: *"given Cara has got some technical
information, we should get it from there first. And if there's some missing, we then try
and seek it from the European website."* That is also the settled rule — the UK importer
defines the range and the price, the factory decides the numbers — and here the importer
happens to publish the numbers too.

### Cara Motorhomes — the price, the masses and the dimensions

`caramotorhomes.co.uk/robeta-motorhomes/the-range/<slug>/`, one page per model, each with
a plain HTML `<table>`:

```html
<h2>Adonis</h2>
<p>Price from £105,290</p>
<table class="table is-fullwidth"><tbody>
<tr><td>MIRO (kg)</td><td>2980</td></tr>
<tr><td>MTPLM (kg)</td><td>3500</td></tr>
<tr><td>Payload (kg)</td><td>520</td></tr>
<tr><td>Height (mm)</td><td>2690</td></tr>
<tr><td>Width (mm)</td><td>2070</td></tr>
<tr><td>Length (mm)</td><td>5930</td></tr>
```

| model | price | MIRO | MTPLM | payload | L | W | H |
|---|---|---|---|---|---|---|---|
| Adonis | £105,290 | 2980 | 3500 | 520 | 5930 | 2070 | 2690 |
| Apollo | £73,328 | 3025 | 3500 | 475 | 6360 | 2050 | 2654 |
| Ares | £69,228 | 2765 | 3500 | 735 | 5410 | 2050 | 2654 |
| Helios | £71,428 | 2930 | 3500 | 570 | 5990 | 2050 | 2654 |
| Kronos | £71,928 | 2930 | 3500 | 570 | 5990 | 2050 | 2654 |
| Schumacher Edition | £272,331 | 4125 | 5500 | 1375 | 7400 | 2020 | 2825 |

**All forty-two of those values match FMLV's six rows exactly**, so FMLV's current Robeta
data was taken from these pages. That is unusually good news for an adapter: a first run
should confirm rather than propose.

**`payload == MTPLM − MIRO` on all six.** That is the self-check, and it is a real one —
Cara publish the three independently in three table rows.

### Do not read `/vehicle-details/` on Cara

The `vehicles-sitemap.xml` lists thirty-two pages of the shape
`/vehicle-details/new-robeta-apollo-for-sale-cara-motorhomes-caravans-ltd-n447/`. **Those
are individual units for sale**, so a mass on one is that van's plate and that van's
options, not the model's — the trap already recorded against a specific unit's listing.
Cara also sell **Sunlight, Adria, Auto-Trail, Coachman and VW** stock under the same URL
shape, so a loose match would pull in other manufacturers' vehicles entirely.

The model pages carry no `<loc>` in any Cara sitemap, so the roster is discovered by
following `/robeta-motorhomes/the-range/<slug>/` links out of the Robeta section.

### The factory site — berths, seats and habitation

`robeta-campervans.com` is a Next.js site serving **static HTML**, and every model page
embeds **schema.org JSON-LD**:

```json
{"@type":"Product","name":"ROBETA ARES","offers":{"price":"64890.00","priceCurrency":"EUR"},
 "additionalProperty":[
   {"name":"Sleeping Capacity","value":"2 - 6"},
   {"name":"Main Bed Dimensions","value":"187 x 130"},
   {"name":"Pop-up Roof Bed Dimensions","value":"200 x 160 cm"},
   {"name":"Refrigerator","value":"65L pull-out drawer compressor fridge"},
   {"name":"Cooker/Sink","value":"Dometic dual gas cooker/sink combo with cover"},
   {"name":"Fresh Water Tank","value":"97L"}]}
```

That is a better parse target than the rendered page and it carries most of the habitation
findings for free. The euro price is **not** wanted — Cara's sterling figure is the UK
price and it is already correct in FMLV.

## The roster is six, and the factory's is bigger

**Cara list exactly six**, matching FMLV. The factory lists more:

* **Hercules** — a new Mercedes model with its own `/models/hercules` page and a launch
  blog post, *"Private Mercedes-Benz grand tourer for two"*.
* **Dionysus** — appears only in the contact form's model dropdown.
* **Ananya** — a "glampervan" with its own section of the site.

**None of the three is on Cara**, so none is in the UK range. Hercules has never been in
FMLV either: the February 2026 and November 2026 exports hold the same six products, the
same prices, and the same gap at product id 8731.

## Berths, and the roof: settled 11 November 2026

**Robeta publish capacities as spans**, and FMLV held the top of every sleeping one:

| model | published sleeping | FMLV held | recorded |
|---|---|---|---|
| Adonis | 2 – 4 | 4 | **2** |
| Apollo | 2 – 6 | 6 | **2** |
| Ares | 2 – 6 | 6 | **2** |
| Helios | 2 – 6 | 6 | **2** |
| Kronos | 2 – 4 *(lineup)* / 2 – 6 *(model page)* | 4 | **2** |
| Schumacher Edition | 2 adults | 2 | 2 — unchanged |

The requester settled it in two steps, from his own research.

**First, the roof.** It is an option on five models and standard on none, and the
Schumacher Edition is not offered with one at all — *"All of them have the option, none of
them are standard, but the Schumacher edition does not have the option. That's the only
one."* Every published source already said it was an option; what he settled is that it is
**never** fitted as standard, and which single model cannot have it.

**Then the second bed.** Taking two off the published maximum would have left the Apollo,
Ares and Helios at four — but their six needs **two** options, not one. Robeta say so on
the Apollo: *"sleeping space for six featuring an electrical lifting bed in the Family
Edition and a 1.45m x 2.2m pop-up roof bed"*, and the Family Edition is listed as available
on exactly those three. His conclusion: *"the birth number on each model is going to
be 2."*

So **two across the range**, which is also the lower end of every published span — the
settled berth-range rule landing in the same place by a different route. See
`STANDARD_BERTHS`, which is the one place to change if a model ever ships with a roof or a
lifting bed as standard.

### Seats: four belts, settled 11 November 2026

The requester, from his own research: *"the standard number of three-point seatbelts is 4,
when you haven't got the upgraded configuration. So that's the driver plus passenger, and
then a bench seat behind of 2 more."* Only three-point belts count, which is the settled
rule and the terms the figure is already in.

**This is the number the published spans could never give, and why is worth keeping.** The
standard sits at a *different place in each span*:

| model | published `Seating Capacity` | where four sits | FMLV held |
|---|---|---|---|
| Ares | `4 - 5` | the **lower** end — *"can be upgraded to seat up to 5"* | 5 |
| Adonis | `2 - 4` | the **upper** end — the *"for Two"* package removes seats | 4 ✓ |
| Kronos | `2 - 4` | the **upper** end | 4 ✓ |
| Apollo | `2 - 5` | the **middle**, reachable from neither end | 5 |
| Helios | `2 - 5` | the **middle** | 5 |

Four is consistent with every one of them, and two of them agree with it independently —
the Ares's span *starts* at four and the Adonis's *ends* at four. That is a real check
rather than a restatement: a span that merely contained four would prove nothing.

So three rows change — Apollo, Ares and Helios from five to four — and the Adonis and
Kronos verify unchanged.

**The Schumacher Edition is two, not four.** Robeta publish its `Seating Capacity` as `2`
outright, and it is a two-berth grand tourer with a floating bed and **no rear bench** —
which is the thing the requester's figure counts. Recording four would contradict the
maker's own explicit number.

## Body type

**Every Robeta is a plain high top.** All six clear the 2,300 mm threshold on height alone
— 2,654 mm on the four Fiats, 2,690 mm on the Adonis, 2,825 mm on the Schumacher Edition —
and none has an elevating roof as standard, so none is
`type_campervan_high_top_elevating_roof`.

That corrects **two FMLV rows**: the Helios (8729) and the Kronos (8730), both of which
were held as high tops *with* an elevating roof. The height never settled this on its own;
the roof did.

## Cara are not the exclusive importer, but they are the only usable UK source

The factory's `/dealers` page lists **43 dealers across 16 countries, and two in the United
Kingdom**:

| | |
|---|---|
| **Cara Motorhomes & Caravans Ltd** | Butterhill Bank, Burston, Stafford ST18 0DT |
| **SC Sporthomes Ltd** | Units 1–5 Panteg Industrial Estate, Griffithstown, Torfaen NP4 5LX |

So Cara are an **appointed dealer, not an exclusive importer**, and their "Price from" is a
dealer's price rather than an importer's list. That matters less than it might: **SC
Sporthomes publish nothing usable** — their `/robeta` page carries no price and no number
of any kind, and their store is unedited template content (`product-page/i-m-a-product`).
There is no conflicting UK price to reconcile today.

It is worth knowing for two reasons. If SC Sporthomes ever publish prices they may differ,
and the two dealers could in principle stock different models — so the roster is "what Cara
list", which happens to match FMLV, rather than "what the UK gets" in any stronger sense.

## What is still open

1. **Whether FMLV should carry Hercules**, which the factory sells and neither UK dealer
   lists.

Nothing else. Every field this adapter can reach is now emitted.

Settled since the survey, and left here so the record shows what moved:

* **`ncc_supplier_name`** — `Robeta`, one `t`, confirmed 11 November 2026 against the NCC
  supplier export dropdown.
* **Whether the pop-up roof is standard** — it is not, on any model, and the Schumacher
  Edition is not offered one. That settled `berths` at two throughout and made every model
  a plain high top.
* **The standard travel-seat count** — four three-point belts on the five with a rear
  bench, two on the Schumacher Edition.
* **The Kronos's sleeping capacity**, which the factory states as `2 - 4` on the lineup
  card and `2 - 6` on the model page. The conflict is now moot: both ends above two are
  optional, so the figure recorded is two either way. Worth remembering if Robeta ever
  publish a standard count, because one of those two pages is wrong.
* **The fridge** — `fridge_freezer` on all six.

## Built, 11 November 2026 — and the first run confirmed rather than proposed

Run #221, against both live sites: **six products, 1 changed, 5 unchanged, 0 new, 0
disappeared, and 50 fields checked and unchanged.** That is what it looks like when the
adapter has been pointed at the same source a person used by hand.

The **one real change** is `automatic_available` → `Yes` on the Schumacher Edition, off
Cara's own prose — *"a 2.0, four cylinder engine with automatic gearbox"*. The other five
stay blank, correctly: neither site mentions a gearbox for them, and
`/standard-equipment-stelantis` does not either. The vocabulary did its job there — the
only thing on that page matching `automatic` is *"Electric valve for grey water (automatic
emptying)"*, which it rightly ignored.

Everything else proposed is a year bump or one of the twelve deliberate blanks below.

### What the adapter does not emit, and why

`berths`, `mh_passenger_seats_inc_driver` and `body_type` carry **no provenance**, so they
are never proposed and FMLV's own figures stand untouched. That is the open question of
this adapter rather than a gap in the sources:

* **The capacities are spans of configurations, not the vehicle as built** — `Sleeping
  Capacity 2 - 6`, `Seating Capacity 4 - 5`.
* **The upper sleeping figure comes from the pop-up roof, which is an upgrade** on every
  factory model page, and which Cara invite you to add.
* **The two ends swap round between models**, so one rule cannot serve both. The Adonis's
  *"for Two" package replaces the travelling seats*, so its standard seating is the
  **upper** figure; the Ares *"can be upgraded to seat up to 5"*, so its standard is the
  **lower**.
* **Body type turns on the same roof question.** All six clear the 2,300mm threshold on
  height alone, so high-top is certain and elevating-or-not is not.

`_narrate_open_questions` prints the published span and the roof caveat for each product on
every run, so the question stays visible. When Cara answer, it is one place to change.

### How it is put together

| | |
|---|---|
| Roster | Cara's Robeta section — the model pages are in **no sitemap** |
| Price, MIRO, MTPLM, payload, L/W/H | Cara's `<table>` on each range page |
| Habitation, capacities, chassis | the factory's schema.org JSON-LD |
| Self-check | `payload == MTPLM − MIRO`, a hard drop on failure |

Two details that would be easy to undo by accident. **`RANGE_LINK` only ever matches
`/robeta-motorhomes/the-range/`** — widening it would pull in `/vehicle-details/`, which is
individual stock and carries five other manufacturers' vehicles. And **the Adonis's own
factory page has no `Product` block**; it embeds the whole lineup array instead, which is
why `factory_properties` returns a map keyed by product name rather than a single block,
and why `collect` reads the lineup page before the model pages.

### A fridge disagreement that the pipeline will not show you

`store.changes` records habitation findings **only for a new product**, and all six Robeta
products are matched, so none appears in the review. The adapter still reads them, and one
is worth knowing about: **FMLV holds `fridge` on five of the six and `fridge_freezer` on
one**, while Robeta's own wording — *"65L pull-out drawer compressor fridge"*, *"85L
compressor refrigerator"* — gives `fridge_freezer` under the house default for a fridge
whose freezer is neither stated nor ruled out.

**Settled on 11 November 2026**: the requester is confident these refrigerators include a
freezer section, so `fridge_freezer` is right on all six and **five FMLV rows need flipping
by hand at the next upload** — 8726 Adonis, 8727 Apollo, 8728 Ares, 8729 Helios and
8730 Kronos. 8732 Schumacher Edition already holds it, which is what suggests the other
five were an oversight rather than a decision.

Because the review will never show this, the run now narrates **both** the manufacturer's
words and what they were read as — `read as: refrigeration = fridge_freezer` — on every
product, every run.
