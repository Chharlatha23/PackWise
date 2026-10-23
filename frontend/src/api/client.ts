import type {
  PackagingRequest,
  RecommendationResponse,
  FeedbackSubmission,
  FeedbackResponse,
  ModelUpdateCandidate
} from '../types/api';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch (e) {
    return false;
  }
}

export async function fetchRecommendation(
  request: PackagingRequest,
  searchEngine?: string
): Promise<RecommendationResponse> {
  const queryParam = searchEngine ? `?search_engine=${encodeURIComponent(searchEngine)}` : '';
  const response = await fetch(`${API_BASE_URL}/api/v1/recommend${queryParam}`, {
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

export async function submitFeedback(submission: FeedbackSubmission): Promise<FeedbackResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(submission),
  });

  if (!response.ok) {
    let errorDetail = 'Failed to submit feedback';
    try {
      const errorData = await response.json();
      errorDetail = errorData.detail || errorDetail;
    } catch (e) {
      errorDetail = `HTTP ${response.status} ${response.statusText}`;
    }
    throw new Error(`Feedback Error: ${errorDetail}`);
  }

  return response.json();
}

export async function fetchAllFeedback(): Promise<FeedbackResponse[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/feedback`);
  if (!response.ok) {
    throw new Error(`Failed to fetch feedback list: HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchModelUpdates(): Promise<ModelUpdateCandidate[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/feedback/model-updates`);
  if (!response.ok) {
    throw new Error(`Failed to fetch model updates: HTTP ${response.status}`);
  }
  return response.json();
}
