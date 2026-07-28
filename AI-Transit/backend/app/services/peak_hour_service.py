from datetime import datetime

class PeakHourService:
    @staticmethod
    def detect_peak_hour(hour_of_day: int) -> dict:
        """
        Detect peak-hour and surge conditions based on the hour of the day.
        
        Rules:
        Morning Peak: 07:00 - 10:00 (inclusive hours 7, 8, 9, 10)
        Evening Peak: 17:00 - 21:00 (inclusive hours 17, 18, 19, 20, 21)
        """
        if 7 <= hour_of_day <= 10:
            status = "morning_peak"
        elif 17 <= hour_of_day <= 21:
            status = "evening_peak"
        else:
            status = "normal"
            
        return {
            "peak_status": status
        }

peak_hour_service = PeakHourService()
