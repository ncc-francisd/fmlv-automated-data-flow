# Pilote — site survey

Surveyed 10 September 2026. FMLV manufacturer id **105**, name **`Pilote`**, display name
the same, NCC supplier name the same. Motorhomes and campervans, no caravans. Forty-three
layouts for 2027; FMLV holds 51 live 2027 rows. **No adapter yet** — see "What is still
blocking the build".

## What the requester brought to the survey

* Manufacturer and supplier names are both **`Pilote`**.
* *"They describe their ranges not by the names, but by their type — A-class, low profile,
  compact low profiles, and panel vans, meaning camper vans."* Exactly right, and it is
  the single most important fact about this source. See "The slug is the range name".
* *"They have an excellent and very clear technical section that you click on after you've
  clicked on the floor plan."* Also right, and it is the problem: see the click below.
* On the panel vans — *"it's difficult to say whether the Van Vega Standard is the same as
  the Pilote Van... the V630S looks incredibly similar."* Confirmed, and settled below.
* Two 2027 documents, supplied by email on 10 September: a **UK vehicle price list** and an
  **Options & Offers brochure**.

## The source: 43 model pages

`pilote-motorhome.uk/<body-type>/<layout>-<offer>/`, plain server-rendered WordPress. **One
URL is one vehicle**, so there is no column-alignment risk anywhere in this brand. The
roster is `vehicule-sitemap.xml`, which lists 44 entries — the 43 pages plus a broken
`%taxo%` placeholder that must be dropped.

### The slug is the range name

The site navigates by body type and never shows an FMLV range name, but the slug carries
both halves of it, and the pair maps exactly:

| body type in the slug | offer in the slug | FMLV `manufacturer_range` | pages |
| --- | --- | --- | --- |
| `a-class` | `expression` | Galaxy Expression | 12 |
| `a-class` | `evidence` | Galaxy Evidence | 5 |
| `low-profile` | `expression` | Pacific Expression | 9 |
| `low-profile` | `evidence` | Pacific Evidence | 4 |
| `compact-low-profile` | `atlas` | ATLAS | 4 |
| `panel-van` | `pilote` | Pilote Van | 6 |
| `panel-van` | `evidence` | Van Vega Evidence | 3 |

**The offer is part of the identity.** One layout code appears under two offers at two
prices — G740FC is £86,900 as Expression and £94,900 as Evidence — so `model` alone is
never an identity here, and the range must be resolved before the match.

### Van Vega Standard is retired into Pilote Van

The requester's ruling, 10 September 2026. FMLV split the six standard-offer vans across
two range names — `Pilote Van` (V600G, V630J, V633M) and `Van Vega Standard` (V540G,
V630S) — and the site has them under one slug, `-pilote`, with the word Vega appearing
nowhere on the website. Four of the six already match the price list to the pound across
both names, which is what makes it one range rather than a coincidence.

So **all six emit as `Pilote Van`**, two rows are renamed, and V630B joins as new. Note
that the price list calls this block *Vega Expression*; the site's own offer name is
`pilote`, and the requester chose the site's.

**Van Vega Evidence is a different offer and stays** — three pages, three price rows, and
£7,000 to £13,000 above the Pilote Van equivalents.

## Three sources, and each one is needed

Revised 11 September 2026, once the click existed and showed what the panel actually
holds. Less of this comes from the emailed documents than the survey first assumed.

| what | where it comes from | refetchable per run? |
| --- | --- | --- |
| roster, range, model | `vehicule-sitemap.xml` | **yes** |
| length, width, height, **MTPLM**, payload | the popup's technical table | **yes — behind a click** |
| berths, seats | the summary strip and the brochure | **yes** / emailed |
| habitation findings | the page's `Standard fittings` section | **yes — server-rendered** |
| floorplan | the model page | **yes** |
| price | UK vehicle price list | no — emailed |

### The roster reconciles three ways, 43 for 43

The sitemap has 43 pages. The price list has 43 rows. The brochure's layout tables have 43
columns. All three carry the same 43 layout-and-offer pairs, with no page unpriced and no
price unpaged. For a source whose numbers arrive by email, that is the strongest available
evidence that the documents and the website describe the same collection.

### The pages publish no price at all

Checked directly: not one `£` in the HTML of any page. So **every one of the 43 prices is a
manually sourced constant** off a document that is not on the website — a far bigger
exposure than Joa's three van prices, and it has to be re-supplied at each rollover.

The list is headed **"Public price incl. VAT excluding transport"**. Joa's list, from the
same group, says "incl. 20% VAT **and** transport" and heads its column *Delivered*. Two
brands of one group on two bases, so **nothing about price may be shared between the two
adapters**.

## What is still blocking the build

**The click capability exists as of 11 September 2026** — `BrowserFetcher.fetch` and
`fetch_with_capture` both take a `click_selector` — and it was proved against
`/a-class/g690gj-expression/`. `click_selector="text=Technical information"` with a
3-second settle reveals:

```
Technical information
Length 7,07 m   Width 2,79 m   Height 2,85 m
Berth 4   Meal place 5   Sleeping place 4   Payload 485 kg
```

and, better than expected, **a full per-model `Standard fittings` list** — Chassis-Engine,
Cab fittings, Living area bodywork, Multimedia, Energy-Autonomy, Exterior accessories,
Lounge and the rest, itemised for that one layout. **So the habitation findings come from
the site after all**, not from the emailed brochure, and they are attributed to one vehicle
by construction.

**MTPLM is there, under a different name — found 11 September 2026.** The requester:
*"did you know that maximum authorised mass, MAM, is for all intents and purposes the
same as the MTPLM? I seem to remember it being the copy including MAM instead of
MTPLM."* Exactly right, and it is why the first search missed it. The popup's own table
reads:

```
Weights - Payloads
Maximum authorised mass (MAM) (kg) - base models   3500
Gross train mass (GTM) (kg)                        5500
```

**So nothing is blocked.** `MAM` is `mtplm_kilograms`, the same mapping `le_voyageur.py`
already makes from that brand's handbook — Groupe Pilote use MAM throughout, and Le
Voyageur's own legal page uses MTPLM and MAM for the one figure in adjacent paragraphs.

Two corrections to what the first attempt concluded, both mine:

* **The selector must be `button.btn-popup`, not `text=Technical information`.** The
  popup markup carries an `<h3>Technical information</h3>` *inside* itself, and a text
  selector matches that heading before the button. Clicking a heading does nothing and
  **does not time out**, so nothing was narrated and it looked like the panel simply had
  no weights. See the warning in [`README.md`](README.md#a-specification-behind-a-button-click_selector).
* **`Standard fittings` is server-rendered and needs no click at all.** It is a separate
  page section, not a tab of the popup — the earlier note that the click revealed it was
  wrong. The click's only job is filling `div.content-popup-techdata`, which starts empty
  and gains a full `<table>` of technical rows.

The figures land in the **rendered DOM**, so the adapter reads the table and never touches
the Airtable JSON. `fetch(url, click_selector="button.btn-popup", settle_ms=8000)` is the
call; the button's id is the layout's own product code (`P26I6900LHF1ST`), so the class is
the stable half of it.

Two traps remain in the *summary* strip above the button, which is not the popup table:

* **Its `Width 2,79 m` is the mirrors-open figure**, against a 2,32 m body. The Le
  Voyageur error in reverse, and the popup table is where the real widths are.
* **Its `Length 7,07 m` disagrees with the brochure's 6,99 m** for the G690GJ. Check both
  against the popup table before trusting either.

**Do not call Airtable directly.** The page source leaks a Pilote personal access token.
Its scope is unknown, and querying their database is a different act from reading their
website. The click is the legitimate route: it lets Pilote's own JavaScript make the call
exactly as it does for any visitor. Pilote should still be told about the leak; the
contact is Miles Storey at `m.storey@group-pilote.com`.

## What the popup table actually holds — measured 11 September 2026

Four layouts read, one per body type, with `click_selector="button.btn-popup"` and an
8-second settle. **The table is not the same shape on every vehicle**, and that is the
single most important thing about this source.

| | V540G (van) | G690GJ | P720U | A630G |
| --- | --- | --- | --- | --- |
| rows in the table | **23** | 57 | 57 | 57 |
| `Vehicle length (cm)` | 541 | 707 | 725 | 630 |
| `Vehicle interior width (cm)` | 205 | 230 | 230 | 220 |
| `Overall width with wing mirrors open (cm)` | 269 | 279 | 269 | 275 |
| `Vehicle height (cm)` | 267 | 285 | 285 | 288 |
| `Maximum authorised mass (MAM) (kg)` | 3500 | 3500 | 3500 | 3500 |
| `Load capacity in kg (on basic models)` | **730** | — | — | — |

### Payload is published, but in two different places

The requester, 11 September 2026: *"as long as you can derive MRO and payload, to be
honest, I couldn't find them."* They are both obtainable on every layout, which is why:

* **Panel vans** print `Load capacity in kg (on basic models)` in the popup table — 730 on
  the V540G — and no payload in the summary strip.
* **Coachbuilts** do the opposite: no load-capacity row in their 57-row table, but the
  summary strip above the button reads `Payload 485 kg` (the G690GJ).

So payload is read from the popup on vans and from the strip on coachbuilts, and
**`mro_kilograms` derives as MAM minus payload** on all 43. As at Joa, Murvi and Le
Voyageur that derivation is true by construction and is not a self-check.

The van's table also carries a row labelled literally **`undefined`, value 411**. A label
that failed to render is not a figure to record under a guess — leave it, and do not let
a positional read pick it up.

### The MAM row is named differently by body type

`Maximum authorised mass (MAM) (kg) **on basic** models` on the van against `... (kg) **-
base** models` on the three coachbuilts. Match on `Maximum authorised mass (MAM)` and stop
before the qualifier, or a third spelling will silently return nothing.

The coachbuilt table also carries four *chassis-variant* MAM rows — `"Light" light vehicle
chassis base`, `"Light" heavy vehicle`, `"Heavy" 4,25 T`, `"Heavy" 4,4 T/4,5 T` — of which
only the first has a value on a base model. **The base-models row is the one to take**, by
the settled base-vehicle rule; the variants are the paid uprates.

### Width is the field this source cannot answer

The popup gives the **interior** width and the **mirrors-open** width and nothing between
them. FMLV wants the body width, excluding mirrors — which is neither, and which the
Options brochure's layout tables do not print either. Do not record either figure: the
mirrors-open one overstates by 40-60 cm and the interior understates. This wants asking of
Pilote before the first run, alongside the length question below.

### The Atlas length disagreement resolves in the site's favour

The survey concluded from the brochure that the model code is not the length on Atlas, and
that the check would have to be scoped around it. **The popup says otherwise**: the A630G
is `Vehicle length (cm) 630`, exactly its code, against the brochure's 6,99 m. FMLV also
holds 6300. Two sources and the naming convention agree, so the brochure's Atlas row is
the outlier and **the model-code check needs no Atlas exemption after all**.

The same comparison the other way: the G690GJ's popup says 707 where the brochure says
6,99 m. The site wins by the settled rule, but the two disagree often enough on length
that it is worth raising with Pilote.

## The self-check, and where it breaks

The model code encodes the length in decimetres, as it does at Joa and Le Voyageur — and
on 39 of the 43 it holds to within 140 mm. **It fails completely on the four Atlas
layouts**, which are the Ford-based narrow low profiles:

| | A630G | A650D | A690G | A690GJ |
| --- | --- | --- | --- | --- |
| code implies | 6.30 m | 6.50 m | 6.90 m | 6.90 m |
| brochure says | 6.99 m | 7.04 m | 7.25 m | 7.25 m |
| out by | **690 mm** | **540 mm** | 350 mm | 350 mm |

**That conclusion is withdrawn — see "The Atlas length disagreement" above.** It rested on
the brochure, and the site's own popup gives the A630G as 630 cm, exactly its code. The
brochure's Atlas lengths are the outlier, not the naming convention, so **no Atlas
exemption is needed** and a single band applies to all 43. The table above is kept because
it is the evidence that the brochure and the site disagree, which still matters.

The usual `payload = MTPLM − MRO` is not available until the click lands. Once it is, the
brochure's legal page states the identity explicitly and gives the tolerance: *"the
available payload corresponds to the difference between the technically permissible maximum
laden mass and the mass in running order"*, within *"a factory tolerance of plus or minus
5%"*.

## Habitation: the brochure's fittings tables

Per-layout tables marked **`● Standard ○ Option - Unavailable`**, the same shape as Joa's
Technical Book and as Knaus's `s o -`. Each range has its own table, and the columns are
that range's layouts, so **the attribution is per layout** and the findings are safe to
record.

| range | heating | refrigeration |
| --- | --- | --- |
| Galaxy | 6,000 W Truma Combi D6E, standard on all 12 | compression, 150 L or 158 L |
| Pacific | 4,000 W Truma Combi 4 (gas) on P690D and P690GJ; 6,000 W Truma Combi 6 (gas) on the other seven | absorption, 141 L or 142 L |
| Atlas | 4,000 W Truma Combi 4 (gas), standard on all 4 | absorption, 142 L |
| Vega | 4,000 W Truma Combi D4, standard on all 6 | 95 L low compression on V540G; 90 L or slim 138 L compressor on the rest |

All four are Truma Combi, so **blown air on all 43**. The Alde wet system appears twice —
standard on the G781FC and G781FGJ Evidence, a £2,200 option elsewhere — so the two
Evidence 781s are the only wet-central vehicles in the range and must not inherit the
range's blown-air reading.

**The word "microwave" appears nowhere in either document**, across 43 layouts and every
fittings table. That is the itemised-table exception on firm footing, the same position as
Joa.

## What the first run should propose

Against FMLV's 51 live 2027 rows, and with Van Vega Standard folded into Pilote Van:

| | count | what |
| --- | --- | --- |
| `rrp_pounds` | **36** | see the price section below |
| `berths` | 6 | four Pacific 4 → 2; Atlas A690G 4 → 2; two Vega Evidence 2 → 3 |
| `mh_length_mm` | 6 | all four Atlas, and P690D in both offers |
| `mh_passenger_seats_inc_driver` | **0** | 4 on all 40 matched rows, agreed by FMLV and the brochure |
| renames | 2 | V540G and V630S, Van Vega Standard → Pilote Van |
| new | 3 | Galaxy Evidence G690GJ, Galaxy Expression G720FGJ, Pilote Van V630B |
| disappeared | 11 | see below |

**Seats agree on all forty.** The brochure prints `4+1 (1)` on the G740C, G740GJ, P740C and
P740GJ with the fifth belt priced at £1,240, so the standard figure is 4 by the settled
three-point-belt rule — and FMLV already holds 4 on all four. Nothing to propose, which is
a good sign for the reading rather than a gap in it.

### The prices have moved and FMLV has not caught up

Systematic, and too consistent to be anything but a 2027 uplift:

| range | FMLV against the 2027 list |
| --- | --- |
| Galaxy Expression | **−£300** on all 11 |
| Pacific Expression | **−£200** on all 9 |
| ATLAS | **−£200** on all 4 |
| Pacific Evidence | **−£600** on all 4 |
| Galaxy Evidence | −£4,200 on the two G740s; **exact** on both G781s |
| Pilote Van | **exact** on five of six |

Going the other way, four rows are **higher** in FMLV than the list, and they are the ones
to look at hardest:

| | FMLV | 2027 list |
| --- | --- | --- |
| Pilote Van V630S | £69,400 | £68,400 |
| Van Vega Evidence V600G | £75,700 | £73,700 |
| Van Vega Evidence V630J | £76,700 | £75,700 |
| Van Vega Evidence V633M | £83,900 | £81,900 |

There is a pattern in the Evidence vans worth a second look before accepting: FMLV's
V540G Evidence is priced at £73,700, which is exactly the list's **V600G** Evidence price,
and FMLV's V600G at £75,700 is exactly the list's **V630J**. The rows look shifted by one
layout against an older list, which would also explain the V540G Evidence that no longer
exists.

### The eleven with no 2027 page

Four are the limited editions and are expected: **Galaxy Selection** G720FC and G720FGJ,
**Pacific Selection** G720FC and G720FGJ. The brochure describes Sélection as a *"Spring
Edition... a limited-time and limited-quantity offer, once a year"*, so their absence from
a June price list is the offer working as designed, not a withdrawal.

The other seven look like genuine deletions and need the requester's eye: **Pacific
Expression** P620D, P650C, P650GJ, P690S and P720P; **Pacific Evidence** P620D; **Van Vega
Evidence** V540G. Six of the seven are Pacific, which is where the range shrank from 14
Expression layouts to 9.

## Traps

* **Atlas is a Ford.** Different chassis, different engine (2.0-litre 165 hp), different
  standard equipment, and a model code that is not the length. Do not let a Fiat-shaped
  assumption reach it.
* **The drop-down bed is not consistently attributed.** The Pacific Evidence layout table
  prints `Sleeping berths 4` on the P740FC and P740FGJ, but the same page's included-
  equipment list says the electric drop-down bed is *"optional on P740FC / FGJ"*. By the
  berth rule the standard figure is **2**, which is what FMLV already holds — so the table
  alone would have produced two wrong proposals. Read the layout table for berths, but
  check the option marks before trusting a figure that depends on a bed.
* **The Atlas option table contradicts its own layout table.** `LIT_PAVILLON` is marked ●
  standard on the A650D while the layout table shows its drop-down bed as `-` unavailable.
  Unresolved; FMLV's 2 berths matches the layout table and should stand until Pilote
  clarify.
* **`mh_length_mm` on the P690D differs by 30 mm** (6990 against the brochure's 7020) in
  both offers. Small, but it is the only non-Atlas length disagreement in 40.

## Still unverified

* **Everything behind the click** — MTPLM, MRO, payload, width and height, on all 43.
* **Whether the site ever publishes a price.** If it does, 43 constants disappear.
* **The seven non-Selection disappearances**, which need confirming with Pilote before any
  are archived.
* **Model year changeover.** The price list is dated 27 May 2026 and effective 1 June 2026,
  and the brochure 5 June 2026 — so Pilote move at the same time as Joa, months before the
  NEC-driven British brands. Not yet observed across a rollover.
