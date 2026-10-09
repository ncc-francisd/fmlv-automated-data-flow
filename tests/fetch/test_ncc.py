"""Tests for the NCC login/download flow, against local fixtures (no real network).

Requires Chromium to be installed once via `uv run playwright install chromium` (see
the note in `tests/fetch/test_browser.py`). The fixtures mirror the real Nova admin
site's selectors as surveyed 2026-08-06 (`fetch/ncc.py`'s module docstring) — a login
form, then an actions-dropdown → modal → zip-download flow on a stand-in
`ncc_products.html`, rather than a single download link.
"""

from __future__ import annotations

import threading
import zipfile
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError

from src.fetch.ncc import (
    CREDENTIALS_EMAIL_ENV,
    CREDENTIALS_PASSWORD_ENV,
    NccCredentials,
    NccCredentialsError,
    NccExportError,
    NccSiteConfig,
    _save_download,
    caravan_export_path,
    download_export,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def fixture_server() -> Iterator[str]:
    """A local HTTP server over `fixtures/` standing in for the NCC site."""
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURES_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


@pytest.fixture
def config(fixture_server: str) -> NccSiteConfig:
    return NccSiteConfig(
        login_url=f"{fixture_server}/ncc_login.html",
        products_url=f"{fixture_server}/ncc_products.html",
    )


def test_credentials_from_env_reads_both_variables() -> None:
    credentials = NccCredentials.from_env(
        env={CREDENTIALS_EMAIL_ENV: "reviewer@example.com", CREDENTIALS_PASSWORD_ENV: "secret"}
    )

    assert credentials.email == "reviewer@example.com"
    assert credentials.password == "secret"


@pytest.mark.parametrize(
    "env",
    [
        {},
        {CREDENTIALS_EMAIL_ENV: "reviewer@example.com"},
        {CREDENTIALS_PASSWORD_ENV: "secret"},
    ],
)
def test_credentials_from_env_requires_both_variables(env: dict[str, str]) -> None:
    with pytest.raises(NccCredentialsError):
        NccCredentials.from_env(env=env)


def test_download_export_logs_in_selects_the_supplier_and_extracts_the_xlsx(
    config: NccSiteConfig, tmp_path: Path
) -> None:
    credentials = NccCredentials(email="reviewer@example.com", password="secret")
    dest_path = tmp_path / "downloads" / "motorhome-campervans.xlsx"

    result_path = download_export(credentials, "Test Motorhomes", dest_path, config=config)

    assert result_path == dest_path
    assert dest_path.exists()
    with zipfile.ZipFile(FIXTURES_DIR / "ncc_export.zip") as archive:
        expected = archive.read("motorhome-campervans.xlsx")
    assert dest_path.read_bytes() == expected
    # The zip is a scratch download, not something a caller should have to clean up.
    assert not dest_path.with_suffix(".zip").exists()


def test_download_export_also_saves_the_touring_caravan_sheet(
    config: NccSiteConfig, tmp_path: Path
) -> None:
    """One export action returns both sheets, so both should survive the download.

    Until 2026-09-03 the caravan half was read out of the zip's namelist and then
    dropped on the floor with the zip itself, which is why no caravan baseline existed
    for any of the sixteen manufacturers already fetched.
    """
    credentials = NccCredentials(email="reviewer@example.com", password="secret")
    dest_path = tmp_path / "downloads" / "2026-09-03_Test_motorhome-campervans.xlsx"

    download_export(credentials, "Test Motorhomes", dest_path, config=config)

    caravan_path = dest_path.with_name("2026-09-03_Test_touring-caravans.xlsx")
    assert caravan_path.exists()
    with zipfile.ZipFile(FIXTURES_DIR / "ncc_export.zip") as archive:
        expected = archive.read("touring-caravans.xlsx")
    assert caravan_path.read_bytes() == expected


def test_download_export_tolerates_an_export_with_no_caravan_sheet(
    config: NccSiteConfig, tmp_path: Path
) -> None:
    """A motorhome-only supplier is normal, not an error.

    The motorhome read raises when its file is absent because there would be no
    baseline at all; the caravan read must not, or every motorhome-only manufacturer
    would start failing its fetch.
    """
    credentials = NccCredentials(email="reviewer@example.com", password="secret")
    dest_path = tmp_path / "downloads" / "motorhome-campervans.xlsx"
    no_caravans = NccSiteConfig(
        login_url=config.login_url,
        products_url=config.products_url,
        caravan_export_filename="not-in-this-zip.xlsx",
    )
    messages: list[str] = []

    result_path = download_export(
        credentials,
        "Test Motorhomes",
        dest_path,
        config=no_caravans,
        on_progress=messages.append,
    )

    assert result_path.exists()
    assert not caravan_export_path(dest_path, config=no_caravans).exists()
    assert any("not-in-this-zip.xlsx" in message for message in messages)


def test_caravan_export_path_pairs_the_two_sheets_by_name() -> None:
    motorhome = Path("data/exports/28_Bailey/2026-08-20_Bailey_motorhome-campervans.xlsx")

    assert caravan_export_path(motorhome).name == "2026-08-20_Bailey_touring-caravans.xlsx"
    assert caravan_export_path(motorhome).parent == motorhome.parent


def test_download_export_raises_a_clear_error_when_the_xlsx_is_missing(
    config: NccSiteConfig, tmp_path: Path
) -> None:
    credentials = NccCredentials(email="reviewer@example.com", password="secret")
    dest_path = tmp_path / "downloads" / "motorhome-campervans.xlsx"
    bad_config = NccSiteConfig(
        login_url=config.login_url,
        products_url=config.products_url,
        motorhome_export_filename="does-not-exist.xlsx",
    )

    with pytest.raises(NccExportError, match="does-not-exist.xlsx"):
        download_export(credentials, "Test Motorhomes", dest_path, config=bad_config)


# --- Why a download failed ------------------------------------------------------------
#
# Playwright reports every unfinished download as `Download.save_as: canceled` whatever
# the cause, and on 8-9 October 2026 that cost two days: Nova had generated the export
# correctly and Cloudflare was refusing the link with a 403, but the message named none
# of it, so the adapter, the VM, the registry row and the account were all suspected
# first. These cover the message that replaced it.


class _FakeResponse:
    def __init__(self, status: int, body: str, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self.headers = headers or {}
        self._body = body

    def text(self) -> str:
        return self._body


class _FakeRequest:
    def __init__(self, response: _FakeResponse | None) -> None:
        self._response = response

    def get(self, url: str) -> _FakeResponse:  # noqa: ARG002
        if self._response is None:
            raise PlaywrightError("connection closed")
        return self._response


class _FakePage:
    def __init__(self, response: _FakeResponse | None) -> None:
        self.request = _FakeRequest(response)


class _FakeDownload:
    """A download that never completes, which is the only case `_save_download` handles."""

    url = "https://findmyleisurevehicle.co.uk/storage/product-exports/1791539091-x.zip"

    def save_as(self, path: Path) -> None:  # noqa: ARG002
        raise PlaywrightError("Download.save_as: canceled")


_CLOUDFLARE_403 = (
    "Sorry, you have been blocked You are unable to access findmyleisurevehicle.co.uk"
)


def test_a_blocked_download_names_the_status_the_url_and_who_refused(tmp_path: Path) -> None:
    page = _FakePage(_FakeResponse(403, _CLOUDFLARE_403, {"cf-ray": "a47c72fcdafdc4f1-LHR"}))
    with pytest.raises(NccExportError) as caught:
        _save_download(page, _FakeDownload(), tmp_path / "export.zip", "Barefoot Caravans")
    message = str(caught.value)
    assert "HTTP 403" in message
    assert "Cloudflare" in message
    assert "a47c72fcdafdc4f1-LHR" in message
    assert "storage/product-exports" in message
    assert "Barefoot Caravans" in message


def test_a_blocked_download_says_nova_did_its_part(tmp_path: Path) -> None:
    """The point of the message: stop the reader suspecting the adapter or the account."""
    page = _FakePage(_FakeResponse(403, _CLOUDFLARE_403))
    with pytest.raises(NccExportError, match="Nova generated the export correctly"):
        _save_download(page, _FakeDownload(), tmp_path / "export.zip", "Barefoot Caravans")


def test_a_non_cloudflare_failure_still_reports_its_status(tmp_path: Path) -> None:
    """A 500 from the site itself is reported the same way, without naming Cloudflare."""
    page = _FakePage(_FakeResponse(500, "<html>Server Error</html>"))
    with pytest.raises(NccExportError) as caught:
        _save_download(page, _FakeDownload(), tmp_path / "export.zip", "Swift Group Ltd")
    message = str(caught.value)
    assert "HTTP 500" in message
    assert "refused by the server" in message
    assert "Cloudflare" not in message


def test_an_unreachable_link_says_so_rather_than_hiding_the_failure(tmp_path: Path) -> None:
    """If the probe itself fails there is still a better message than 'canceled'."""
    page = _FakePage(None)
    with pytest.raises(NccExportError) as caught:
        _save_download(page, _FakeDownload(), tmp_path / "export.zip", "Barefoot Caravans")
    assert "could not be re-requested" in str(caught.value)
