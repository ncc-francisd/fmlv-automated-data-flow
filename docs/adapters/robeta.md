# Robeta — survey and adapter

**Surveyed and built 11 November 2026.** The adapter is `src/adapters/robeta.py`.

**NCC id 255**, `Robeta`.

Robeta d.o.o., Pohorska cesta 6b, 2380 Slovenj Gradec, **Slovenia** — `info@robeta.si`.
Premium panel-van conversions on Fiat and Mercedes, sold in the UK through **Cara
Motorhomes & Caravans**.

**The spelling is `Robeta`, one `t`.** The NCC manufacturer list reads `Robeta` at id 255
and the FMLV export's `manufacturer` column reads `Robeta`. The requester referred to it as
"Robetta"; `ncc_supplier_name` has not been read off the NCC export dropdown and is the one
identity field still unverified.

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

## The open question: berths, and whether the pop-up roof is standard

**Robeta publish capacities as ranges**, and FMLV holds the top of every sleeping one:

| model | factory sleeping | factory seating | FMLV berths | FMLV seats |
|---|---|---|---|---|
| Ares | 2 – 6 | 4 – 5 | 6 | 5 |
| Helios | 2 – 6 | 2 – 5 | 6 | 5 |
| Kronos | 2 – 4 *(lineup)* / 2 – 6 *(model page)* | 2 – 4 | 4 | 4 |
| Apollo | 2 – 6 | 2 – 5 | 6 | 5 |
| Adonis | 2 – 4 | 2 – 4 | 4 | 4 |
| Schumacher Edition | 2 adults | load capacity 5 | 2 | 2 |

**The factory says the pop-up roof is an upgrade**, in the same words on every model page:

> Pop-up Roof — Add versatile living space with our pop-up roof solution. **This upgrade**
> provides an additional sleeping area with a comfortable mattress.

Its FAQ is blunter: the Helios has an *"optional pop-up roof"*, and *"The Ares can be
upgraded to seat up to 5 people … and with a pop-up roof, it can sleep up to 6 people."*
**Cara agree**, on the Adonis page: *"Or looking to travel with 4 passengers, why not add a
pop top?"*

On the settled lower-figure rule that makes the berths **2** on five of the six, and makes
**no model an elevating-roof campervan** — against FMLV, which marks the Helios and Kronos
`type_campervan_high_top_elevating_roof`.

**The requester said on 11 November 2026 that the elevating roofs are standard.** Every
published source read here says the opposite. He may be right about what Cara actually
supply in the UK — the importer defines the UK range, and a UK vehicle built with the roof
fitted as standard would be an elevating-roof campervan whatever the factory's generic page
says. **This must be settled with him and with Cara before any adapter is written**,
because it decides `berths` and `body_type` on five of six products.

### Seats run the other way, so do not apply one rule to both ends

The Adonis's **"for Two" package *removes* travelling seats** — *"Just the two of you
travelling? The Adonis for Two package replaces the travelling seats with more storage"*.
So for seating the **upper** figure is the standard one, and FMLV's seat counts already
look right. Reading both ends of both ranges as "take the lower" would be wrong.

## Body type

**All six are high tops on height alone** — 2654 mm on the four Fiats, 2690 mm on the
Adonis, 2825 mm on the Schumacher Edition, every one above the settled 2300 mm threshold.
So `type_campervan_high_top` for all six, and
`type_campervan_high_top_elevating_roof` only for whichever models turn out to have the
pop-up roof as standard — which on the published evidence is none.

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

## What is unverified

1. **`ncc_supplier_name`**, which has not been read off the NCC export dropdown. The NCC
   manufacturer list says `Robeta`; the requester said "Robetta".
2. **Whether the pop-up roof is standard on UK vehicles**, which decides `berths` and
   `body_type` on five of six products. Every published source says it is an upgrade.
3. **The Kronos's sleeping capacity**, which the factory states two different ways —
   `2 - 4` on the lineup card, `2 - 6` in the model page's JSON-LD.
4. **Whether FMLV should carry Hercules**, which the factory sells and neither UK dealer
   lists.

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

Robeta say nothing either way about a freezer on any model. The run narrates the
`Refrigerator` string verbatim for each product so the call can be made from their words
rather than from the default.
