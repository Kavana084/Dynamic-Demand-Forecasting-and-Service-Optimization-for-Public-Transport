import client from './client';

export const predictDemand = async (data) => {
  const response = await client.post('/api/predict_demand', data);
  return response.data;
};
