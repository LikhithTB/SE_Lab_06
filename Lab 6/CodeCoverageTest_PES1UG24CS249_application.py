import pytest
from shipping_quote import process_shipments, monitor_container_pressures


def make_shipment(**overrides):
    """Build a valid, approved ground shipment; override any field."""
    shipment = {
        "manifest_approved": True,
        "mode": "ground",
        "is_fragile": False,
        "express_priority": False,
        "packages": [{"weight_kg": 10, "is_hazmat": False}],
    }
    shipment.update(overrides)
    return shipment


# Example test case:
def test_single_ground_shipment():
    shipments = [
        {
            "manifest_approved": True,
            "mode": "ground",
            "is_fragile": False,
            "express_priority": False,
            "packages": [{"weight_kg": 10, "is_hazmat": False}]
        }
    ]
    result = process_shipments(shipments, 20.0)
    assert result["total_quote"] == 60.0
    assert result["status"] == "CLEARED"


# ---------- process_shipments: input validation ----------

def test_non_list_shipments_raises():
    with pytest.raises(ValueError):
        process_shipments("not a list", 10.0)


def test_negative_handling_fee_raises():
    with pytest.raises(ValueError):
        process_shipments([], -1.0)


# ---------- process_shipments: manifest and transport modes ----------

def test_unapproved_manifest_is_skipped():
    shipments = [make_shipment(manifest_approved=False)]
    result = process_shipments(shipments, 20.0)
    assert result == {"total_quote": 0.0, "status": "NO_CARGO"}


def test_air_shipment_uses_air_rate():
    # 20 handling + 10 kg * 12.0 air rate = 140
    shipments = [make_shipment(mode="air")]
    result = process_shipments(shipments, 20.0)
    assert result["total_quote"] == 140.0
    assert result["status"] == "CLEARED"


def test_unknown_mode_is_rejected():
    shipments = [make_shipment(mode="sea")]
    result = process_shipments(shipments, 20.0)
    assert result == {"total_quote": 0.0, "status": "NO_CARGO"}


# ---------- process_shipments: packages ----------

def test_zero_weight_parcel_is_rejected_but_others_billed():
    # zero-weight parcel is rejected (+1); 10 kg ground = 40
    shipments = [make_shipment(packages=[{"weight_kg": 0}, {"weight_kg": 10}])]
    result = process_shipments(shipments, 0.0)
    assert result["total_quote"] == 40.0
    assert result["status"] == "CLEARED"


def test_hazmat_non_fragile_adds_flat_fifty():
    # 20 handling + 50 hazmat surcharge = 70
    shipments = [make_shipment(packages=[{"weight_kg": 5, "is_hazmat": True}])]
    result = process_shipments(shipments, 20.0)
    assert result["total_quote"] == 70.0
    assert result["status"] == "CLEARED"


def test_hazmat_fragile_zeroes_shipment_and_stops_billing_packages():
    # First shipment: fragile + hazmat -> cost forced to 0, remaining package ignored.
    # Second shipment: plain 10 kg ground = 40.
    # If the `break` were missing, the first shipment would add 40 -> total 80.
    shipments = [
        make_shipment(
            is_fragile=True,
            packages=[{"weight_kg": 5, "is_hazmat": True},
                      {"weight_kg": 10, "is_hazmat": False}],
        ),
        make_shipment(packages=[{"weight_kg": 10, "is_hazmat": False}]),
    ]
    result = process_shipments(shipments, 0.0)
    assert result["total_quote"] == 40.0
    assert result["status"] == "CLEARED"


def test_heavy_package_gets_surcharge_rate():
    # 40 kg > 30 -> 40 * (4.0 * 1.5) = 240
    shipments = [make_shipment(packages=[{"weight_kg": 40, "is_hazmat": False}])]
    result = process_shipments(shipments, 0.0)
    assert result["total_quote"] == 240.0


# ---------- process_shipments: express and totals ----------

def test_express_priority_multiplies_by_1_25():
    # (20 handling + 10 kg * 4.0) * 1.25 = 75
    shipments = [make_shipment(express_priority=True)]
    result = process_shipments(shipments, 20.0)
    assert result["total_quote"] == 75.0


def test_more_than_three_rejected_parcels_is_flagged():
    # four zero-weight parcels rejected; 10 kg ground billed = 40
    shipments = [make_shipment(
        packages=[{"weight_kg": 0}, {"weight_kg": 0},
                  {"weight_kg": 0}, {"weight_kg": 0},
                  {"weight_kg": 10}],
    )]
    result = process_shipments(shipments, 0.0)
    assert result == {"total_quote": 40.0, "status": "FLAGGED_REVIEW"}


def test_no_shipments_returns_no_cargo():
    result = process_shipments([], 5.0)
    assert result == {"total_quote": 0.0, "status": "NO_CARGO"}


# ---------- monitor_container_pressures ----------

def test_monitor_no_data_for_empty_input():
    assert monitor_container_pressures([]) == "NO_DATA"
    assert monitor_container_pressures(None) == "NO_DATA"


def test_monitor_detects_two_consecutive_low_readings():
    # 15 resets, then 13 and 12 are two consecutive low readings
    assert monitor_container_pressures([[15, 13, 12]]) == "LEAK_DETECTED"


def test_monitor_single_low_reading_is_not_a_leak_and_resets_streak():
    # 13 -> streak 1, 15 -> reset (else branch), 13 -> streak 1 again
    assert monitor_container_pressures([[13, 15, 13]]) == "STABLE"


def test_monitor_stable_when_all_readings_normal():
    assert monitor_container_pressures([[15, 16, 14.5]]) == "STABLE"
