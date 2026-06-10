"""Tests for AskeyRouterClient.async_login covering router quirks."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from multidict import CIMultiDict

from router import AskeyRouterClient


def _mock_response(*, set_cookie: str | None, body: str):
    resp = MagicMock()
    headers = CIMultiDict()
    if set_cookie is not None:
        headers.add("Set-Cookie", set_cookie)
    resp.headers = headers
    resp.cookies = {}
    resp.text = AsyncMock(return_value=body)
    return resp


def _mock_session(get_resp, post_resp):
    session = MagicMock()
    session.get = AsyncMock(return_value=get_resp)
    session.post = AsyncMock(return_value=post_resp)
    return session


SUCCESS_BODY = (
    "<html><head><title></title>"
    "<script>window.top.location = \"/\";</script></head></html>"
)
LOGIN_FORM_BODY = (
    '<html><body><form action="te_acceso_router.cgi">'
    '<input name="loginPassword"></form></body></html>'
)


@pytest.mark.asyncio
async def test_login_success():
    get_resp = _mock_response(
        set_cookie="sessionID=12345; path=/; HttpOnly", body="<html></html>"
    )
    post_resp = _mock_response(
        set_cookie="sessionID=12345; path=/; HttpOnly", body=SUCCESS_BODY
    )
    client = AskeyRouterClient(_mock_session(get_resp, post_resp), password="x")

    assert await client.async_login() is True


@pytest.mark.asyncio
async def test_login_rejects_sessionid_zero(caplog):
    # The router returns sessionID=0 when no admin slot is free. We must not
    # proceed with the POST (it would always fail) and the user needs to know.
    get_resp = _mock_response(
        set_cookie="sessionID=0; path=/; HttpOnly", body="<html></html>"
    )
    post_resp = _mock_response(set_cookie=None, body="")
    session = _mock_session(get_resp, post_resp)
    client = AskeyRouterClient(session, password="x")

    assert await client.async_login() is False
    session.post.assert_not_awaited()
    assert "sessionID=0" in caplog.text


@pytest.mark.asyncio
async def test_login_fails_when_post_returns_login_form():
    get_resp = _mock_response(
        set_cookie="sessionID=999; path=/; HttpOnly", body="<html></html>"
    )
    post_resp = _mock_response(set_cookie=None, body=LOGIN_FORM_BODY)
    client = AskeyRouterClient(_mock_session(get_resp, post_resp), password="x")

    assert await client.async_login() is False


@pytest.mark.asyncio
async def test_login_fails_when_no_session_cookie():
    get_resp = _mock_response(set_cookie=None, body="<html></html>")
    post_resp = _mock_response(set_cookie=None, body="")
    session = _mock_session(get_resp, post_resp)
    client = AskeyRouterClient(session, password="x")

    assert await client.async_login() is False
    session.post.assert_not_awaited()
