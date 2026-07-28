from apscheduler.schedulers.background import BackgroundScheduler
import time
from .logger import app_logger

# Global scheduler instance
scheduler = BackgroundScheduler()

def fetch_weather_task():
    """Simulate fetching weather data periodically."""
    app_logger.info("Scheduler: Executing weather update task.")
    # In a real app, this would call an external API and update a global state or DB
    # We will just log it here as simulated
    
def refresh_demand_predictions_task():
    """Simulate refreshing ML demand predictions."""
    app_logger.info("Scheduler: Executing demand prediction refresh task.")
    from .cache import app_cache
    # Clear ML prediction caches to force recomputation
    # Or precompute and store in cache
    # app_cache.clear() # Clears all for simplicity, or could clear specific keys

def run_optimization_task():
    """Simulate rerunning MILP optimization."""
    app_logger.info("Scheduler: Executing MILP optimization rerun task.")
    # In a real app, we'd trigger the optimize_fleet logic and cache the new result
    from .cache import app_cache
    # app_cache.set('latest_optimization', result)

def start_scheduler():
    if not scheduler.running:
        # Schedule jobs
        scheduler.add_job(fetch_weather_task, 'interval', minutes=15, id='weather_job', replace_existing=True)
        scheduler.add_job(refresh_demand_predictions_task, 'interval', minutes=30, id='demand_job', replace_existing=True)
        scheduler.add_job(run_optimization_task, 'interval', hours=1, id='optimization_job', replace_existing=True)
        
        scheduler.start()
        app_logger.info("Background Scheduler started successfully.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        app_logger.info("Background Scheduler stopped.")
