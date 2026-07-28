import client from './client';

const STATIC_CACHE_DURATION_MS = 5 * 60 * 1000; // 5 minutes (for static GTFS stops only)
let locationsCache = {
  data: null,
  timestamp: null
};

export const fetchLocations = async () => {
  const now = Date.now();
  
  // Return cached data if valid
  if (locationsCache.data && locationsCache.timestamp && (now - locationsCache.timestamp < STATIC_CACHE_DURATION_MS)) {
    return locationsCache.data;
  }

  try {
    const response = await client.get('/routes/meta');
    let fetchedLocations = [];
    
    if (response.data.locations) {
      fetchedLocations = response.data.locations;
    } else if (response.data.routes) {
      const allStops = response.data.routes.flatMap(route => route.stops || []);
      fetchedLocations = [...new Set(allStops)];
    }

    if (fetchedLocations.length > 0) {
      locationsCache = {
        data: fetchedLocations,
        timestamp: now
      };
      return fetchedLocations;
    }
    
    throw new Error('Empty response format');
  } catch (err) {
    console.error('API /routes/meta failed:', err);
    
    // Return stale cache if available
    if (locationsCache.data) {
      console.info('Serving stale cached data.');
      return locationsCache.data;
    }
    
    // No fallback data - let the caller handle the error
    throw err;
  }
};

export const planTrip = async (data) => {
  const response = await client.post('/plan_trip', data);
  return response.data;
};
