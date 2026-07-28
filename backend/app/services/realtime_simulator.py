import asyncio
from ..websocket_manager import manager
from ..logger import app_logger
from .vehicle_tracking_service import vehicle_tracking_service

async def generate_realtime_updates():
    """Generates real-time vehicle updates every 5 seconds and broadcasts via WebSockets."""
    app_logger.info("Real-time vehicle simulator started.")
    
    while True:
        try:
            await asyncio.sleep(5)
            active_buses = list(vehicle_tracking_service.active_vehicles.keys())
            
            for bus_id in active_buses:
                state = vehicle_tracking_service.update_vehicle_position(bus_id)
                if state:
                    update_msg = {
                        "type":               "vehicle_update",
                        "route_id":           state["route_id"],
                        "bus_id":             state["bus_id"],
                        "current_stop_index": state["current_stop_index"],
                        # ETA
                        "eta_minutes":        state["eta_minutes"],
                        "delay_minutes":      state.get("delay_minutes"),
                        "eta_confidence":     state.get("eta_confidence"),
                        # Occupancy
                        "occupancy_percent":  state["occupancy_percent"],
                        # Demand KPIs
                        "predicted_demand":   state.get("predicted_demand"),
                        "demand_confidence":  state.get("demand_confidence"),
                        # Fleet KPIs
                        "required_buses":     state.get("required_buses"),
                        "fleet_utilization":  state.get("fleet_utilization"),
                        "fleet_gap":          state.get("fleet_gap"),
                        "allocation_status":  state.get("allocation_status"),
                        # Route & Intelligence KPIs
                        "route_efficiency":   state.get("route_efficiency"),
                        "peak_status":        state.get("peak_status"),
                        "optimization_score": state.get("optimization_score"),
                    }
                    await manager.broadcast(update_msg)
            
        except asyncio.CancelledError:
            app_logger.info("Real-time vehicle simulator stopped.")
            break
        except Exception as e:
            app_logger.error(f"Error in realtime simulator: {e}", exc_info=True)
            await asyncio.sleep(5)
