const API_URL =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function submitEvaluation(payload) {
  const response = await fetch(
    `${API_URL}/api/evaluation/submit`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    const detail = data?.detail || `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return data;
}
export async function submitBatchEvaluation(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(
    'http://127.0.0.1:8000/api/evaluation/batch',
    {
      method: 'POST',
      body: formData,
    }
  );

  const data = await response.json();

  if (!response.ok) {
    const message =
      data?.detail ||
      'Batch evaluation failed.';

    throw new Error(
      typeof message === 'string'
        ? message
        : JSON.stringify(message)
    );
  }

  return data;
}

async function getJson(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);
  const data = await response.json();

  if (!response.ok) {
    const detail = data?.detail || `HTTP ${response.status}`;
    throw new Error(
      typeof detail === 'string' ? detail : JSON.stringify(detail)
    );
  }

  return data;
}

export async function getEvaluationHistory() {
  return getJson('/api/evaluation/history');
}

export async function getHistoryDetail(evaluationId) {
  return getJson(
    `/api/evaluation/result/${encodeURIComponent(evaluationId)}`
  );
}

export async function getDashboardOverview(filters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, value);
    }
  });

  const query = params.toString();

  return getJson(
    `/api/dashboard/overview${query ? `?${query}` : ''}`
  );
}
