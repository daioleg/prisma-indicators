import unittest

from prisma_indicators.clients.inventory_client import (
    RESOURCE_COUNT_GROUP_BY,
    InventoryClient,
)
from tests.testing_utils import FakeHttpClient


class TestInventoryClient(unittest.TestCase):
    def test_fetch_resource_counts_sends_correct_body_and_parses_rows(self) -> None:
        http = FakeHttpClient(
            [
                {
                    "groupedAggregates": [
                        {
                            "cloudTypeName": "aws",
                            "serviceName": "Amazon EC2",
                            "resourceTypeName": "AWS EC2 Instance",
                            "accountName": "prod-account",
                            "accountId": "123456789012",
                            "regionName": "AWS Virginia",
                            "totalResources": 59,
                        }
                    ],
                    "timestamp": 123,
                }
            ]
        )
        client = InventoryClient(http)

        result = client.fetch_resource_counts()

        self.assertEqual(http.calls[0]["method"], "POST")
        self.assertEqual(http.calls[0]["path"], "/v3/inventory")
        self.assertEqual(
            http.calls[0]["json_body"], {"groupBy": RESOURCE_COUNT_GROUP_BY}
        )

        self.assertEqual(len(result), 1)
        row = result[0]
        self.assertEqual(row.provider, "aws")
        self.assertEqual(row.service, "Amazon EC2")
        self.assertEqual(row.resource_name, "AWS EC2 Instance")
        self.assertEqual(row.account, "prod-account")
        self.assertEqual(row.region, "AWS Virginia")
        self.assertEqual(row.quantity, 59)

    def test_missing_fields_fall_back(self) -> None:
        http = FakeHttpClient(
            [{"groupedAggregates": [{"cloudTypeName": "gcp", "accountId": "proj-1"}]}]
        )

        row = InventoryClient(http).fetch_resource_counts()[0]

        self.assertEqual(row.account, "proj-1")
        self.assertEqual(row.service, "N/A")
        self.assertEqual(row.region, "N/A")
        self.assertEqual(row.quantity, 0)

    def test_invalid_group_by_raises_value_error(self) -> None:
        client = InventoryClient(FakeHttpClient([]))

        with self.assertRaises(ValueError):
            client.fetch_resource_counts(["not.a.real.field"])

    def test_empty_grouped_aggregates_returns_empty_list(self) -> None:
        http = FakeHttpClient([{"groupedAggregates": []}])

        self.assertEqual(InventoryClient(http).fetch_resource_counts(), [])


if __name__ == "__main__":
    unittest.main()
