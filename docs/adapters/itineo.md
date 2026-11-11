# ITINEO — survey, 11 November 2026

**NCC id 128.** **Stage 1 only. No adapter has been written.**

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
