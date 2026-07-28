import httpx
from typing import Dict, Any, List
from fastapi import HTTPException
from app.logger import app_logger

OTP_BASE_URL = "http://localhost:8080/otp/routers/default/plan"

class OTPMappingService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_plan(self, from_lat: float, from_lon: float, to_lat: float, to_lon: float, date: str = None, time: str = None) -> Dict[str, Any]:
        """
        Communicates with the local OTP REST API to fetch a journey plan.
        """
        params = {
            "fromPlace": f"{from_lat},{from_lon}",
            "toPlace": f"{to_lat},{to_lon}",
            "mode": "TRANSIT,WALK",
            "maxWalkDistance": 800
        }
        
        if date:
            params["date"] = date
        if time:
            params["time"] = time

        try:
            response = await self.client.get(OTP_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "plan" not in data or "itineraries" not in data["plan"]:
                raise HTTPException(status_code=404, detail="No route found by OTP")
                
            return data
            
        except httpx.TimeoutException:
            app_logger.error("OTP Mapping Service timeout.")
            raise HTTPException(status_code=504, detail="OTP Engine Timeout")
        except httpx.HTTPStatusError as e:
            app_logger.error(f"OTP API Error: {str(e)}")
            raise HTTPException(status_code=502, detail="Error communicating with OTP Engine")
        except Exception as e:
            app_logger.error(f"OTP mapping service failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal OTP Mapping Error")

otp_mapping_service = OTPMappingService()
