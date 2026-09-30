import os
import unittest
from unittest import mock

from prisma_indicators.config import PrismaConfig
from prisma_indicators.exceptions import ConfigError


class TestPrismaConfig(unittest.TestCase):
    def test_from_env_success(self) -> None:
        env = {
            "PRISMA_BASE_URL": "https://api2.eu.prismacloud.io/",
            "PRISMA_ACCESS_KEY": "access-key-id",
            "PRISMA_SECRET_KEY": "super-secret",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            config = PrismaConfig.from_env()

        self.assertEqual(config.base_url, "https://api2.eu.prismacloud.io")
        self.assertEqual(config.access_key, "access-key-id")
        self.assertEqual(config.secret_key, "super-secret")

    def test_from_env_missing_vars_raises_without_leaking_values(self) -> None:
        env = {
            "PRISMA_BASE_URL": "",
            "PRISMA_ACCESS_KEY": "",
            "PRISMA_SECRET_KEY": "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            with self.assertRaises(ConfigError) as ctx:
                PrismaConfig.from_env()

        message = str(ctx.exception)
        self.assertIn("PRISMA_BASE_URL", message)
        self.assertIn("PRISMA_ACCESS_KEY", message)
        self.assertIn("PRISMA_SECRET_KEY", message)

    def test_repr_never_shows_secret(self) -> None:
        config = PrismaConfig(
            base_url="https://api.example.com", access_key="ak", secret_key="topsecret"
        )
        self.assertNotIn("topsecret", repr(config))
        self.assertNotIn("ak", repr(config))


if __name__ == "__main__":
    unittest.main()
