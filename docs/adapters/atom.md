# Atom — site survey

Surveyed 16 September 2026. **A brand new to FMLV**, which no other adapter has been: there
is no manufacturer id, no supplier name, no baseline export and no existing rows. Four
campervans on a VW Crafter.

**Not yet built.** See "What is still needed" at the foot.

## Whose brand is it

The requester introduced Atom as a sub-brand of Auto-Trail. The site is more specific, and
both halves matter:

> **"ATOM is a new campervan brand from Trigano"** — `/who-is-atom`
>
> **"Every ATOM is manufactured at our factory in Lincolnshire"** — `/manufacture`

Lincolnshire is Auto-Trail's factory. So **Auto-Trail build it and Trigano own the brand**,
which is the same shape as the rest of this group — Marquis, Auto-Sleepers, Benimar, Elnagh,
Mobilvetta, McLouis and Chausson are all Trigano.

FMLV already files Trigano marques under their own ids rather than as ranges of one another:

| id | `fmlv_manufacturer` |
| --- | --- |
| 35 | `Trigano S A McLouis` |
| 53 | `Trigano VDL Chausson` |
| 61 | `Auto-Trail` |
| 212 | `Auto-Sleepers Limited` |

And the Pilote group is three ids for one manufacturer — `Pilote`, `Joa by Pilote`,
`Le Voyageur`. **So a row of its own looks right rather than a range under Auto-Trail**, but
the id and the exact string are the NCC's to allocate, not this project's.

## The source: a JavaScript-rendered single-page app

`atommotorhomes.com` is a Vite SPA. Plain HTTP returns **3 kB and the single word "Atom"**,
so this is one of the few adapters that genuinely needs `fetch.browser.BrowserFetcher` —
`docs/adapters/README.md` warns against reaching for it first, and here the plain path was
tried and failed outright.

| page | what it carries |
| --- | --- |
| `/models` | **the comparison table** — all four layouts, every published field, one page |
| `/model/coreb`, `/coreg`, `/element-b`, `/element-g` | the same figures per layout, plus equipment prose |
| `/atom-config` | the configurator: mass in running order and prices |
| `/faq`, `/why-buy-an-atom` | corroborate the seat count in words |

**The comparison table is the source.** One fetch for the roster and the specification, with
the four model pages as the cross-check rather than the other way round.

## The roster: two ranges, two layouts each

The requester settled the naming on 16 September 2026: *"The models are called the Atom Core
B, Atom Core G, Atom Element B and Atom Element G."*

**FMLV renders a listing as manufacturer + range + model**, which is why `pilote.py` names
its panel vans `Van` rather than `Pilote Van` — see commit `be7bf49`, where the live site
showed "Pilote Pilote Van V630S". So the split is:

| range | model | renders as |
| --- | --- | --- |
| `Core` | `B` | Atom Core B |
| `Core` | `G` | Atom Core G |
| `Element` | `B` | Atom Element B |
| `Element` | `G` | Atom Element G |

The configurator calls them `Core 600B` and `Element 600G`, and the body copy `The Core
600 B` — the `600` being the 5.986 m length. **That naming is deliberately not used**, on the
requester's ruling above.

The four are mutually distinguishable to `diff/matching.py`: `{core, b}` against `{core, g}`
scores 0.333, well under the 0.5 threshold, so no two can be confused for one another.

## The figures, measured

From `/models`, identical across all four except where noted:

| | Core B | Core G | Element B | Element G |
| --- | --- | --- | --- | --- |
| Berths | 2 | 2 | 2 | 2 |
| **Seatbelts** | 2 | 2 | 2 | 2 |
| Length | 5986 | 5986 | 5986 | 5986 |
| Width (excl. door mirrors) | 2040 | 2040 | 2040 | 2040 |
| Height | 2710 | 2710 | 2710 | 2710 |
| Max authorised weight | 3500 | 3500 | 3500 | 3500 |
| Mass in running order † | 2720 | 2720 | 2810 | 2810 |
| Payload (derived) | 780 | 780 | 690 | 690 |

† from the configurator; the comparison table does not carry it.

**All four share every dimension**, which is not an error — one Crafter body, four interior
layouts. It does mean there is no cross-model variation to catch a misread, so the roster
count and the cross-page agreement are the structural defences.

### Width is published excluding mirrors, which is unusual and welcome

`Width (excl. door mirrors) 2040mm` — the settled rule's figure, stated outright. A Crafter's
body is about 2040 mm, so this needs none of the judgement `README.md` records for a
`mirrors folded` figure.

### Max authorised weight is the MTPLM

Confirmed with the requester on 12 September 2026 for Pilote: *"maximum authorised mass, MAM,
is for all intents and purposes the same as the MTPLM."* Atom print it as `Max. authorised
weight` on the model pages and `GVM` in the configurator, and both say 3500 kg.

### Seats: two, and only two

Stated three ways, which is worth recording because two belts on a campervan is low enough
to look like a parse error:

* the comparison table's `Seatbelts 2`;
* `/faq`: *"Both models also have two designated travelling seats"*;
* `/why-buy-an-atom`: *"Two travelling seats"*.

These are the cab seats. Nothing suggests a lap belt anywhere, so the settled rule to count
three-point belts only is satisfied.

### Body type: campervan high top

2710 mm clears the settled 2300 mm threshold. Confirmed by the requester from the
photographs, 16 September 2026.

## The site contradicts itself on height, and 2710 is right

| source | height |
| --- | --- |
| `/models` comparison table | **2710mm** |
| `/model/coreb`, `/model/coreg` | 2170mm |
| `/model/element-b`, `/model/element-g` | *not published* — a `Wheel base, mm 3640` row sits where the height is on the Core pages |

Transposed digits on the Core pages. 2710 mm is right for a Crafter carrying a full-height
shower — which every model has as standard — and 2170 mm is not. The requester settled it on
16 September 2026: *"I definitely take 2710 as they're definitely high top. I can see it from
the pictures. I think that's a typo."*

**It is not a cosmetic difference**: 2170 mm would put these below the 2300 mm threshold and
file all four as plain campervans rather than high tops.

So the comparison table is the source for height, and a model page that disagrees is noise.

## Prices are unsettled, and the site gives three answers

| source | Core B |
| --- | --- |
| `/atom-config`, headline | £60,210 |
| `/atom-config`, "Winter Sale Price" | £62,155 |
| `/why-buy-an-atom` | "Core models start from £61,940" |

The "sale" price being **higher** than the headline is the clearest sign these are not
settled. The requester, 16 September 2026: *"I think that's just a very temporary price"* —
an official price list is to follow, and is what the adapter should use.

Recorded here so the disagreement is not rediscovered: the configurator's other figures are
`Core 600G £59,550`, `Element 600B £66,535`, `Element 600G £65,870`, each with a higher
"Winter Sale Price".

## The self-check is weak, and that is worth stating plainly

`docs/adapters/README.md` asks for the arithmetic a manufacturer publishes against itself.
Atom publish **no payload at all**, so `MTPLM - MRO` cannot be checked against a printed
figure — the subtraction is the only route to the payload rather than a check on it.

What is available instead:

* **`3500 kg` appears in three places** — the model pages, the comparison table and the
  configurator — and they agree;
* **the comparison table and the model pages state the same length and width**, so a parse
  reading either can be checked against the other;
* **the roster is four**, stated by the navigation, the models page and `/manufacture`'s
  *"4 MODELS TO CHOOSE FROM"*.

The height is the one field where those sources **disagree**, and it is settled above.

## What is still needed before this can be built

1. **The NCC `manufacturer_id`.** Atom is absent from `resources/manufacturers-full-list.csv`.
   It is an NCC-side key and inventing one silently detaches every run from its history, so
   it has to be allocated rather than guessed.
2. **The exact `fmlv_manufacturer` string**, which is the join key — a trailing space or
   `Ltd` against `Ltd.` means the run finds an empty baseline and proposes every product as
   new.
3. **The `ncc_supplier_name`**, from the supplier drop-down on the NCC export page.
4. **The official price list**, which the requester is sending.

## Still unverified

* **Whether a new manufacturer runs end to end with no baseline at all.** Every product will
  be classified new, which is correct, but no adapter has been built against an empty
  baseline before and the path is untested.
* **Floorplans**, and whether Core B/G and Element B/G differ enough to record different
  habitation fields. The B models are described as a twin-bench layout and the G models as
  an expedition layout, but the comparison table lists identical equipment for all four.
* **Whether the site settles.** The contact page carries placeholder addresses
  (`new.email1@example.com`, `tel:+4401111111111`), so it is newly launched and still moving.
