"""Logging in to the NCC website and downloading one manufacturer's current export.

DESIGN.md §6.2: this is the one piece of NCC-site automation the pipeline does —
Playwright logs in and downloads the current export for one manufacturer, which
becomes the baseline for a run against that manufacturer. The *generated* upload CSV
(`output/`) is still uploaded by hand; that human gate on the only irreversible step is
unaffected by this module.

Surveyed against the real site 2026-08-06 (TODO.md's "For Ben" note is now resolved).
The login page is a plain form, but there is no "download the whole export" button —
the export is generated **per manufacturer** via Nova's (the NCC's Laravel admin
panel) resource actions:

    /nova/resources/products → the "..." actions dropdown → "Export Products by
    Supplier" → pick a supplier from the dropdown, untick "Only Active and Most Recent
    Year Products" (we want everything to diff against, not just the live subset) →
    "Run Action" → a `.zip` download containing `motorhome-campervans.xlsx` and
    `touring-caravans.xlsx`.

The supplier dropdown's labels don't always match `fmlv_manufacturer` (e.g. "Adria
Mobil" vs "Adria Caravans & Motorhomes") — that's why the registry carries a separate
`ncc_supplier_name` column (`registry/models.py`) rather than reusing `fmlv_manufacturer`
here.
"""

from __future__ import annotations

import os
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

#: DESIGN.md §8: "Anthropic API key and NCC credentials via environment, never
#: committed." These are the two env vars that carry the NCC login.
CREDENTIALS_EMAIL_ENV = "FMLV_NOVA_LOGIN_EMAIL"
CREDENTIALS_PASSWORD_ENV = "FMLV_NOVA_LOGIN_PASSWORD"


class NccCredentialsError(RuntimeError):
    """Raised when the NCC login credentials aren't available in the environment."""


class NccExportError(RuntimeError):
    """Raised when the downloaded export doesn't contain the file we expect.

    Most likely cause: the supplier dropdown label in `ncc_supplier_name` no longer
    matches what the site shows, or the zip's internal filename has changed.
    """


@dataclass(frozen=True)
class NccCredentials:
    """NCC site login. Always sourced from the environment — see `from_env`."""

    email: str
    password: str

    @classmethod
    def from_env(cls, *, env: dict[str, str] | None = None) -> NccCredentials:
        """Read the login from `FMLV_NOVA_LOGIN_EMAIL`/`FMLV_NOVA_LOGIN_PASSWORD`.

        Raises `NccCredentialsError` rather than proceeding with a blank credential —
        a login attempt with an empty password is a confusing failure to debug from
        the site's side, and there's nothing useful to do with a partial login.
        """
        source = env if env is not None else os.environ
        email = source.get(CREDENTIALS_EMAIL_ENV)
        password = source.get(CREDENTIALS_PASSWORD_ENV)
        if not email or not password:
            msg = (
                f"{CREDENTIALS_EMAIL_ENV} and {CREDENTIALS_PASSWORD_ENV} must both be "
                "set in the environment to log in to the NCC site"
            )
            raise NccCredentialsError(msg)
        return cls(email=email, password=password)


@dataclass(frozen=True)
class NccSiteConfig:
    """Where the NCC login/export pages are and how to drive them.

    Surveyed against the real site 2026-08-06 — these are the actual URLs/selectors,
    not placeholders (unlike the pre-survey version of this module). Still overridable
    per call, both so tests can point at local fixtures and so a future site redesign
    is a config change here rather than a rewrite.
    """

    login_url: str = "https://findmyleisurevehicle.co.uk/nova/login"
    products_url: str = "https://findmyleisurevehicle.co.uk/nova/resources/products"
    email_selector: str = 'input[type="email"], input[name="email"]'
    password_selector: str = 'input[type="password"], input[name="password"]'
    login_submit_selector: str = 'button[type="submit"]'
    actions_dropdown_selector: str = 'button[dusk="index-standalone-action-dropdown"]'
    export_by_supplier_selector: str = 'text="Export Products by Supplier"'
    supplier_select_selector: str = "select#exhibitor"
    #: The "Only Active and Most Recent Year Products" toggle. We want it *off* — the
    #: baseline for a diff needs everything currently in FMLV, not just the live subset.
    only_active_toggle_selector: str = '[dusk="only_active_products-default-boolean-field"]'
    run_action_selector: str = '[dusk="confirm-action-button"]'
    #: Name of the motorhome/campervan file inside the downloaded zip.
    motorhome_export_filename: str = "motorhome-campervans.xlsx"
    #: Name of the touring-caravan file inside the same zip. Saved alongside the
    #: motorhome one rather than discarded: one export action returns both, so keeping
    #: the second costs nothing and is the baseline the caravan schema needs.
    caravan_export_filename: str = "touring-caravans.xlsx"


class SupplierNotListed(RuntimeError):
    """The NCC's supplier drop-down has no such supplier.

    Its own name, because it is not a fault to be retried: the supplier genuinely is not
    there, and no amount of waiting will add it.
    """


def _select_supplier(
    page,
    selector: str,
    supplier_name: str,
    on_progress: Callable[[str], None] = lambda message: None,
) -> None:
    """Pick one supplier from the NCC export drop-down, or say plainly that it is absent.

    **Playwright's own failure here is 30 seconds of silence and then a locator dump.**
    Asked for a supplier the list does not contain, `select_option` retries until it times
    out and reports *"did not find some options"* beside the `<select>`'s markup — which
    names neither the supplier nor the reason, and reads like the site is broken.

    It is not broken. A manufacturer FMLV holds no products for has no supplier to export,
    which is the state every brand new to FMLV starts in: Atom failed exactly this way on
    16 September 2026, from the review app's trigger, because the trigger refreshes the
    export before diffing and `Atom` was not yet an NCC supplier.

    So the options are read first and a missing one fails immediately, naming the supplier
    and what to do instead. The near-misses are listed because the likelier cause, once a
    manufacturer does exist, is `ncc_supplier_name` in the registry not matching the site's
    own spelling.
    """
    options = [
        (text or "").strip()
        for text in page.locator(f"{selector} option").all_text_contents()
    ]
    if supplier_name in options:
        page.select_option(selector, label=supplier_name)
        return

    lowered = supplier_name.casefold()

    # **Case alone is not worth failing a run over, but it is worth saying.** The NCC list
    # spells Atom `ATOM`, and `Atom` in the registry matched nothing — three triggered runs
    # died on it on 16 September 2026 before a screenshot of the drop-down settled it. A
    # scheduled sweep would have died the same way, in the middle of the night, so the
    # nearest unambiguous match is used and the registry is told to catch up.
    same_but_for_case = [option for option in options if option.casefold() == lowered]
    if len(same_but_for_case) == 1:
        on_progress(
            f"WARNING: the NCC list spells this supplier {same_but_for_case[0]!r} and the "
            f"registry says {supplier_name!r}. Using the site's spelling — correct "
            f"ncc_supplier_name so this stops being a guess"
        )
        page.select_option(selector, label=same_but_for_case[0])
        return

    near = [option for option in options if lowered in option.casefold()] or [
        option for option in options if option.casefold()[:4] == lowered[:4]
    ]
    suggestion = (
        f" The closest the list offers: {', '.join(repr(option) for option in near[:5])}."
        if near
        else ""
    )
    msg = (
        f"{supplier_name!r} is not in the NCC supplier list, so there is no export to "
        f"download.{suggestion} Either the registry's ncc_supplier_name does not match the "
        f"site's spelling, or this manufacturer has no FMLV products yet — a brand new to "
        f"FMLV has nothing to export, so run it from the command line against an empty "
        f"baseline instead (`fmlv empty-baseline <manufacturer>`, then `fmlv run "
        f"<manufacturer>`) until its first upload has created some."
    )
    raise SupplierNotListed(msg)


def _ensure_toggle_off(page, selector: str) -> None:
    """Click the "Only Active..." toggle if it's currently on.

    Nova renders this as a custom `role="checkbox"` element, not a native input, so
    state is read from `data-state` (`"checked"` / `"unchecked"`) rather than
    `checked`. Idempotent — if the toggle already reflects the last run's state,
    clicking it unconditionally would flip it the wrong way.
    """
    if page.get_attribute(selector, "data-state") == "checked":
        page.click(selector)


def caravan_export_path(
    motorhome_path: Path | str, *, config: NccSiteConfig = NccSiteConfig()
) -> Path:
    """Where the touring-caravan half of an export sits, given the motorhome half.

    One "Export Products by Supplier" action returns both sheets in one zip, so the two
    are always downloaded together and always belong to the same supplier and the same
    moment. Naming the caravan file by substitution rather than by its own date stamp is
    what keeps that pairing legible on disk months later:

        2026-08-20_Bailey_motorhome-campervans.xlsx
        2026-08-20_Bailey_touring-caravans.xlsx

    `cli.fetch_export` builds the motorhome name, so deriving the caravan one here means
    only one place knows the convention.
    """
    motorhome_path = Path(motorhome_path)
    motorhome_stem = Path(config.motorhome_export_filename).stem
    caravan_stem = Path(config.caravan_export_filename).stem
    if motorhome_stem in motorhome_path.name:
        return motorhome_path.with_name(
            motorhome_path.name.replace(motorhome_stem, caravan_stem)
        )
    return motorhome_path.with_name(f"{motorhome_path.stem}_{caravan_stem}.xlsx")


def download_export(
    credentials: NccCredentials,
    supplier_name: str,
    dest_path: Path | str,
    *,
    config: NccSiteConfig = NccSiteConfig(),
    headless: bool = True,
    executable_path: str | None = None,
    on_progress: Callable[[str], None] = lambda message: None,
) -> Path:
    """Log in to the NCC site and download one manufacturer's current export.

    `supplier_name` must match a label in the site's own "Export Products by Supplier"
    dropdown exactly — see `registry.Manufacturer.ncc_supplier_name`. A fresh browser
    is launched and closed for this one action rather than reusing a long-lived
    instance the way `BrowserFetcher` does for many manufacturer-page fetches — a run
    needs this exactly once, to obtain the baseline (DESIGN.md §5).

    `on_progress` fires at the two points worth narrating to someone watching a
    terminal — this whole call otherwise blocks silently for several seconds while a
    real browser drives a real login — following the same convention as
    `adapters.adria.collect`'s `on_progress`.

    Returns `dest_path` (parents created if needed) once the `.xlsx` has been
    extracted from the downloaded zip. `executable_path` overrides which Chromium
    binary Playwright launches — normally left as `None` so Playwright uses the
    browser installed for the pinned version (see `playwright install chromium`,
    TODO.md Phase 3); tests pass it explicitly to target a specific local build.
    """
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path = dest_path.with_suffix(".zip")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, executable_path=executable_path)
        try:
            page = browser.new_page()
            on_progress(f"logging in to {config.login_url}")
            page.goto(config.login_url)
            page.fill(config.email_selector, credentials.email)
            page.fill(config.password_selector, credentials.password)
            with page.expect_navigation():
                page.click(config.login_submit_selector)

            page.goto(config.products_url)
            page.click(config.actions_dropdown_selector)
            page.click(config.export_by_supplier_selector)
            _select_supplier(
                page, config.supplier_select_selector, supplier_name, on_progress
            )
            _ensure_toggle_off(page, config.only_active_toggle_selector)

            on_progress(f"triggering the export download for {supplier_name!r}")
            with page.expect_download() as download_info:
                page.click(config.run_action_selector)
            download_info.value.save_as(zip_path)
        finally:
            browser.close()

    try:
        with zipfile.ZipFile(zip_path) as archive:
            try:
                data = archive.read(config.motorhome_export_filename)
            except KeyError as exc:
                msg = (
                    f"{config.motorhome_export_filename!r} not found in the downloaded "
                    f"export for {supplier_name!r} — zip contains: {archive.namelist()}"
                )
                raise NccExportError(msg) from exc
            dest_path.write_bytes(data)

            # The caravan half of the same zip. Missing is normal and not an error — a
            # motorhome-only supplier's export simply has no caravan sheet — so this
            # narrates the outcome rather than raising the way the motorhome read does.
            caravan_path = caravan_export_path(dest_path, config=config)
            try:
                caravan_data = archive.read(config.caravan_export_filename)
            except KeyError:
                on_progress(f"no {config.caravan_export_filename!r} in {supplier_name!r}'s export")
            else:
                caravan_path.write_bytes(caravan_data)
                on_progress(f"saved the touring-caravan export to {caravan_path}")
    finally:
        zip_path.unlink(missing_ok=True)

    return dest_path
