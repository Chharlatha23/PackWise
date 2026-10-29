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
      if (Array.isArray(errorData.detail)) {
        errorDetail = errorData.detail.map((d: any) => `${d.loc ? d.loc.slice(1).join(".") : "field"}: ${d.msg}`).join("; ");
      } else if (typeof errorData.detail === "object" && errorData.detail !== null) {
        errorDetail = JSON.stringify(errorData.detail);
      } else {
        errorDetail = errorData.detail || errorDetail;
      }
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
      if (Array.isArray(errorData.detail)) {
        errorDetail = errorData.detail.map((d: any) => `${d.loc ? d.loc.slice(1).join(".") : "field"}: ${d.msg}`).join("; ");
      } else if (typeof errorData.detail === "object" && errorData.detail !== null) {
        errorDetail = JSON.stringify(errorData.detail);
      } else {
        errorDetail = errorData.detail || errorDetail;
      }
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

export async function fetchGoogleAuthUrl(): Promise<{ authorization_url: string; state: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/google/login`);
  if (!response.ok) {
    throw new Error('Failed to initiate Google sign in.');
  }
  return response.json();
}

export async function exchangeGoogleCodeForToken(code: string, state?: string): Promise<{ access_token: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/google/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ code, state }),
  });
  if (!response.ok) {
    let errorDetail = 'Failed to verify Google login';
    try {
      const data = await response.json();
      errorDetail = data.detail || errorDetail;
    } catch (e) {
      errorDetail = `HTTP ${response.status} ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function fetchCurrentUser(token: string): Promise<import('../types/api').UserProfile> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  if (!response.ok) {
    throw new Error('Invalid or expired session');
  }
  return response.json();
}

export async function loginWithEmailPassword(email: string, password: string): Promise<{ access_token: string; user: any }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    let errorDetail = 'Login failed';
    try {
      const data = await response.json();
      errorDetail = data.detail || errorDetail;
    } catch (e) {
      errorDetail = `HTTP ${response.status} ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function registerWithEmailPassword(name: string, email: string, password: string): Promise<{ access_token: string; user: any }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name, email, password }),
  });
  if (!response.ok) {
    let errorDetail = 'Registration failed';
    try {
      const data = await response.json();
      errorDetail = data.detail || errorDetail;
    } catch (e) {
      errorDetail = `HTTP ${response.status} ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function forgotPasswordApi(email: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/forgot-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) {
    let errorDetail = 'Request failed';
    try {
      const data = await response.json();
      errorDetail = data.detail || errorDetail;
    } catch (e) {
      errorDetail = `HTTP ${response.status} ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function resetPasswordApi(token: string, newPassword: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/reset-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  if (!response.ok) {
    let errorDetail = 'Reset password failed';
    try {
      const data = await response.json();
      errorDetail = data.detail || errorDetail;
    } catch (e) {
      errorDetail = `HTTP ${response.status} ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function logoutApi(token: string): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
  } catch (e) {
    // Best-effort logout
  }
}

export async function fetchOverviewMetrics(): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/v1/overview`);
  if (!response.ok) {
    throw new Error('Failed to load overview metrics');
  }
  return response.json();
}

export async function fetchPackagingMaterials(): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/materials`);
  if (!response.ok) {
    throw new Error('Failed to load packaging materials');
  }
  return response.json();
}

export async function fetchEvidenceLibrary(limit: number = 50): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/evidence?limit=${limit}`);
  if (!response.ok) {
    throw new Error('Failed to load scientific evidence library');
  }
  return response.json();
}

export async function fetchCommodities(): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/commodities`);
    if (!response.ok) {
      return ['apple', 'durian', 'salmon', 'strawberry'];
    }
    const data = await response.json();
    return Array.isArray(data) ? data : ['apple', 'durian', 'salmon', 'strawberry'];
  } catch (e) {
    return ['apple', 'durian', 'salmon', 'strawberry'];
  }
}


