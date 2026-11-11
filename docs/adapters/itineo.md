# ITINEO — survey and adapter

**Surveyed and built 11 November 2026.** The adapter is `src/adapters/itineo.py`.

**NCC id 128.**

Part of **Groupe Rapido** (Mayenne, France), alongside Rapido (id 129, adapter built),
Dreamer (id 127, to survey next), Campéréve and Fleurette. Ten coachbuilt motorhomes on
Peugeot Boxer / Fiat Ducato. No campervans and **no caravans** — the registry row is
`categories=motorhome`.

| | ITINEO |
|---|---|
| JavaScript needed | **Yes**, for the Calaméo reader only — the site itself is plain HTML |
| Products | **10**, matching the ten model pages exactly |
| Price | **None published anywhere.** No model page, no guide, no catalogue |
| Weights | **MIRO and payload for all ten**, in one table |
| Dimensions | All three, and the width is published **excluding wing mirrors** |
| Berths / seats | Published **with the options already split out** |
| Self-check | `MIRO + payload == GVW`, holds on all ten |

## The spelling, which is deliberate and not ours to tidy

The NCC manufacturer list spells id 128 **`ITINEO`, in capitals**, in both `Name` and
`DisplayName`. The requester notes there is no branding reason for it — the site uses
`ITINEO` in its logo and `Itineo` in prose.

**`fmlv_manufacturer` is unverified** and is the one thing blocking a build. It must equal
the FMLV export's `manufacturer` column byte for byte, and no export has been downloaded.
The row carries `ITINEO` on the strength of the NCC list alone. Getting this wrong means
the run finds an empty baseline and proposes all ten products as new, so it is worth the
one check — and the capitals must not be "tidied" in either direction without it.

## There are no prices, and that is settled rather than a gap

The requester: *"the website never shows the pricing, so unfortunately it's unlikely that
we'll get prices for each of these models, and we don't carry those prices at the moment."*
The survey agrees — no price on any model page, none in the technical guide, none in the
catalogue. **Exactly Rapido's position**, and the adapter should emit no price at all, so
that the occasional dealer-sourced figure already sitting on an FMLV row is never blanked.

## The source is a Calaméo technical guide, and Rapido's parser already reads it

This is the survey's main finding. `/motorhome_doc.php` carries two Calaméo books:

| | book | thumbnail |
|---|---|---|
| Catalogue | `007692732a7abe049655f` | `collection-2027.jpg` |
| **Specifications** | **`007692732cc45a1d22052`** | **`cahier-technique-2027.jpg`** |

**Both sit on the same Calaméo publisher account as Rapido's** — every book code begins
`00769273`. The group uses one document generator, which is the Pilote / Joa / Le Voyageur
arrangement again: one column reader serves several brands.

**Verified by running it, not by assuming it.** `rapido.page_cells` splits Itineo's pages
on `dx` unchanged, first try:

```
Overall length                          6.61 | 6.61 | 6.99 | 7.42 | 7.42 | 7.42 | 5.99 | 6.99 …
Overall width (excluding wing mirrors)  2.19 | 2.19 | 2.34 | 2.34 | 2.34 | 2.34 | 2.32 …
Mass in Running Order (MIRO) (kg)       2900 | 2935 | 2995 | 3070 | 3085 | 3075 | 2780 | 2975 | 3070 | 3125
Payload (kg)                             600 |  565 |  505 |  430 |  415 |  425 |  720 |  525 |  430 |  375
```

Eight pages against Rapido's thirty-two, and ten columns in one table rather than a column
block per series.

Three things carry over from Rapido unchanged, and one does not:

* The **`dx` cell splitting**, the **token-signed asset capture** through `BrowserFetcher`,
  and **`reconciles`** all work as they are.
* **`technical_guide_url` does not find this link.** It keys on a `TECHNICAL GUIDE`
  heading; Itineo's anchor is `id="itineo-dl-gt-gbr-en"` beside the words *"Download the
  specifications"*. Discovery needs its own rule.

**Rediscover the book each run.** The code is opaque and will change for 2028.

## The self-check is the best one yet

`MIRO + payload == GVW`, and every one of the ten pairs sums to **exactly 3500 kg**:

| CJ660 | CM660 | SBD700 | JC740 | MC740 | SB740 | PF600 | PJ700 | PM740 | PS740 |
|---|---|---|---|---|---|---|---|---|---|
| 2900+600 | 2935+565 | 2995+505 | 3070+430 | 3085+415 | 3075+425 | 2780+720 | 2975+525 | 3070+430 | 3125+375 |

`rapido.reconciles(miro, payload, gross_weights)` already implements it.

**The GVW is a choice, not a figure.** Every model lists `LIGHT: 3.5 T` *and*
`HEAVY: 4.4 T`. Take the light one as the base vehicle — which is what the arithmetic
confirms, since the payloads are computed against 3,500 kg.

## Berths and seats come with the options already split out

Unusually good, and worth not throwing away. Each model page gives the standard figure and
the options **separately**, twice over:

* the headline block — `Number of possible sleeping spaces  2(+1+1 opt)`; and
* the prose — *"Up to 4 berths (including 2 as an option): French bed … **as standard**;
  inbuilt electric single drop-down bed … **optional**"*.

Two independent statements of the same standard figure on the same page, so they check each
other. Take the leading number. Seats are written the same way — `4 (m) (+1 opt)` — where
`(m)` is a footnote about registered seats varying with the chassis.

## The roster

Ten, matching the ten `motorhome_<code>.php` pages one for one:

| series | models |
|---|---|
| COZI | CJ660, CM660 |
| FAMILI | SBD700, JC740, MC740, SB740 |
| COMPACT | PF600, PJ700, PM740, PS740 |

## What is unverified

1. **`fmlv_manufacturer` and `ncc_supplier_name`** — both `ITINEO` from the NCC list, and
   neither checked against an export or the supplier dropdown. This blocks a build.
2. **What FMLV currently holds** — no export has been downloaded, so the product count, the
   naming of range versus model, and which rows carry a dealer price are all unknown.

## Built, 11 November 2026

Run #229, against the live site and the live guide: **ten products collected, every one
reconciling to exactly 3,500 kg**, against a baseline of nine.

```
classified  8 changed, 0 unchanged, 2 new, 1 disappeared
verified    48 fields checked and unchanged
findings     5 habitation readings
```

### Three things the first run turned up

**`PC640` has gone from the site.** It is live in FMLV (7088, COZI, £58,800) and has no
model page any more, so it comes through as the run's one disappearance. Nothing is
proposed for it — deactivating is a decision for a person.

**`JC740` is a relisting, not a new model.** FMLV holds it at **7085**, archived and
inactive, and the baseline drops archived rows — so the adapter proposes it as new. It is
not: Itineo have put it back. The row to reactivate is 7085, matched on the mass (FMLV
3,065 kg against the guide's 3,070 kg for the 2027 collection). Creating a second JC740
would leave two rows for one vehicle.

**`PS740` is genuinely new**, and is not a renamed `PS700`. FMLV's PS700 (8252) is archived
at 2,935 kg; the guide gives PS740 3,070 kg, and the two are a different length.

### The column order, and the guard that makes it safe

The guide's ten model codes are staggered across two lines and some share one `<text>`
element, so the page's own `(y, x)` reading order interleaves them. Sorting the
**elements** by x and flattening each one's cells gives the true order:

```
CM660, CJ660, SBD700, JC740, MC740, SB740, PF600, PJ700, PS740, PM740
```

**Nothing about that is self-evident, and a wrong order would not look wrong** — every
figure would still be plausible for an Itineo. So `_check_alignment` compares the guide's
height column against **each model page's own published height**, and refuses the product
if they disagree. All ten agree.

### Where Rapido's code was reused, and where it was not

| | |
|---|---|
| `rapido.page_cells`, `_split_element`, `_svg_of` | reused unchanged |
| `rapido._capture_pages` | reused unchanged |
| `rapido.reconciles` | reused unchanged |
| `rapido.technical_guide_url` | **does not match** — keys on a `TECHNICAL GUIDE` heading |
| `rapido.heading_key` | **does not transfer** — anchors on `VEHICLE DIMENSIONS`, and this guide says `VEHICULE DIMENSIONS` |

### One length cannot be read at all

Column nine's overall length extracts as `.` — private-use glyphs, the
font-substitution problem the Rapido survey found in prose, here landing in a number. It
converts to `None` rather than to a plausible figure, so **PS740 is recorded with no
length**. Every other value on that row reads cleanly.

### What is not emitted, and why

* **No price.** Itineo publish none anywhere. FMLV's nine live rows carry dealer-sourced
  figures, and a blank would propose deleting them.
* **No MTPLM.** The guide gives the gross weight as a *choice* — `LIGHT: 3.5 T` and
  `HEAVY: 4.4 T` — not as this model's own figure. It is used for the arithmetic and
  narrated, never proposed.
