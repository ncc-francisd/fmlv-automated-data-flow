# Robeta — survey and adapter

**Updated 12 November 2026: the UK range is eight, not six.** See "The roster was six".


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

## The roster was six; from 12 November 2026 it is eight

**Cara's website lists exactly six**, matching FMLV, and still did on 12 November 2026.
The factory lists more:

* **Hercules** — a Mercedes grand tourer with its own `/models/hercules` page.
* **Ananya** — a "glampervan" with its own section of the site and its own brand.
* **Dionysus** — appears only in the contact form's model dropdown.

Until 12 November 2026 the adapter collected none of the three, on the grounds that the
importer defines the range and no UK seller listed them. **Then the importer said
otherwise.** John Burton, General Manager of Cara Motorhomes, to the NCC directory:

> *"There are 2 new models within the Robeta range for 2027, Hercules and Ananya, you can
> view them all at www.robetauk.co.uk"*

That settles the range, because the importer's word is what defines it — **their website
lagging behind their own email is not evidence against them.** Both are now collected.
The Dionysus was not named and is still left out.

### The link in that email is not a new source

`www.robetauk.co.uk` looks like a UK importer site and is not one. It serves the factory
homepage, its `<link rel="canonical">` points at `https://www.robeta-campervans.com/`,
and every sub-path 404s. It is a domain alias, so there is nothing on it to read that
`robeta-campervans.com` does not already have.

### What collecting them costs

Everything numeric in this adapter comes from Cara, because Cara are the ones who publish
numbers. These two have no Cara page, so they come with **no price, no mass, no
self-check and no habitation reading** — see `robeta.FACTORY_ONLY`. In particular:

| | Hercules | Ananya |
|---|---|---|
| length | 6.97 m | 6.97 m |
| height | *not published* | 2.66 m |
| berths | 2 | *not published* |
| travel seats | 4 | 3 |
| MIRO / MTPLM / payload | *none* | payload 1,362 kg only |
| price | €130,990.44, tagged `eligibleRegion: DE` | €198,000 **net** |
| base vehicle | Mercedes | Mercedes (Sprinter 419 CDI long 4x4) |

**Neither price is usable.** The Hercules's is a German RRP at a German VAT rate; the
Ananya's is explicitly *net*, which is to say excluding VAT. This project's euro
conversion assumes a domestic VAT-inclusive price, so converting either would invent a UK
figure rather than convert one.

**Neither mass is usable either.** The Hercules publishes none. The Ananya publishes
*"Base chassis rating (Sprinter 419): 4,100 kg. Category B registration is possible only
if the completed vehicle is homologated at 3,500 kg"* — two candidate plated weights with
no way to tell which a UK buyer gets — and a payload with no MIRO or MTPLM to sit against.

**And their habitation is not read.** The other five are read from the factory's
structured `additionalProperty` block; these two have only marketing prose, and running
that through `habitation.features_from` produced two wrong findings on the first run: the
Ananya's `refrigeration` out of *"maybe a mini-fridge if you're lucky"* — a sentence about
how **other** manufacturers build vans — and the Hercules's out of its *optional*
140-litre refrigerator rather than the 90-litre one its own specification list gives as
standard. Both would have reached a reviewer with a plausible quotation attached.

They are collected anyway, because a product with a name, dimensions, berths and seats is
worth more than no product, and a blank required column does not block an upload.

### Two page layouts, because Robeta built them on different stacks

* the **Hercules** has a Next.js `The essentials` definition list — `<dl>` of
  `<dt>Length</dt><dd>6.97 m</dd>` pairs — read by `parse_launch_specs`;
* the **Ananya** sits on a Webflow sub-site with a `Key facts` bullet list —
  `<li><strong>Vehicle Length: </strong>6.97 meters</li>` — read by `parse_key_facts`.

Neither carries the `additionalProperty` JSON-LD the other five use. The Hercules's only
JSON-LD is an `offers` block holding the German price; the Ananya's is an `Organization`.

### The Hercules's berth count may be read straight; the others' may not

The factory lineup block gives the Hercules `Sleeping Capacity 2` — a plain number — where
the other five get spans like `2 - 6`. That difference is the whole point:
a span is a set of configurations needing a judgement about which options are standard,
and a plain number is the vehicle as built. `_standard_berths_from` refuses a span, so if
Robeta ever start offering options on the Hercules its berth count stops being proposed
rather than silently becoming wrong.

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

**The Schumacher Edition is two, not four** — confirmed by the requester the same day:
*"The Schumacher edition is strictly two seats for seatbelts as well as two berths."*
Robeta publish its `Seating Capacity` as `2` outright, and it is a two-berth grand tourer
with a floating bed and **no rear bench**, which is the thing the four-belt figure counts.

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

All five are questions for Cara, who answer, and all five concern the two models they
named as new for 2027:

1. **A UK price for the Hercules and the Ananya.** Neither published figure is a UK one —
   a German RRP and a net price.
2. **MIRO, MTPLM and payload for both.** Nothing is published for the Hercules at all,
   and the Ananya gives a payload against two candidate plated weights.
3. **The Hercules's height and width**, which would also give it a body type — it is
   plainly a high top in the photographs, but a dimension is what decides that and there
   is none.
4. **The Ananya's berth count.** The factory publishes no sleeping capacity for it.
5. **How many of the stated seats are three-point belts** — four on the Hercules, three
   on the Ananya, with no belt type given, and only three-point belts are counted.

Two further things worth watching rather than asking:

* **A Cara range page appearing for either model** at
  `/robeta-motorhomes/the-range/hercules/` or `.../ananya/`. That would supply the price,
  the masses and the arithmetic self-check in one go, and the run narrates the absence
  every time so it cannot be missed.
**Settled 12 November 2026: the Ananya is listed.** It was raised as the one entry a
person might reasonably decide against — own brand site (`glam-van.com`), own logo, three
seats, a 4,100 kg Sprinter 4x4 base and a €198,000 net price. The requester settled it the
same day: *"I can't see any reason why the Ananya wouldn't be listed in FMLV at the
moment. If he's saying that that's available in the UK, so yeah, it looks like a range
name, or a company even, but there's only one model so I can't think of a reason why
not."* Availability in the UK is the test, and a name that reads like a brand is not a
reason to withhold a vehicle that is on sale here.

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
freezer section, so `fridge_freezer` is right on all six. **Five FMLV rows hold plain
`fridge`** — 8726 Adonis, 8727 Apollo, 8728 Ares, 8729 Helios and 8730 Kronos — and he is
changing them by hand; 8732 Schumacher Edition already holds it, which is what suggests
the other five were an oversight rather than a decision.

Because the review will never show this, the run now narrates **both** the manufacturer's
words and what they were read as — `read as: refrigeration = fridge_freezer` — on every
product, every run.
