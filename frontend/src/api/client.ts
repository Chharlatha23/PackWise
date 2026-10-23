import type { PackagingRequest, RecommendationResponse } from '../types/api';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch (e) {
    return false;
  }
}

export async function fetchRecommendation(request: PackagingRequest): Promise<RecommendationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/recommend`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let errorDetail = 'Unknown error occurred';
    try {
      const errorData = await response.json();
      errorDetail = errorData.detail || errorDetail;
    } catch (e) {
      errorDetail = `HTTP ${response.status} ${response.statusText}`;
    }
    throw new Error(`API Error: ${errorDetail}`);
  }

  return response.json();
}
