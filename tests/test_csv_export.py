import csv
import tempfile
import unittest
from pathlib import Path

from prisma_indicators.csv_export import (
    FIELDNAMES,
    totals_by_provider,
    write_provider_csvs,
)
from prisma_indicators.models import ResourceCount


def make_count(**overrides) -> ResourceCount:
    defaults = dict(
        provider="aws",
        service="Amazon EC2",
        resource_name="AWS EC2 Instance",
        account="prod",
        region="AWS Virginia",
        quantity=10,
    )
    defaults.update(overrides)
    return ResourceCount(**defaults)


class TestWriteProviderCsvs(unittest.TestCase):
    def test_writes_one_csv_per_provider_with_expected_columns(self) -> None:
        counts = [
            make_count(quantity=20000),
            make_count(provider="azure", service="Compute", resource_name="Azure VM"),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "output"
            written = write_provider_csvs(counts, output_dir)

            self.assertEqual(set(written.keys()), {"aws", "azure"})
            with (output_dir / "aws.csv").open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
            self.assertEqual(reader.fieldnames, FIELDNAMES)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["provedor"], "aws")
            self.assertEqual(rows[0]["service"], "Amazon EC2")
            self.assertEqual(rows[0]["resource name"], "AWS EC2 Instance")
            self.assertEqual(rows[0]["conta"], "prod")
            self.assertEqual(rows[0]["região"], "AWS Virginia")
            self.assertEqual(rows[0]["quantidade"], "20000")

    def test_provider_name_is_sanitized_for_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            written = write_provider_csvs(
                [make_count(provider="Some/Weird Provider!")], Path(tmp)
            )

            path = written["Some/Weird Provider!"]
            self.assertTrue(path.exists())
            self.assertNotIn("/", path.name)
            self.assertNotIn("!", path.name)


class TestTotalsByProvider(unittest.TestCase):
    def test_sums_quantity_per_provider(self) -> None:
        counts = [
            make_count(quantity=5),
            make_count(quantity=7, region="AWS Ohio"),
            make_count(provider="gcp", quantity=3),
        ]

        self.assertEqual(totals_by_provider(counts), {"aws": 12, "gcp": 3})


if __name__ == "__main__":
    unittest.main()
