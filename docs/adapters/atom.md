# Atom — site survey

Surveyed 16 September 2026. **A brand new to FMLV**, which no other adapter has been: there
is no manufacturer id, no supplier name, no baseline export and no existing rows. Four
campervans on a VW Crafter.

**Built 16 September 2026.** Run #102: four collected, four correctly new, 44 proposals and
10 habitation findings against an empty baseline.

FMLV manufacturer id **278**, allocated by the NCC on 16 September 2026.

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

The press pack confirms the split outright — *"2 model ranges — CORE and ELEMENT (each
having the 2 different layouts)"*, with **CORE the standard specification and ELEMENT the
enhanced one** (page 7). The letters are the layout: *"2 different layouts — rear bench seat
models and rear garage models"*, so **B is bench and G is garage**.

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
* `/why-buy-an-atom`: *"Two travelling seats"*;
* the press pack, page 7, from the other direction: *"Within the next year, we will also
  introduce 4 seat belt 4 berth models"* — which only makes sense if today's are two.

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

## Prices: the press pack settles them, and explains the site

**`ATOM - Press Presentation - Sept. 2026`, page 14**, supplied by the requester on
16 September 2026, carries the official table. The **on-the-road price is the one recorded**,
per the settled rule that FMLV holds the manufacturer's headline OTR figure:

| | ex works (incl. VAT) | **on the road** |
| --- | --- | --- |
| Core 600B | £62,155 | **£62,600** |
| Core 600G | £61,495 | **£61,940** |
| Element 600B | £68,480 | **£68,925** |
| Element 600G | £67,815 | **£68,260** |

That resolves all three figures the website gives:

* the configurator's **"Winter Sale Price"** is the **ex works** price — £62,155 for the
  Core 600B, exactly the pack's column. It is mislabelled on the site, which is why it
  appears *above* the headline rather than below it;
* the configurator's headline (£60,210 and friends) is the **launch promotion**. Page 6:
  *"we are aiming to have a launch promotion to enable customers to have an effective
  starting price of £59,950 OTR"*;
* `/why-buy-an-atom`'s *"Core models start from £61,940"* is the **Core 600G's OTR price**,
  and agrees with the pack exactly.

**So the site alone would have given the wrong figure**, and no reading of it would have
revealed which of the three was the price. Whether the adapter can take OTR from the site at
all is unresolved — the configurator publishes the ex works and promotional figures, not the
OTR one. See "What is still needed".

**The B costs more than the G**, in both ranges, which is worth stating because it looks
inverted: £62,600 against £61,940, and £68,925 against £68,260.

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

## The pack and the site disagree on the water tanks

| | press pack, page 12 | `/models` comparison table |
| --- | --- | --- |
| Fresh | 60 ltr | 80 l |
| Waste | 80 ltr | 60 l |

**Swapped, not merely different.** Neither is a field FMLV records, so nothing turns on it —
but it is a second place where the site and the pack disagree, after the height, and it says
something about how settled either source is. Worth re-checking if a water capacity is ever
added to the schema.

## Sold online only, which bears on the supplier name

> *"ATOM models will only be sold Online direct to end customers. They will not be a stocked
> product at a network of dealers."* — press pack, page 15

There is no importer or dealer network to name, unlike every Marquis brand. Warranty and
service run through the ATOM sales HQ at Melton *"but will utilise Auto-Trail factory
applications"* (page 16), and the leadership on the introductions slide is Auto-Trail's —
Shane Devoy (MD), Scott Stephens (Commercial Director), Paul Gorry (Head of Marketing).

So the `ncc_supplier_name` has no obvious external candidate: it is Atom, or Auto-Trail, and
that is the NCC's to decide.

## The id, and a name that is not unique

**278**, allocated on 16 September 2026. The build ran on a provisional 9001 before that,
chosen outside the NCC range because Atom was absent from
`resources/manufacturers-full-list.csv` altogether; the registry row, `data/exports/`,
`data/snapshots/` and the three existing runs were all repointed when the real id arrived.

**`Trigano` is not a unique `fmlv_manufacturer`, and that is worth knowing before anyone
adds another Trigano brand.** The NCC list already holds:

| id | name | display name |
| --- | --- | --- |
| 187 | `Trigano` | Silver |
| 222 | `Trigano` | Mini Freestyle |
| 278 | `Trigano` | **Atom** |

Which confirms the naming — the Swift/Ace pattern is Trigano's own house style too — but
`adapters.ADAPTERS` is keyed on `(manufacturer, vehicle_class)`, so **a second Trigano
motorhome adapter would silently overwrite this one**. `registry.loader` cross-checks
duplicate `manufacturer_id`s and duplicate `website_url`s but not duplicate
`fmlv_manufacturer`, so nothing would warn. Left alone because no such adapter exists; it
needs solving the day Silver or Mini Freestyle is added.

## An empty baseline, which no adapter has faced before

`cli.latest_export` **raises** when a manufacturer has no export rather than assuming an
empty baseline, and rightly — that guard is what stops a forgotten download turning every
product into a duplicate. A genuinely new brand has no export to forget, though, so
**`fmlv empty-baseline <manufacturer>`** writes a header-only one:

```
fmlv empty-baseline Atom
```

It is not an export and does not come from the NCC — those are downloaded per supplier and
there is nothing to download yet. It writes the schema's header row and nothing else, into
the same `<id>_<name>` directory a real export would, so the two are interchangeable and
`latest_export` supersedes it the moment a real one is fetched. It **refuses** where an
export already exists, since an empty baseline over a real one would classify every product
as new.

Deliberately a command rather than a flag on `run`, and deliberately not automatic: writing
one is a statement that this manufacturer is new, which is exactly the thing a reviewer
should not discover by accident.

The pipeline then says the right thing on its own:

> *the export has no rows for 'Trigano', so every scraped product was classified as new —
> check the export and that the registry's fmlv_manufacturer matches its 'manufacturer'
> column*

**Expected here and alarming anywhere else.** Once the first upload creates the four
products, a real export replaces the empty one and the warning stops.

## Uploading the products does not create the supplier

**Found the hard way on 16 September 2026**, and it is the step no document described.

The four products uploaded cleanly and appear in Nova with product codes. The review app's
trigger still failed, because a triggered run refreshes the export first and the NCC's
`Export Products by Supplier` drop-down — `select#exhibitor` — **still does not list Atom**.

There is no supplier or exhibitor column anywhere in `schema.COLUMNS`, so nothing in the
upload could have created or linked one. It is an NCC-side record, separate from the
products and from the manufacturer, and it has to be created there.

**So a brand new to FMLV needs three things, not two:**

1. a **manufacturer** — 278, `Trigano` / `Atom`, created before the first run;
2. its **products**, from the first upload;
3. a **supplier/exhibitor record** matching `ncc_supplier_name`, which is what makes the
   export — and therefore every future run — possible at all.

Until the third exists there is no export, so the pipeline cannot see the products it just
created. **Do not upload again in that state**: every run still diffs against the empty
baseline, classifies all four as new, and a second upload would duplicate them.

The name has to match `ncc_supplier_name` exactly. If the NCC create it as something other
than `Atom`, the registry column changes rather than the record.

## Still unverified

* ~~Whether a new manufacturer runs end to end with no baseline~~ — **it does**, see above.
* **Floorplans**, and whether Core B/G and Element B/G differ enough to record different
  habitation fields. The B models are described as a twin-bench layout and the G models as
  an expedition layout, but the comparison table lists identical equipment for all four.
* **Whether the site settles.** The contact page carries placeholder addresses
  (`new.email1@example.com`, `tel:+4401111111111`), so it is newly launched and still moving.
* **The 4-belt, 4-berth models** the pack promises *"within the next year"* (page 7), and the
  6.8 m wheelbase it says may follow the 6 m one (page 6). The roster is four today and the
  count is pinned, so both will surface as a roster warning rather than silently.
* **Whether a price brochure appears on the site**, which would settle the OTR question
  above.

## Two things the build changed

### The equipment is in prose, not in a list

`habitation.list_items` finds **twelve** items on a model page and every one is navigation:
Atom render their specification as divs. The first run produced **zero findings** because of
it. The facts are in the prose instead — *"There's also a 70ltr compressor fridge with
integrated freezer included"*, *"Truma heating and hot water all as standard"* — so
`copy_lines_from` splits the page into sentences and `habitation` reads those. Ten findings
now.

One gap left alone: the B models' *"twin benches easily make up into two single berths"*
yields no bed type, because `habitation.bed_types_from` requires the word **bed** and this
says **berths**. That is a shared-vocabulary change affecting every adapter, so it is not
made here.

### A row must have exactly four columns, not at least four

The first version took the first four figures in a row and ignored anything after, so a
**fifth model would have been silently dropped** — the run would collect the same four for
ever and the roster count, which is the main defence here, would never fire. Atom have said
in writing that a fifth is coming: four-belt four-berth models within the year, and a 6.8 m
wheelbase after the 6 m one. The row pattern now refuses a fifth column outright.
