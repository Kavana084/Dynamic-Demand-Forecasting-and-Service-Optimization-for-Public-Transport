import client from './client';

export const fetchSystemHealth = async () => {
  const response = await client.get('/api/health');
  return response.data;
};
