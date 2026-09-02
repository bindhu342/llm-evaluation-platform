const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function submitEvaluation(payload) {
  const response = await fetch(`${API_URL}/api/evaluation/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    // Surface the backend detail message directly
    const detail = data?.detail || `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return data;
}
