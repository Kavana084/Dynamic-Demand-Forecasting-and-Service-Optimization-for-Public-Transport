import re

with open('backend/app/services/analytics_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Current logic:
#         # 1. Predicted Demand (Current Window)
#         q_pred = db.query(
#             ForecastHistory.route_id,
#             Route.route_short_name,
#             func.sum(ForecastHistory.predicted_passengers).label('total_pred'),
#             func.max(ForecastHistory.generated_at).label('last_updated')
#         ).join(Route, Route.route_id == ForecastHistory.route_id)
#         if start and end:
#             q_pred = q_pred.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
#         q_pred = _apply_route_scope_filter(db, q_pred, ForecastHistory.route_id, region, depot)
#         pred_rows = q_pred.group_by(ForecastHistory.route_id, Route.route_short_name).all()

# We need to change it to:
#         q_pred = db.query(
#             ForecastHistory.route_id,
#             Route.route_short_name,
#             ForecastHistory.predicted_passengers,
#             ForecastHistory.generated_at
#         ).join(Route, Route.route_id == ForecastHistory.route_id)
#         if start and end:
#             q_pred = q_pred.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
#         q_pred = _apply_route_scope_filter(db, q_pred, ForecastHistory.route_id, region, depot)
#         q_pred = q_pred.order_by(ForecastHistory.generated_at.desc())
#         all_pred_rows = q_pred.all()
#         pred_dict = {}
#         for r in all_pred_rows:
#             if r.route_id not in pred_dict:
#                 pred_dict[r.route_id] = type('Row', (), {'route_id': r.route_id, 'route_short_name': r.route_short_name, 'total_pred': r.predicted_passengers, 'last_updated': r.generated_at})
#         pred_rows = list(pred_dict.values())

old_pred_logic = """        # 1. Predicted Demand (Current Window)
        q_pred = db.query(
            ForecastHistory.route_id,
            Route.route_short_name,
            func.sum(ForecastHistory.predicted_passengers).label('total_pred'),
            func.max(ForecastHistory.generated_at).label('last_updated')
        ).join(Route, Route.route_id == ForecastHistory.route_id)
        if start and end:
            q_pred = q_pred.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
        q_pred = _apply_route_scope_filter(db, q_pred, ForecastHistory.route_id, region, depot)
        pred_rows = q_pred.group_by(ForecastHistory.route_id, Route.route_short_name).all()"""

new_pred_logic = """        # 1. Predicted Demand (Current Window) - Latest only
        q_pred = db.query(
            ForecastHistory.route_id,
            Route.route_short_name,
            ForecastHistory.predicted_passengers,
            ForecastHistory.generated_at
        ).join(Route, Route.route_id == ForecastHistory.route_id)
        if start and end:
            q_pred = q_pred.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
        q_pred = _apply_route_scope_filter(db, q_pred, ForecastHistory.route_id, region, depot)
        q_pred = q_pred.order_by(ForecastHistory.generated_at.desc())
        all_pred_rows = q_pred.all()
        pred_dict = {}
        for r in all_pred_rows:
            if r.route_id not in pred_dict:
                pred_dict[r.route_id] = type('Row', (), {'route_id': r.route_id, 'route_short_name': r.route_short_name, 'total_pred': r.predicted_passengers, 'last_updated': r.generated_at})
        pred_rows = list(pred_dict.values())"""

content = content.replace(old_pred_logic, new_pred_logic)

with open('backend/app/services/analytics_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated analytics_service.py predicted demand logic')
