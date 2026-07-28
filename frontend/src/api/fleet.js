import client from './client';

export const optimizeFleet = async (data) => {
  const response = await client.post('/api/optimize_fleet', data);
  return response.data;
};
