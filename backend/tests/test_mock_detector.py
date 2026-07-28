import pytest
from app.service import prediction_service

def test_mock_detector_no_static_features():
    """
    Test that the prediction service does not inject static mocked target features
    or traffic features that are not available in real-time.
    """
    features = prediction_service._construct_features_from_inputs(
        route_id="route_1",
        hour=8,
        weather_condition="Clear",
        traffic="Low"
    )

    # Assert that target leakage features are not mocked
    assert "passenger_count" not in features, "passenger_count is mocked"
    assert "demand_class" not in features, "demand_class is mocked"
    assert "occupancy_ratio" not in features, "occupancy_ratio is mocked"

    # Assert that missing real-time traffic features are not mocked
    assert "congestion_index" not in features, "congestion_index is mocked"
    assert "traffic_delay" not in features, "traffic_delay is mocked"
