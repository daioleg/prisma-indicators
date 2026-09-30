import unittest
from unittest import mock

from prisma_indicators.auth import PrismaAuth, TOKEN_TTL_SECONDS
from prisma_indicators.config import PrismaConfig
from prisma_indicators.exceptions import AuthenticationError
from tests.testing_utils import FakeResponse, FakeSession


def make_config() -> PrismaConfig:
    return PrismaConfig(
        base_url="https://api.example.com", access_key="ak", secret_key="sk"
    )


class TestPrismaAuth(unittest.TestCase):
    def test_login_success_extracts_token_field(self) -> None:
        session = FakeSession(
            [FakeResponse(200, {"token": "jwt-123", "message": "login_successful"})]
        )
        auth = PrismaAuth(make_config(), session=session)

        token = auth.get_token()

        self.assertEqual(token, "jwt-123")
        sent_body = session.calls[0]["json"]
        self.assertEqual(sent_body, {"username": "ak", "password": "sk"})

    def test_login_failure_raises_sanitized_error(self) -> None:
        session = FakeSession([FakeResponse(401, {"message": "invalid_credentials"})])
        auth = PrismaAuth(make_config(), session=session)

        with self.assertRaises(AuthenticationError) as ctx:
            auth.get_token()

        message = str(ctx.exception)
        self.assertIn("invalid_credentials", message)
        self.assertNotIn("sk", message)

    def test_login_success_without_token_field_raises(self) -> None:
        session = FakeSession([FakeResponse(200, {"message": "ok"})])
        auth = PrismaAuth(make_config(), session=session)

        with self.assertRaises(AuthenticationError):
            auth.get_token()

    def test_token_reused_when_not_near_expiry(self) -> None:
        session = FakeSession([FakeResponse(200, {"token": "jwt-1"})])
        auth = PrismaAuth(make_config(), session=session)

        first = auth.get_token()
        second = auth.get_token()

        self.assertEqual(first, "jwt-1")
        self.assertEqual(second, "jwt-1")
        self.assertEqual(len(session.calls), 1)

    def test_token_renewed_when_near_expiry(self) -> None:
        session = FakeSession(
            [FakeResponse(200, {"token": "jwt-1"}), FakeResponse(200, {"token": "jwt-2"})]
        )
        auth = PrismaAuth(make_config(), session=session)

        with mock.patch(
            "time.monotonic", side_effect=[0.0, TOKEN_TTL_SECONDS, TOKEN_TTL_SECONDS]
        ):
            first = auth.get_token()
            second = auth.get_token()

        self.assertEqual(first, "jwt-1")
        self.assertEqual(second, "jwt-2")
        self.assertEqual(len(session.calls), 2)

    def test_force_new_always_relogs_in(self) -> None:
        session = FakeSession(
            [FakeResponse(200, {"token": "jwt-1"}), FakeResponse(200, {"token": "jwt-2"})]
        )
        auth = PrismaAuth(make_config(), session=session)

        auth.get_token()
        second = auth.get_token(force_new=True)

        self.assertEqual(second, "jwt-2")
        self.assertEqual(len(session.calls), 2)


if __name__ == "__main__":
    unittest.main()
