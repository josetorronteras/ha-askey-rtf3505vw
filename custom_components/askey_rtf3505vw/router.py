"""Async HTTP client and HTML parsers for the Askey RTF3505VW router."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import aiohttp
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Router network constants (self-contained, no HA dependency)
# ---------------------------------------------------------------------------

DEFAULT_HOST = "192.168.1.1"

ENDPOINT_LOGIN = "/te_acceso_router.cgi"
ENDPOINT_DHCP = "/dhcpinfo.html"
ENDPOINT_ARP = "/arpview.cmd"
ENDPOINT_WIFI = "/wlstationlist.cmd"
ENDPOINT_WIFI_SWITCH_WL0 = "/wlswitchinterface0.wl"
ENDPOINT_WIFI_SWITCH_WL1 = "/wlswitchinterface1.wl"
ENDPOINT_INFO = "/info.html"

SESSION_COOKIE = "sessionID"

_LOGIN_INDICATORS = ("loginPassword", "te_acceso_router")

IFACE_WIFI_24 = "wl0"
IFACE_WIFI_24_GUEST = "wl0.1"
IFACE_WIFI_5 = "wl1"

_LOGGER = logging.getLogger(__name__)
_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")
_SESSION_KEY_RE = re.compile(r"var sessionKey='(\d+)'")


class SessionExpiredError(Exception):
    """Raised when the router returns the login page instead of requested data."""


def _is_login_page(html: str) -> bool:
    return any(indicator in html for indicator in _LOGIN_INDICATORS)


def _is_valid_mac(value: str) -> bool:
    return bool(_MAC_RE.match(value.strip()))


def _normalise_mac(mac: str) -> str:
    return mac.upper().replace("-", ":")


def _clean(text: str) -> str:
    """Strip whitespace and non-breaking spaces."""
    return text.replace("\xa0", "").strip()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RouterDevice:
    """Represents a device seen on the network."""

    mac: str
    ip: str = ""
    hostname: str = ""
    band: str = ""
    interface: str = ""
    dhcp_expires: str = ""
    rssi: int = 0
    ssid: str = ""

    def __post_init__(self) -> None:
        self.mac = _normalise_mac(self.mac)
        if not self.hostname:
            self.hostname = self.mac

    @property
    def is_wifi(self) -> bool:
        return self.band != ""

    @property
    def is_wired(self) -> bool:
        return self.band == ""

    @property
    def is_guest(self) -> bool:
        return "." in self.interface


@dataclass
class RouterInfo:
    """System information scraped from /info.html."""

    uptime_raw: str = ""       # e.g. "0D 4H 28M 53S"
    uptime_seconds: int = 0
    software_version: str = ""
    wireless_driver: str = ""


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

class AskeyRouterClient:
    """Async client that scrapes the Askey RTF3505VW web interface."""

    def __init__(self, session, host: str = DEFAULT_HOST, password: str = "") -> None:
        self._session = session
        self._base_url = f"http://{host}"
        self._password = password
        self._session_id: str | None = None
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Mobile Safari/537.36"
            )
        }

    async def async_login(self) -> bool:
        """Log in to the router. Returns True on success.

        Raises connection-related exceptions (aiohttp.ClientError, OSError,
        TimeoutError) so the caller can distinguish "router unreachable" from
        "wrong credentials".  Returns False only for authentication failures.
        """
        timeout = aiohttp.ClientTimeout(total=15)

        # Step 1: GET / to obtain the initial sessionID cookie
        resp = await self._session.get(
            self._base_url, headers=self._headers, allow_redirects=True,
            timeout=timeout,
        )
        session_id = self._extract_cookie(resp, SESSION_COOKIE)
        if not session_id:
            _LOGGER.error("Login step 1 failed: no %s in response", SESSION_COOKIE)
            return False

        # Step 2: POST credentials
        resp2 = await self._session.post(
            f"{self._base_url}{ENDPOINT_LOGIN}",
            data={"loginPassword": self._password},
            headers={
                **self._headers,
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": f"{SESSION_COOKIE}={session_id}",
                "Origin": self._base_url,
                "Referer": f"{self._base_url}/te_acceso_router.html",
            },
            allow_redirects=True,
            timeout=timeout,
        )
        new_session_id = self._extract_cookie(resp2, SESSION_COOKIE)
        self._session_id = new_session_id or session_id

        # Step 3: Verify login by checking the response is not the login page
        body = await resp2.text()
        if _is_login_page(body):
            _LOGGER.error("Login failed: router still showing login page after POST")
            return False

        _LOGGER.debug("Login OK — %s=%s", SESSION_COOKIE, self._session_id)
        return True

    async def async_close(self) -> None:
        """Close the underlying aiohttp session."""
        await self._session.close()

    async def async_test_credentials(self) -> bool:
        return await self.async_login()

    async def async_reboot(self) -> bool:
        """Reboot the router. Returns True if the command was sent successfully.

        Step 1: GET /resetrouter.html to extract the CSRF sessionKey.
        Step 2: GET /rebootinfo.cgi?sessionKey=XXXX to trigger the reboot.
        """
        html = await self._fetch("/resetrouter.html")
        if not html:
            _LOGGER.error("Reboot: could not fetch /resetrouter.html")
            return False

        match = _SESSION_KEY_RE.search(html)
        if not match:
            _LOGGER.error("Reboot: sessionKey not found in /resetrouter.html")
            return False

        session_key = match.group(1)
        _LOGGER.debug("Reboot: sessionKey=%s", session_key)
        await self._fetch(f"/rebootinfo.cgi?sessionKey={session_key}")
        _LOGGER.info("Reboot command sent to router")
        return True

    async def async_get_devices(self) -> dict[str, RouterDevice]:
        """Return {mac: RouterDevice} for every device currently on the network.

        Raises RuntimeError if both primary data sources (DHCP and ARP) fail,
        so the coordinator can distinguish "0 devices" from "router not
        responding".
        """
        devices: dict[str, RouterDevice] = {}
        sources_ok = 0

        # 1. DHCP leases — primary source for hostnames and IPs
        html = await self._fetch(ENDPOINT_DHCP)
        if html:
            sources_ok += 1
            for dev in _parse_dhcp(html):
                devices[dev.mac] = dev

        # 2. ARP table — catches devices with static IPs not in DHCP
        html = await self._fetch(ENDPOINT_ARP)
        if html:
            sources_ok += 1
            for dev in _parse_arp(html):
                if dev.mac not in devices:
                    devices[dev.mac] = dev
                else:
                    devices[dev.mac].interface = dev.interface

        if sources_ok == 0:
            raise RuntimeError("Both DHCP and ARP fetches failed — router may be unreachable")

        # 3. WiFi station lists — must switch radio before each fetch.
        #    The router exposes a single /wlstationlist.cmd endpoint; the active
        #    radio is selected by GETting /wlswitchinterfaceN.wl first.
        for switch_ep, band_hint in (
            (ENDPOINT_WIFI_SWITCH_WL0, "2.4GHz"),
            (ENDPOINT_WIFI_SWITCH_WL1, "5GHz"),
        ):
            await self._fetch(switch_ep)
            html = await self._fetch(ENDPOINT_WIFI)
            if not html or "<table" not in html.lower():
                continue
            for dev in _parse_wifi(html, band_hint=band_hint):
                if dev.mac in devices:
                    devices[dev.mac].band = dev.band
                    if dev.interface:
                        devices[dev.mac].interface = dev.interface
                    if dev.ssid:
                        devices[dev.mac].ssid = dev.ssid
                    if dev.rssi != 0:
                        devices[dev.mac].rssi = dev.rssi
                else:
                    devices[dev.mac] = dev

        _LOGGER.debug("Found %d device(s) on the network", len(devices))
        return devices

    async def async_get_info(self) -> RouterInfo | None:
        """Fetch system info (uptime, firmware version) from /info.html.

        Returns None when the page cannot be fetched so the caller can
        keep the previous good data instead of overwriting it with empty values.
        """
        html = await self._fetch(ENDPOINT_INFO)
        if html:
            return _parse_info(html)
        return None

    async def _fetch(self, path: str) -> str | None:
        """GET a router page and return its HTML body, or None on failure."""
        headers = {**self._headers, "Referer": f"{self._base_url}/menu.html"}
        if self._session_id:
            headers["Cookie"] = f"{SESSION_COOKIE}={self._session_id}"
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            resp = await self._session.get(
                f"{self._base_url}{path}", headers=headers, timeout=timeout,
            )
            if resp.status == 200:
                text = await resp.text()
                if _is_login_page(text):
                    raise SessionExpiredError(f"Session expired — login page returned for {path}")
                return text
            _LOGGER.debug("%s → HTTP %s", path, resp.status)
        except SessionExpiredError:
            raise
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Request to %s failed: [%s] %s", path, type(err).__name__, err)
        return None

    @staticmethod
    def _extract_cookie(resp, name: str) -> str | None:
        """Extract a cookie value from Set-Cookie headers or the cookie jar."""
        for header_val in resp.headers.getall("Set-Cookie", []):
            for part in header_val.split(";"):
                part = part.strip()
                if part.startswith(f"{name}="):
                    return part.split("=", 1)[1]
        if name in resp.cookies:
            return resp.cookies[name].value
        return None


# ---------------------------------------------------------------------------
# HTML parsers (pure functions — no HA dependency, easy to unit-test)
# ---------------------------------------------------------------------------

def _parse_dhcp(html: str) -> list[RouterDevice]:
    """Parse /dhcpinfo.html — columns: Hostname | MAC | IP | Expires."""
    results: list[RouterDevice] = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.find_all("tr")[1:]:
            cols = [_clean(td.get_text()) for td in row.find_all("td")]
            if len(cols) < 3:
                continue
            hostname, mac, ip = cols[0], cols[1], cols[2]
            expires = cols[3] if len(cols) > 3 else ""
            if not _is_valid_mac(mac):
                continue
            results.append(
                RouterDevice(mac=mac, ip=ip, hostname=hostname or mac, dhcp_expires=expires)
            )
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Error parsing DHCP page: %s", err)
    return results


def _parse_arp(html: str) -> list[RouterDevice]:
    """Parse /arpview.cmd — columns: IP | Flags | HW Address | Device."""
    results: list[RouterDevice] = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.find_all("tr")[1:]:
            cols = [_clean(td.get_text()) for td in row.find_all("td")]
            if len(cols) < 3:
                continue
            ip, _flags, mac = cols[0], cols[1], cols[2]
            interface = cols[3] if len(cols) > 3 else ""
            if not _is_valid_mac(mac):
                continue
            results.append(RouterDevice(mac=mac, ip=ip, interface=interface))
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Error parsing ARP page: %s", err)
    return results


def _parse_wifi(html: str, band_hint: str = "") -> list[RouterDevice]:
    """Parse /wlstationlist.cmd — columns: MAC | … | SSID | Interface | RSSI."""
    results: list[RouterDevice] = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue

            headers = [_clean(td.get_text()).lower() for td in rows[0].find_all(["th", "td"])]
            mac_idx = next((i for i, h in enumerate(headers) if "mac" in h or "address" in h), None)
            if mac_idx is None:
                continue

            ssid_idx  = next((i for i, h in enumerate(headers) if "ssid" in h), None)
            iface_idx = next((i for i, h in enumerate(headers) if "interface" in h or "iface" in h), None)
            rssi_idx  = next((i for i, h in enumerate(headers) if "rssi" in h or "signal" in h), None)

            for row in rows[1:]:
                cols = [_clean(td.get_text()) for td in row.find_all("td")]
                if len(cols) <= mac_idx:
                    continue
                mac = cols[mac_idx]
                if not _is_valid_mac(mac):
                    continue

                ssid      = cols[ssid_idx]  if ssid_idx  is not None and len(cols) > ssid_idx  else ""
                interface = cols[iface_idx] if iface_idx is not None and len(cols) > iface_idx else ""
                rssi_raw  = cols[rssi_idx]  if rssi_idx  is not None and len(cols) > rssi_idx  else "0"

                try:
                    rssi = int(rssi_raw.split()[0])
                except (ValueError, IndexError):
                    rssi = 0

                if interface.startswith("wl1"):
                    band = "5GHz"
                elif interface.startswith("wl0"):
                    band = "2.4GHz"
                else:
                    band = band_hint

                if not interface:
                    interface = "wl0" if "2.4" in band else "wl1"

                results.append(
                    RouterDevice(mac=mac, band=band, interface=interface, ssid=ssid, rssi=rssi)
                )
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Error parsing WiFi station list: %s", err)
    return results


def _parse_uptime(raw: str) -> int:
    """Convert '0D 4H 28M 53S' to total seconds."""
    total = 0
    for part in raw.upper().split():
        try:
            if part.endswith("D"):
                total += int(part[:-1]) * 86400
            elif part.endswith("H"):
                total += int(part[:-1]) * 3600
            elif part.endswith("M"):
                total += int(part[:-1]) * 60
            elif part.endswith("S"):
                total += int(part[:-1])
        except ValueError:
            pass
    return total


def _parse_info(html: str) -> RouterInfo:
    """Parse /info.html for uptime and firmware version."""
    info = RouterInfo()
    try:
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.find_all("tr"):
            cols = [_clean(td.get_text()) for td in row.find_all("td")]
            if len(cols) < 2:
                continue
            key, val = cols[0].lower(), cols[1]
            if "uptime" in key:
                info.uptime_raw = val
                info.uptime_seconds = _parse_uptime(val)
            elif "software version" in key:
                info.software_version = val
            elif "wireless driver" in key:
                info.wireless_driver = val
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Error parsing info page: %s", err)
    return info
