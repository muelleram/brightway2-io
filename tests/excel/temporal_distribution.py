import os
import json
import numpy as np
import pytest
from bw2io import ExcelImporter
from bw2data.tests import bw2test
from bw_temporalis import FixedTD, FixedTimeOfYearTD, TemporalDistribution

from bw2io.strategies.csv import csv_restore_temporal_distributions

EXCEL_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "excel")


# ---------------------------------------------------------------------------
# Helpers – build minimal activity dicts with a temporal_distribution string
# -------------------------------------------------------------------


def make_data(td):
    """Wrap a TD object's JSON string in a minimal activity/exchange structure."""
    return [
        {
            "name": "test activity",
            "exchanges": [
                {
                    "name": "test exchange",
                    "amount": 1.0,
                    "temporal_distribution": td.to_json(),
                }
            ],
        }
    ]


# ---------------------------------------------------------------------------
# Unit tests – strategy function directly, no Excel file needed
# ---------------------------------------------------------------------------


def test_temporal_distribution_restored():
    """A TemporalDistribution JSON string is converted to a TD object."""
    td = TemporalDistribution(
        date=np.array([-1, 0, 1], dtype="timedelta64[Y]"),
        amount=np.array([0.25, 0.5, 0.25]),
    )
    data = make_data(td)
    result = csv_restore_temporal_distributions(data)

    restored = result[0]["exchanges"][0]["temporal_distribution"]
    assert isinstance(restored, TemporalDistribution)
    np.testing.assert_array_equal(restored.amount, td.amount)


def test_fixed_td_restored():
    """A FixedTD JSON string is converted to a FixedTD object."""
    td = FixedTD(
        date=np.array(["2020", "2021"], dtype="datetime64[Y]"),
        amount=np.array([0.4, 0.6]),
    )
    data = make_data(td)
    result = csv_restore_temporal_distributions(data)

    restored = result[0]["exchanges"][0]["temporal_distribution"]
    assert isinstance(restored, FixedTD)
    np.testing.assert_array_equal(restored.amount, td.amount)


def test_fixed_time_of_year_td_restored():
    """A FixedTimeOfYearTD JSON string is converted to a FixedTimeOfYearTD object."""
    td = FixedTimeOfYearTD(
        date=np.array([0, 100 * 24 * 3600], dtype="timedelta64[s]"),
        amount=np.array([0.5, 0.5]),
    )
    data = make_data(td)
    result = csv_restore_temporal_distributions(data)

    restored = result[0]["exchanges"][0]["temporal_distribution"]
    assert isinstance(restored, FixedTimeOfYearTD)
    np.testing.assert_array_equal(restored.amount, td.amount)


def test_short_loader_name_accepted():
    """Short __loader__ names (e.g. 'TemporalDistribution') are also accepted."""
    td = TemporalDistribution(
        date=np.array([-1, 0, 1], dtype="timedelta64[Y]"),
        amount=np.array([0.25, 0.5, 0.25]),
    )
    # Manually construct JSON with short loader name
    raw = json.loads(td.to_json())
    raw["__loader__"] = "TemporalDistribution"
    data = [
        {
            "name": "test activity",
            "exchanges": [
                {
                    "name": "test exchange",
                    "amount": 1.0,
                    "temporal_distribution": json.dumps(raw),
                }
            ],
        }
    ]
    result = csv_restore_temporal_distributions(data)
    restored = result[0]["exchanges"][0]["temporal_distribution"]
    assert isinstance(restored, TemporalDistribution)


def test_exchange_without_td_untouched():
    """Exchanges without a temporal_distribution field are left unchanged."""
    data = [
        {
            "name": "test activity",
            "exchanges": [{"name": "test exchange", "amount": 1.0}],
        }
    ]
    result = csv_restore_temporal_distributions(data)
    assert "temporal_distribution" not in result[0]["exchanges"][0]


def test_empty_exchanges_untouched():
    """Activities with no exchanges are handled gracefully."""
    data = [{"name": "test activity", "exchanges": []}]
    result = csv_restore_temporal_distributions(data)
    assert result[0]["exchanges"] == []


def test_invalid_json_raises_value_error():
    """A malformed JSON string raises a descriptive ValueError."""
    data = [
        {
            "name": "test activity",
            "exchanges": [
                {
                    "name": "test exchange",
                    "amount": 1.0,
                    "temporal_distribution": "this is not json",
                }
            ],
        }
    ]
    with pytest.raises(ValueError, match="Could not parse"):
        csv_restore_temporal_distributions(data)


def test_missing_loader_key_raises_value_error():
    """JSON without a __loader__ key raises a descriptive ValueError."""
    raw = json.dumps({"date_dtype": "timedelta64[s]", "date": [0], "amount": [1.0]})
    data = [
        {
            "name": "test activity",
            "exchanges": [
                {"name": "test exchange", "amount": 1.0, "temporal_distribution": raw}
            ],
        }
    ]
    with pytest.raises(ValueError, match="missing the `__loader__` key"):
        csv_restore_temporal_distributions(data)


def test_unknown_loader_raises_value_error():
    """An unknown __loader__ value raises a descriptive ValueError."""
    raw = json.dumps(
        {"__loader__": "bw_temporalis.UnknownClass", "date": [0], "amount": [1.0]}
    )
    data = [
        {
            "name": "test activity",
            "exchanges": [
                {"name": "test exchange", "amount": 1.0, "temporal_distribution": raw}
            ],
        }
    ]
    with pytest.raises(ValueError, match="Unknown `__loader__`"):
        csv_restore_temporal_distributions(data)


def test_idempotent():
    """Applying the strategy twice does not raise or corrupt the data."""
    td = TemporalDistribution(
        date=np.array([-1, 0, 1], dtype="timedelta64[Y]"),
        amount=np.array([0.25, 0.5, 0.25]),
    )
    data = make_data(td)
    result = csv_restore_temporal_distributions(data)
    result = csv_restore_temporal_distributions(result)  # second pass

    restored = result[0]["exchanges"][0]["temporal_distribution"]
    assert isinstance(restored, TemporalDistribution)


@bw2test
def test_excel_importer_restores_temporal_distributions():
    """ExcelImporter correctly deserializes temporal_distribution columns end-to-end.

    The fixture file contains:
    - a production exchange with no TD
    - a technosphere exchange (hard coal) with a relative TemporalDistribution
      specified in years (timedelta64[Y])
    - a technosphere exchange (natural gas) with no TD
    - a biosphere exchange (CO2) with a FixedTD specified with string dates
      (datetime64[D]), e.g. "2025-02-21"

    Note: bw_temporalis always converts all date inputs to seconds internally
    (timedelta64[s] or datetime64[s]) regardless of the original unit specified
    in the JSON. This is by design for consistent convolution math.
    """
    ei = ExcelImporter(os.path.join(EXCEL_FIXTURES_DIR, "temporal_distributions.xlsx"))
    ei.apply_strategies()

    activity = next(ds for ds in ei.data if ds["name"] == "electricity production")
    exchanges = {exc["name"]: exc for exc in activity["exchanges"]}

    # production exchange has no TD
    assert "temporal_distribution" not in exchanges["electricity production"]

    # hard coal has a relative TemporalDistribution with timedelta64[Y] input.
    # bw_temporalis converts [-1, 0, 1] years to seconds internally.
    td = exchanges["hard coal production"]["temporal_distribution"]
    assert isinstance(td, TemporalDistribution)
    assert len(td.date) == 3
    np.testing.assert_array_almost_equal(td.amount, [0.25, 0.5, 0.25])
    np.testing.assert_array_almost_equal(td.date.astype(int), [-31556952, 0, 31556952])

    # natural gas has no TD
    assert "temporal_distribution" not in exchanges["natural gas production"]

    # CO2 has a FixedTD with string datetime64[D] input ("2025-02-21", "2026-03-01").
    # bw_temporalis converts these to seconds internally.
    td_fixed = exchanges["CO2"]["temporal_distribution"]
    assert isinstance(td_fixed, FixedTD)
    assert len(td_fixed.date) == 2
    np.testing.assert_array_almost_equal(td_fixed.amount, [0.4, 0.6])
    np.testing.assert_array_almost_equal(
        td_fixed.date.astype(int), [1740096000, 1772323200]
    )
