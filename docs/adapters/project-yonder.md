# Project Yonder

Hastings converter of 4x4 Mercedes-Benz Sprinter campervans. Three products, none of them
in FMLV. Adapter built 12 November 2026; `src/adapters/project_yonder.py`.

Francis raised them on 12 November 2026: they exhibit at the NCC show in February, they
have exhibited before, and they have never been on Find My Leisure Vehicle. His own read of
the site was that it "doesn't seem to have much in the way of specifications", and that the
alternative was asking them for brochures and price lists. Both halves of that turned out
to be true at once — see **What the site does and does not publish**.

## What this is

| | |
|---|---|
| Company | Project Yonder Ltd, Unit 8, Platform Business Centre, Haywood Way, Hastings TN35 4FB |
| Contact | `hello@projectyonder.co.uk`, 01424 271121 |
| Site | <https://www.projectyonder.co.uk/> |
| Products | 3 — Nomad (MWB), Freedom 4X (LWB), Freedom 4X Utility (LWB) |
| Base vehicle | Mercedes-Benz Sprinter, AWD and RWD, bought new from the factory |
| Price band | £192,625 – £194,775 |
| FMLV rows today | **none** |
| NCC id | **none — 9004 is locally assigned** |

They are not in `resources/manufacturers-full-list.csv`, so there is no NCC
`manufacturer_id` and no FMLV export to match `fmlv_manufacturer` against. `9004` follows
the convention already used for Fleurette (9001/9002) and Globe-Traveller (9003).
**Both `manufacturer_id` and `ncc_supplier_name` need confirming before the first upload.**
This is the first adapter written for a manufacturer with no baseline at all: the usual
safety net, where a wrong value shows up as a proposed change against a figure FMLV already
holds, does not exist here. Every figure this adapter emits creates a row.

## What the site does and does not publish

It publishes more than it appears to and less than an adapter wants.

**More**, because the site is Remix rendered over a Storyblok CMS and inlines its entire
content tree into every page as `window.__remixContext`. What looks like a styled graphic
is a typed record:

```json
{"big_text": "4.1T", "small_text": "GVW", "component": "callout_spec"}
{"price": "£194,775*", "title": "AWD From", "component": "pricing_block"}
```

No browser, no OCR, no PDF — there is no PDF anywhere on the site to want one.

**And the FAQ page is a data source whose answers do not render.** They sit in collapsed
accordions supplied from the payload and written into the DOM only on a click, so anything
reading the rendered page finds fifteen questions and no answers. That page is the **only
place on the whole site where a width or a height is published**:

> *"Our MWB campervan is 6m long x 2.1m wide x 2.9m high. Our LWB campervan is 7m long x
> 2.1m wide x 2.9m high."*

**Less**, because of what is simply not there:

| Field | Published? |
|---|---|
| Price, berths, belts, length, GVW, base vehicle, gearbox | yes, per model |
| Width, height | FAQ only — one pair for all three models |
| Heating, refrigeration, washroom | **Freedom 4X page only** |
| **Mass in running order** | **nowhere, for anything** |
| **Payload** | **nowhere, for anything** |
| Floorplan | nowhere, for anything |
| Sleeping / kitchen / lounge / bathroom position | nowhere |

There is no models index page. The homepage's three cards are the roster, and the fourth
card is the Gear Shop — told apart not by its name but because its link is an external URL
where a model card's is a Storyblok story.

## The self-check

**There is no mass arithmetic.** `payload == MTPLM - MRO` guards most adapters in this
repo; Project Yonder publish one gross weight per model and nothing at all to divide it
with, so that check cannot exist here. This was flagged before the build as the thing that
changes the risk profile of the whole adapter, and it remains true.

What exists instead is the **length, held by two pages that are edited months apart**: the
model page's `6.0M` tile against the FAQ's "Our MWB campervan is 6m long". `_reconciles`
requires them to agree, and a product whose two sources disagree is dropped.

That check is weaker than mass arithmetic but it is not decorative, because it guards the
specific thing that would otherwise go wrong silently: the width and height are taken from
an FAQ row **chosen by wheelbase**, and nothing else proves the row belongs to this
vehicle. If the LWB row were read for the Nomad, the length is what would catch it.

The pages were published 22 April 2026 (Freedom 4X), 27 July 2026 (FAQ) and 7 September
2026 (Nomad and Utility), so their agreeing is not a tautology.

## Nomad is a rename, not a new model

The `/nomad` page says so itself, in four places:

* its SEO title is still `Freedom 4X - The Ultimate AWD Motorhome`;
* its hero image is `20250205_py_freedom-4x_mwb_417_web_v1.jpg`;
* its body copy opens *"Freedom knows no limits"*;
* and the FAQ, written in July, still calls the 140" van `Freedom 4X 140" (MWB)`.

Only the story name, the slug and the navigation say `NOMAD`. Project Yonder renamed the
model around 7 September 2026 and have not finished renaming the page. Narrated every run.

Since nothing of theirs is in FMLV, the rename costs nothing this time. It is recorded
because it is the clearest evidence available about how this company maintains its site,
and because the FAQ's stale naming is what makes its *other* stale figures legible.

## Two contradictions, both settled by one rule

**The model page beats the standing page**, because only the model page is maintained —
Francis, 13 November 2026, now a cross-manufacturer rule in `docs/adapters/README.md`.
Both conflicts below fall to it, and both are still narrated on every run as *applied*
rather than as questions, so that a new disagreement would surface the same way.

**The gross weight.** Every model page tile says `4.1T`. The FAQ says *"Our vans have a
Gross Vehicle Weight of 4.4T which means you require a C1 licence to drive them."* The tile
is recorded.

This one had to be settled rather than left open, because it is what turns a mass in
running order into a payload. Asking Project Yonder for the payload as well as the MIRO
would have been asking for a figure we can calculate — and the whole point of the request
made to them on 13 November 2026 is that it is small enough to answer quickly.

**The price.** The model pages say £192,625 (Nomad) and £194,775 (both LWB vans). The FAQ
still says:

> *Starting price Freedom 4X 140" (MWB): RWD model from £152,775 OTR / AWD model from
> £164,775 OTR. Starting price Freedom 4X 170" (LWB): RWD model from £157,895 OTR / AWD
> model from £169,725 OTR.*

£25,000–£28,000 lower, labelled `OTR` where the model pages are not, and pricing **RWD
variants that have no model page at all**. The model-page figure is recorded, as the
manufacturer's own headline price and under the same rule. Whether the range is three
vehicles or six was not asked, deliberately — see below.

**The rename is what proves the rule's direction** rather than merely asserting it.
Project Yonder renamed the 140" van in September and the FAQ still used the old name in
November, so the FAQ's staleness is demonstrated rather than assumed. Once one figure on a
page is known stale, the rest are suspect by the same mechanism.

## The prose trap

Project Yonder have no specification document. They have paragraphs, and they put the
standard fitting and the paid upgrade in the same sentence:

> *"...a two ring induction hob plus a 90L fridge freezer & a variety of additional cooking
> options such as air fryer, microwave & coffee machine..."*

> *"Optional belted passenger seats, cosy kids bunk beds or even an elevating pop-top roof
> will make your little ones dreams a reality."*

The shared `habitation._OPTION` filter cannot see either, because it keys on a price or on
`option:` with a colon — which is how a *spec sheet* writes an extra. Read whole, the first
sentence asserts a microwave in every van and the second asserts fixed bunks in a van that
has none. Both were observed before the filter was written.

`_standard_prose` truncates every sentence at the first word that turns it into an offer.
What precedes the marker is a fitting; what follows is a catalogue.

## Decisions

**Range names are the prose spelling, not the navigation's.** The nav styles everything in
capitals and the CMS story names copy that; Project Yonder's own writing does not. The
third vehicle is `UTILITY` in the nav and `Freedom 4X Utility` in their blog post and in
its slug, and the short form would file a Freedom 4X variant as an unrelated range.

**The model is the wheelbase**, following `landseer`, so that a product is not filed as
`Nomad Nomad` — the doubling Nova forces when a product has one name, which Francis then
unpicks by hand. The inch figure stays out of the value and goes in the provenance: a bare
double-quote in a CSV cell is a needless hazard for one digit.

**Berths and belts are both recorded as 2** from a published `2-4`. Berths follow the
settled lower-figure rule. The belts land on the same number for a different reason:
Project Yonder's own feature list calls the extra belted seats `Optional`, so two is the
Sprinter's cab pair. **They never say what kind of belt the optional seats carry**, and
only three-point belts count as travel seats.

**Body type is campervan high top** on all three — a fixed-roof panel-van conversion at
2,900mm, clearing the settled 2,300mm threshold by 600mm. The Caravan and Motorhome Club
awarded the Freedom 4X in the category *"Van Conversions with a fixed roof over 6 metres"*,
so the reading does not depend on the FAQ's rounded height being exactly right. The pop-top
roof they mention is an option, so it does not make this an elevating-roof campervan.

**Habitation findings come from the Freedom 4X page only.** It names a Truma D6 E and a 90L
fridge freezer; the Nomad and Utility pages carry no equipment prose at all, and the
homepage's range-wide *"gas-free habitation as standard"* panel names no appliance.
Asserting one model's kit on its siblings is the `robeta` mistake exactly.

**Nothing is emitted for mass in running order or payload**, because nothing is published.
Unlike every other adapter, there is no FMLV figure being protected here — there is simply
nothing, and a number this adapter invented would be a number nobody could ever catch.

## A shared-vocabulary gap this source exposed

`habitation._WARM_AIR` already matched `combi` for the Truma Combi, which Francis settled
on 11 November 2026 for ITINEO. Project Yonder write **"the extremely capable Truma D6 E
makes light work of your heating & hot water"** — the Combi D 6 E, named without the word
`Combi`. Truma's own operating manual describes it as a warm-air heater with a 10-litre
water boiler built in.

Added to the shared pattern as the make plus a D-number, because that designation exists
only in Truma's warm-air lines; a bare `truma` would also claim their fridges, fans and
movers. `varioheat` went in beside it for the same reason.

## What was asked of Project Yonder, and what was not

**Asked, 13 November 2026 — two things only:**

1. **Mass in running order, for each of the three models.** The one figure no page on the
   site could ever supply.
2. A **floorplan** for each model, which would settle the sleeping, kitchen, lounge and
   washroom positions in one go.

**Deliberately not asked**, on Francis's instruction: *"the less that it looks like we need,
the more likely they're going to respond quickly."*

| Not asked | Why |
|---|---|
| Payload | It is the published gross weight less the MIRO. Asking for a figure we can calculate makes the request look twice as big as it is. |
| Which gross weight is right | Settled by the model-page rule. |
| The current price list, and whether the RWD models are still sold | Settled by the same rule. |
| Dimensions in millimetres | Everything published is rounded to 0.1m. Worth having, not worth the ask. |
| Whether the optional belted seats are three-point | Only two are recorded as standard either way. |
| Whether the Nomad is the renamed MWB Freedom 4X | Their own FAQ already answers it. |

Everything in the right-hand column is still narrated on every run, so none of it is lost —
it is deprioritised, not forgotten. If Project Yonder answer quickly and are willing, that
list is the second conversation.

## Before the first upload

Project Yonder are the second brand genuinely new to FMLV, after Atom. The bootstrap order
is in `docs/adapters/README.md` under *"A brand new to FMLV needs three things created, not
two"*, and all three apply:

1. **Confirm `manufacturer_id`.** `9004` is locally assigned. If the NCC have allocated one,
   it replaces this before anything is uploaded.
2. **Run against `fmlv empty-baseline "Project Yonder"`** until the first upload exists —
   already done locally, and needed again on the VM, which has its own export store. The
   run then warns that every product was classified as new, which is true rather than a
   fault.
3. **Create the supplier record** matching `ncc_supplier_name`. Uploading the products does
   not create it, and until it exists `fetch-export` has nothing to select.

**Set the model year at upload.** The adapter emits none, and a blank year drops the row out
of every future baseline. **Do not upload twice** before a real export exists: every run
still diffs against the empty baseline, so a second upload duplicates all three.

First run, #248 on 12 November 2026: 3 scraped, 3 new, 42 changes proposed, 3 habitation
findings, nothing dropped.

## Open, and watched every run

* A **fourth campervan card** appearing on the homepage, which is the only index this site
  has. The run narrates any card slug `project_yonder.MODELS` does not know.
* The **`/nomad` page's SEO title**, which will stop saying `Freedom 4X` when the rename is
  finished.
* The **FAQ's price and gross weight answers**, which are both stale today.
* Whether `UTILITY` settles as a range of its own or stays a Freedom 4X variant.
