import polyline

def decode_polyline(encoded_polyline: str) -> list:
    """
    Decodes a Google Encoded Polyline string into a list of [lat, lon] pairs.
    """
    try:
        return polyline.decode(encoded_polyline)
    except Exception:
        return []

def simplify_polyline(coords: list, tolerance: float = 0.001) -> list:
    """
    Simplifies a polyline using a basic distance tolerance to reduce vertex count for the frontend.
    """
    if len(coords) < 3:
        return coords
        
    simplified = [coords[0]]
    for i in range(1, len(coords) - 1):
        prev = simplified[-1]
        curr = coords[i]
        
        # Simple euclidean distance check (not true haversine for speed)
        dist = ((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)**0.5
        if dist > tolerance:
            simplified.append(curr)
            
    simplified.append(coords[-1])
    return simplified

def route_bounds(coords: list) -> dict:
    """
    Calculates the bounding box for a given set of coordinates.
    Returns: {"min_lat": X, "max_lat": Y, "min_lon": Z, "max_lon": W}
    """
    if not coords:
        return None
        
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    
    return {
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lon": min(lons),
        "max_lon": max(lons)
    }
