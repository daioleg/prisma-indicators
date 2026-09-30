from __future__ import annotations

import unittest
from unittest import mock

from prisma_indicators.exceptions import (
    AuthenticationError,
    PrismaApiError,
    RateLimitExceededError,
)
from prisma_indicators.http_client import PrismaHttpClient, RetryPolicy
from tests.testing_utils import FakeResponse, FakeSession


def make_client(session: FakeSession, token_calls: list[bool] | None = None) -> PrismaHttpClient:
    calls = token_calls if token_calls is not None else []

    def token_provider(force_new: bool = False) -> str:
        calls.append(force_new)
        return "jwt-new" if force_new else "jwt-old"

    return PrismaHttpClient(
        base_url="https://api.example.com",
        token_provider=token_provider,
        session=session,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.01, max_delay_seconds=0.02),
    )


class TestPrismaHttpClient(unittest.TestCase):
    def test_success_returns_parsed_json(self) -> None:
        session = FakeSession([FakeResponse(200, {"ok": True})])
        client = make_client(session)

        result = client.request_json("GET", "/v3/inventory")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(session.calls[0]["headers"]["x-redlock-auth"], "jwt-old")

    def test_no_content_returns_none(self) -> None:
        session = FakeSession([FakeResponse(200, None)])
        client = make_client(session)

        result = client.request_json("GET", "/anything")

        self.assertIsNone(result)

    @mock.patch("time.sleep", return_value=None)
    def test_retries_on_5xx_then_succeeds(self, _sleep) -> None:
        session = FakeSession([FakeResponse(503, {"error": "unavailable"}), FakeResponse(200, {"ok": True})])
        client = make_client(session)

        result = client.request_json("GET", "/path")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(session.calls), 2)

    @mock.patch("time.sleep", return_value=None)
    def test_persistent_5xx_raises_after_max_attempts(self, _sleep) -> None:
        session = FakeSession([FakeResponse(500, {}) for _ in range(5)])
        client = make_client(session)

        with self.assertRaises(PrismaApiError):
            client.request_json("GET", "/path")

    @mock.patch("time.sleep", return_value=None)
    def test_429_respects_retry_after_header_then_succeeds(self, sleep_mock) -> None:
        session = FakeSession(
            [
                FakeResponse(429, {"error": "rate_limited"}, headers={"Retry-After": "2"}),
                FakeResponse(200, {"ok": True}),
            ]
        )
        client = make_client(session)

        result = client.request_json("GET", "/path")

        self.assertEqual(result, {"ok": True})
        sleep_mock.assert_called_once_with(2.0)

    @mock.patch("time.sleep", return_value=None)
    def test_persistent_429_raises_rate_limit_error(self, _sleep) -> None:
        session = FakeSession([FakeResponse(429, {}) for _ in range(5)])
        client = make_client(session)

        with self.assertRaises(RateLimitExceededError):
            client.request_json("GET", "/path")

    def test_401_renews_token_once_then_succeeds(self) -> None:
        session = FakeSession([FakeResponse(401, {"message": "expired"}), FakeResponse(200, {"ok": True})])
        token_calls: list[bool] = []
        client = make_client(session, token_calls)

        result = client.request_json("GET", "/path")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(token_calls, [False, True])
        self.assertEqual(session.calls[1]["headers"]["x-redlock-auth"], "jwt-new")

    def test_401_twice_raises_authentication_error(self) -> None:
        session = FakeSession([FakeResponse(401, {}), FakeResponse(401, {})])
        client = make_client(session)

        with self.assertRaises(AuthenticationError):
            client.request_json("GET", "/path")

    def test_unexpected_4xx_raises_prisma_api_error(self) -> None:
        session = FakeSession([FakeResponse(400, {"error": "bad_request"})])
        client = make_client(session)

        with self.assertRaises(PrismaApiError):
            client.request_json("GET", "/path")


if __name__ == "__main__":
    unittest.main()
