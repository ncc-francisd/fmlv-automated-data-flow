# RS Motorhomes — survey

**Surveyed 9 November 2026. No adapter written yet.**

RS Motorhomes build very large bespoke luxury coachbuilts in Westwoodside, Doncaster —
£300,000 to £400,000, four models, one product each. They are also a dealership trading as
RS Sales Nottingham, and about half the website is used stock, including other makers'
vehicles. That split matters more here than on any site surveyed so far: the brand pages
and the dealer pages sit under one domain and one footer disclaimer, and the disclaimer
itself says *"as these are used motorhomes"* on pages selling brand-new ones.

| | RS Motorhomes |
|---|---|
| JavaScript needed | No |
| Products | 4 |
| Fetches | 1 media listing + 3 PDFs + 1 HTML page |
| Price | **In the specification PDFs**, for three of four models |
| Berths / seats | Marketing ranges only, and they disagree between pages |
| Weights | **GVW only. No mass in running order and no payload, anywhere** |
| Dimensions | In the PDFs and the one HTML table |

## What the user brought to the survey

Francis gave the brand, the NCC supplier name (`RS Motorhomes`, the same string as the
FMLV manufacturer), the website, and an FMLV export of **the active range only** — four
rows, all filed under range `RS`. He said the range was "about 4 pre-built motorhomes".

Both held. The site's own `/luxury-motorhomes/` index lists exactly four models, and they
are the four in the export: Endeavour, Elysian, Evolution, Envoy. Nothing he gave was
superseded, and the export being active-only saved a wrong roster: `/rs-emotion/` still
resolves and would otherwise have looked like a fifth product (see below).

## The data is in PDFs the site never links to

Every model page is marketing. There is no specification table, no weight, no price, and
no dimension except in prose — *"a total length of 30ft (9.1 Metres)"*. Both documents a
buyer would want are behind an email form:

> **Download Price List** — Please provide your email below and we will send the price
> list direct to your inbox.

**The WordPress media library answers without the form.** This is the whole survey:

```
/wp-json/wp/v2/media?per_page=100&media_type=application
```

Twenty non-image files, and three of them are current specification documents:

| Title | Uploaded | URL |
|---|---|---|
| RS Endeavour Specification Document | 23 Sep 2026 | `/wp-content/uploads/2026/02/RS-Endeavour-Specification-Document.pdf` |
| RS Elysian Specification Document | 28 Sep 2026 | `/wp-content/uploads/2026/02/RS-Elysian-Specification-Document.pdf` |
| RS Envoy Specification Document | 28 Sep 2026 | `/wp-content/uploads/2026/02/RS-Envoy-Specification-Document.pdf` |

**Discover them through the endpoint, never by building the path.** The paths lie about
dates in both directions: the 2027 documents sit under `/2026/02/`, and the Envoy's *2026*
brochure sits under `/2024/01/`. The upload date in the listing is reliable; the folder in
the URL is not.

These are real text PDFs, not images, and they carry what FMLV needs:

```
Base Vehicle Iveco Daily 72-210
Transmission 6-speed manual
Overall Length 9,100mm
Overall Width 2,400mm
Overall Height 3,400mm
Gross Vehicle Weight 7,200kg
Gross Train Weight 10,500kg
Towing Capacity 3,500kg (3,300kg if Hi-Matic automatic gearbox is selected)
```

The glossy sitting next to them is the near-miss: `RS-Envoy-Brochure-2026.pdf` (11 MB,
re-uploaded 9 November 2026) extracts as letter-spaced display type —
`£ 3 9 9 , 9 9 5  i n c l u d i n g  V A T` — and carries no specification table at all.
It agrees on the price and is useless for everything else.

## The Evolution has no current document

Its only source is an HTML table at `/rs-evolution-specifications/`, and that page is of
2022–23 vintage: it gives the base vehicle as **DAF LF 260**, matching
`RS-Evolution-DAF-LF260-2023.pdf` from 2022, while the model page's prose says the
Evolution *"can be based on a 10 ton DAF or Mercedes chassis"*.

The equivalent pages for the other three models **do not exist**, including
`/rs-elysian-specifications/`, which the Elysian page still links to and which returns 404.
So the HTML route covers exactly the one model the PDF route does not — complementary by
accident, not by design, and a reissue of either could end that at any time.

## What a parser has to survive

**Two rows share one label.** On the Evolution page, verbatim from the markup:

```
Gross Vehicle Weight – 7200KG
Gross Vehicle Weight – 10.5 Tonnes
```

`Engine Capacity – 4500cc` appears twice as well. A label-keyed parser would take one of
the two masses and be equally confident either way, and the two differ by 3.3 tonnes. The
prose points at 10.5 tonnes, the other Iveco models print 7200kg, and FMLV's row has used
**both** — 7200 as the mass in running order and 10500 as the MTPLM. Nothing published
settles it, so an adapter must refuse the field and say why, not choose.

**The Envoy's cover contradicts its own table.** The cover reads `IVECO DAILY 72-210`; the
chassis table five lines later reads `Base Vehicle DAF XB – 16000KG`, with a 200-litre
fuel tank, hydraulic cab tilt and a differential lock. The table is the vehicle and the
cover is a copy-paste left over from the Endeavour. Read the table.

**A mass may not be in kilogrammes.** The Envoy prints `Gross Vehicle Weight 16 ton` and
`Gross Train Weight 12-ton towing capacity` — the second is not a train weight at all.

**Endeavour and Elysian are indistinguishable by their figures.** Same base vehicle, same
9,100 × 2,400 × 3,400, same 7,200kg and 10,500kg, same towing capacity, same options list
down to the £8,523 awning. They differ on price and on interior. Only the document
identifies them, which is the same rule the Auto-Trail adapter lives by for its two
Expeditions.

**Floorplan drawings are mislabelled.** The Evolution page's "Interior layout options"
carousel serves nine `RS-Elysian-interior-layout-*.svg` files, all with empty `alt` text.
They are the Elysian's drawings on the Evolution's page.

## What this means against FMLV's current four rows

Nothing here has been proposed to anyone; this is what the sources say against what the
export holds today.

| | Document says | FMLV holds |
|---|---|---|
| Endeavour | Iveco Daily 72-210, 9100×2400×3400, GVW 7200, **£299,995** | IVECO, 9100×2400×3400, MTPLM 7200, **£259,000** |
| Elysian | Iveco Daily 72-210, 9100×2400×**3400**, GVW 7200, **£335,000** | IVECO, 9100×2400×**3600**, MTPLM 7200, **£290,000** |
| Envoy | **DAF XB 16000KG**, **10005**×2600×3700, GVW **16 ton**, **£399,995** | **Mercedes**, **9448**×2600×3700, MTPLM **7200**, **£380,000** |
| Evolution | DAF LF 260, 9448×2600×3700, GVW 7200 **or** 10.5t, no price | DAF, 9448×2600×3700, MTPLM 10500, £320,000 |

Two further corrections apply to all four:

- **Heating.** Every model specifies a *"Full Alde diesel-powered water radiator heating
  system throughout"*. That is wet central heating; FMLV records blown air on all four.
- **Seats.** Each Iveco model gives a `Single passenger seat` with *"rear seatbelts
  available depending on layout"* — two travel seats as built, more only as an option.
  FMLV has the Envoy and the Evolution at four.

## There is no self-check, and that is the headline risk

**No mass in running order and no payload is published for any model**, so the payload
arithmetic that checks every other adapter's parse does not exist here. This is the first
manufacturer surveyed with none, and it means a misread mass would reach a reviewer
looking exactly as plausible as a correct one.

Three weaker checks are available and all three should be used:

1. **The price is printed twice** in each PDF — once on the cover as `From £299,995 inc.
   VAT` and once in the body as `£299,995`. Two printings of one number; if they disagree,
   record no price.
2. **Gross train weight minus gross vehicle weight equals the stated towing capacity**, on
   the Iveco pair: 10,500 − 7,200 = 3,300, which is the Hi-Matic towing figure exactly.
   The quoted 3,500kg manual figure does not reconcile, so the train weight is the
   automatic's.
3. **The cover's base vehicle against the chassis table's.** This one already fires, on the
   Envoy, which is the argument for keeping it.

## Other things worth knowing

- **Berths are marketing and the marketing disagrees with itself.** The Endeavour page says
  *"Available in 2 berth up to 6 berth"*, the index page says *"up to 7 berth"*, its 2027
  PDF says *"Comfortably accommodates up to 6 people"*, and the Evolution's page says *"up
  to 8"*. Under the settled lower-figure rule all four would be 2 against FMLV's 4. That is
  a judgement about the vehicles, not about the parse.
- **An automatic is an option, so `automatic_available` is Yes.** The Endeavour page offers
  a *"New 8 speed, Hi Matic (fully automatic) gearbox"*, and the spec PDFs price the
  Hi-Matic's effect on towing capacity. The Envoy's base transmission is already automatic.
  FMLV already carries an automatic price for the Endeavour and the Elysian.
- **`/rs-emotion/` is an orphan, not a fifth model.** It resolves, describes an 18-tonne
  Mercedes-Benz Antos at 12.1 metres with four slide-outs, and is absent from both the nav
  and the `/luxury-motorhomes/` index. It also throws a visible PHP warning —
  *"Attempt to read property \"post_title\" on null"* — which is what a page left behind
  looks like. It is not in the active export either. Watch it rather than collect it.
- **Never read `/listings/` or `/preowned-motorhomes/`.** They are the dealership's used
  stock and include Bailey, Carado, Dethleffs, Swift and Autocruise vehicles alongside
  used RS ones. A used `rs-endeavour-4` listing is one unit's plate, not the model's spec.
- **These are bespoke builds.** Every document says *"Bespoke luxury. Built around you"* and
  *"Choice of layout configurations"*. One FMLV row per model is a base specification, not
  a layout, which is how the export already treats them.
