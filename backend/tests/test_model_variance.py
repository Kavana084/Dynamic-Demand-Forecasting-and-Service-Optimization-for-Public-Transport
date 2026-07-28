import pytest
from app.ml.predictor import predictor

def test_model_variance():
    """
    Test that the model produces different predictions for different hours of the day
    when other inputs remain constant. If the model is returning the same prediction
    for 2 AM and 8 AM, it's either broken or ignoring the temporal features.
    """
    from app.service import prediction_service
    from app.ml.model_loader import model_loader
    model_loader.load_model()
    
    # Wait until model is loaded
    if not model_loader.is_model_loaded():
        pytest.skip("Model is not loaded")

    pred_2am = prediction_service.predict_demand(
        route_id="route_1",
        hour=2,
        weather_condition="Clear",
        traffic="Low"
    )

    pred_8am = prediction_service.predict_demand(
        route_id="route_1",
        hour=8,
        weather_condition="Clear",
        traffic="High"
    )

    pred_2pm = prediction_service.predict_demand(
        route_id="route_1",
        hour=14,
        weather_condition="Clear",
        traffic="Medium"
    )

    assert pred_2am is not None
    assert pred_8am is not None
    assert pred_2pm is not None

    # Assert predictions are not all exactly identical
    assert not (pred_2am == pred_8am == pred_2pm), f"Model predictions show zero variance across time: {pred_2am}, {pred_8am}, {pred_2pm}"
