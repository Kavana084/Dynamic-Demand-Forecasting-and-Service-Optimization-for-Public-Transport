import pytest
from backend.app.services.eta_prediction_service import predict_eta

def test_eta_prediction_low_traffic():
    route_path = [1, 2, 3, 4, 5]
    result = predict_eta(
        route_path=route_path,
        current_stop_index=0,
        traffic_level="Low",
        occupancy_percent=40,
        transfer_count=0
    )
    assert result["eta_minutes"] == 48 # 4 remaining * 12
    assert result["delay_minutes"] == 0
    assert result["confidence"] == 0.95

def test_eta_prediction_high_traffic_high_occupancy():
    route_path = [1, 2, 3, 4, 5]
    result = predict_eta(
        route_path=route_path,
        current_stop_index=0,
        traffic_level="High",
        occupancy_percent=85,
        transfer_count=0
    )
    # base = 48
    # traffic penalty = 48 * 0.25 = 12
    # occupancy penalty = 48 * 0.10 = 4
    # delay = 16
    assert result["delay_minutes"] == 16
    assert result["eta_minutes"] == 64
    assert result["confidence"] == 0.80

def test_eta_prediction_multi_transfer():
    route_path = [1, 2, 3]
    result = predict_eta(
        route_path=route_path,
        current_stop_index=0,
        traffic_level="Low",
        occupancy_percent=40,
        transfer_count=2
    )
    # base = 2 * 12 = 24
    # penalty = 5
    assert result["delay_minutes"] == 5
    assert result["eta_minutes"] == 29
    assert result["confidence"] == 0.90
