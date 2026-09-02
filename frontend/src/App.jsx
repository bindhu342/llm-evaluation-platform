import { useState } from 'react';
import { submitEvaluation } from './api';
import './index.css';

// ── Loading steps shown while waiting for the API ────────────────
const LOADING_STEPS = [
  'Evaluating response...',
  'Analyzing relevance...',
  'Checking accuracy...',
  'Detecting hallucinations...',
  'Checking completeness...',
];

// ── Verdict colour map ───────────────────────────────────────────
const VERDICT_COLORS = {
  EXCELLENT: { bg: '#d1fae5', text: '#065f46', border: '#6ee7b7' },
  GOOD:      { bg: '#dbeafe', text: '#1e40af', border: '#93c5fd' },
  FAIR:      { bg: '#fef9c3', text: '#854d0e', border: '#fde047' },
  POOR:      { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' },
};

// ── Score progress bar ───────────────────────────────────────────
function ScoreBar({ value }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.85 ? '#10b981'
              : value >= 0.70 ? '#3b82f6'
              : value >= 0.50 ? '#f59e0b'
              : '#ef4444';
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{
        height: 8, borderRadius: 4, background: '#e5e7eb', overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', width: `${pct}%`, background: color,
          borderRadius: 4, transition: 'width 0.6s ease',
        }} />
      </div>
    </div>
  );
}

// ── Individual score card ────────────────────────────────────────
function ScoreCard({ label, value }) {
  const pct = (value * 100).toFixed(0);
  const color = value >= 0.85 ? '#10b981'
              : value >= 0.70 ? '#3b82f6'
              : value >= 0.50 ? '#f59e0b'
              : '#ef4444';
  return (
    <div style={{
      background: '#fff', borderRadius: 12, padding: '20px 24px',
      boxShadow: '0 1px 4px rgba(0,0,0,0.08)', flex: '1 1 180px',
      minWidth: 160,
    }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </div>
      <div style={{ fontSize: 36, fontWeight: 700, color, marginTop: 6 }}>
        {value.toFixed(2)}
      </div>
      <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 2 }}>{pct}%</div>
      <ScoreBar value={value} />
    </div>
  );
}

// ── Textarea field ───────────────────────────────────────────────
function Field({ label, value, onChange, placeholder, rows = 3, required }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <label style={{ display: 'block', fontWeight: 600, fontSize: 14, marginBottom: 6, color: '#374151' }}>
        {label}{required && <span style={{ color: '#ef4444' }}> *</span>}
      </label>
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        style={{
          width: '100%', padding: '10px 14px', borderRadius: 8,
          border: '1.5px solid #d1d5db', fontSize: 14, lineHeight: 1.6,
          resize: 'vertical', outline: 'none', fontFamily: 'inherit',
          transition: 'border-color 0.2s',
        }}
        onFocus={e => e.target.style.borderColor = '#6366f1'}
        onBlur={e => e.target.style.borderColor = '#d1d5db'}
      />
    </div>
  );
}

// ── Main App ─────────────────────────────────────────────────────
export default function App() {
  const [question, setQuestion]         = useState('');
  const [response, setResponse]         = useState('');
  const [referenceAnswer, setReference] = useState('');
  const [sourceDocument, setSource]     = useState('');

  const [loading, setLoading]           = useState(false);
  const [loadingStep, setLoadingStep]   = useState(0);
  const [result, setResult]             = useState(null);
  const [error, setError]               = useState(null);

  // Cycle through loading messages while waiting
  const startLoadingCycle = () => {
    setLoadingStep(0);
    let step = 0;
    const interval = setInterval(() => {
      step = (step + 1) % LOADING_STEPS.length;
      setLoadingStep(step);
    }, 900);
    return interval;
  };

  const handleSubmit = async () => {
    if (!question.trim() || !response.trim()) return;

    setLoading(true);
    setResult(null);
    setError(null);

    const interval = startLoadingCycle();

    try {
      const data = await submitEvaluation({
        question: question.trim(),
        response: response.trim(),
        reference_answer: referenceAnswer.trim() || null,
        source_document: sourceDocument.trim() || null,
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      clearInterval(interval);
      setLoading(false);
    }
  };

  const canSubmit = question.trim() && response.trim() && !loading;
  const verdict = result?.verdict;
  const vc = VERDICT_COLORS[verdict] || VERDICT_COLORS.FAIR;

  return (
    <div style={{ minHeight: '100vh', background: '#f0f2f5', padding: '32px 16px' }}>

      {/* ── Header ── */}
      <div style={{ maxWidth: 860, margin: '0 auto 28px' }}>
        <div style={{
          background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
          borderRadius: 16, padding: '32px 40px', color: '#fff',
          boxShadow: '0 4px 20px rgba(79,70,229,0.3)',
        }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: '-0.02em' }}>
            🧠 LLM Response Evaluation Platform
          </h1>
          <p style={{ marginTop: 8, opacity: 0.85, fontSize: 15 }}>
            Evaluate AI-generated responses for quality, factuality and hallucination
            using multi-agent LLM-as-a-Judge scoring.
          </p>
        </div>
      </div>

      <div style={{ maxWidth: 860, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* ── Input card ── */}
        <div style={{
          background: '#fff', borderRadius: 16, padding: '32px 36px',
          boxShadow: '0 1px 6px rgba(0,0,0,0.08)',
        }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 24, color: '#111827' }}>
            Evaluation Input
          </h2>

          <Field
            label="Question"
            value={question}
            onChange={setQuestion}
            placeholder='e.g. "What is the capital of France?"'
            rows={2}
            required
          />
          <Field
            label="AI Generated Response"
            value={response}
            onChange={setResponse}
            placeholder='e.g. "The capital of France is Paris."'
            rows={3}
            required
          />
          <Field
            label="Reference Answer"
            value={referenceAnswer}
            onChange={setReference}
            placeholder='e.g. "Paris is the capital of France." (recommended for accuracy evaluation)'
            rows={2}
          />
          <Field
            label="Source Document (optional)"
            value={sourceDocument}
            onChange={setSource}
            placeholder="Paste a reference document or context passage (optional)"
            rows={3}
          />

          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            style={{
              width: '100%', padding: '14px 0', borderRadius: 10,
              background: canSubmit ? 'linear-gradient(135deg, #4f46e5, #7c3aed)' : '#e5e7eb',
              color: canSubmit ? '#fff' : '#9ca3af',
              border: 'none', fontSize: 16, fontWeight: 700,
              cursor: canSubmit ? 'pointer' : 'not-allowed',
              transition: 'all 0.2s', letterSpacing: '0.01em',
              boxShadow: canSubmit ? '0 4px 14px rgba(79,70,229,0.35)' : 'none',
            }}
          >
            {loading ? '⏳ Evaluating...' : '▶  Evaluate Response'}
          </button>
        </div>

        {/* ── Loading state ── */}
        {loading && (
          <div style={{
            background: '#fff', borderRadius: 16, padding: '28px 36px',
            boxShadow: '0 1px 6px rgba(0,0,0,0.08)', textAlign: 'center',
          }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>⚙️</div>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#4f46e5' }}>
              {LOADING_STEPS[loadingStep]}
            </div>
            <div style={{ marginTop: 16, display: 'flex', justifyContent: 'center', gap: 6 }}>
              {LOADING_STEPS.map((_, i) => (
                <div key={i} style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: i === loadingStep ? '#4f46e5' : '#e5e7eb',
                  transition: 'background 0.3s',
                }} />
              ))}
            </div>
          </div>
        )}

        {/* ── Error state ── */}
        {error && !loading && (
          <div style={{
            background: '#fff', borderRadius: 16, padding: '28px 36px',
            boxShadow: '0 1px 6px rgba(0,0,0,0.08)',
            borderLeft: '4px solid #ef4444',
          }}>
            <div style={{ fontSize: 17, fontWeight: 700, color: '#991b1b', marginBottom: 10 }}>
              ⚠️ Evaluation Failed
            </div>
            <p style={{ color: '#374151', fontFamily: 'monospace', fontSize: 13 }}>{error}</p>
          </div>
        )}

        {/* ── Results ── */}
        {result && !loading && (
          <div style={{
            background: '#fff', borderRadius: 16, padding: '32px 36px',
            boxShadow: '0 1px 6px rgba(0,0,0,0.08)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <h2 style={{ fontSize: 17, fontWeight: 700, color: '#111827' }}>
                📊 Evaluation Results
              </h2>
              <button
                type="button"
                onClick={() => { setQuestion(''); setResponse(''); setReference(''); setSource(''); setResult(null); setError(null); }}
                style={{
                  padding: '10px 20px', borderRadius: 8, border: '2px solid #4f46e5',
                  background: '#fff', color: '#4f46e5', fontSize: 14, fontWeight: 700,
                  cursor: 'pointer', fontFamily: 'inherit',
                }}
              >
                🔄 New Evaluation
              </button>
            </div>

            {/* Score cards */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 28 }}>
              <ScoreCard label="Relevance"        value={result.scores.relevance} />
              <ScoreCard label="Accuracy"         value={result.scores.accuracy} />
              <ScoreCard label="Hallucination-Free" value={result.scores.hallucination_free} />
              <ScoreCard label="Completeness"     value={result.scores.completeness} />
            </div>

            {/* Final score + verdict */}
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 28 }}>
              <div style={{
                flex: 1, minWidth: 180, background: '#f9fafb', borderRadius: 12,
                padding: '20px 24px', textAlign: 'center',
                border: '2px solid #e5e7eb',
              }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Final Score
                </div>
                <div style={{ fontSize: 48, fontWeight: 800, color: '#111827', marginTop: 4 }}>
                  {result.final_score.toFixed(2)}
                </div>
                <ScoreBar value={result.final_score} />
              </div>

              <div style={{
                flex: 1, minWidth: 180, borderRadius: 12,
                padding: '20px 24px', textAlign: 'center',
                background: vc.bg, border: `2px solid ${vc.border}`,
              }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: vc.text, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Verdict
                </div>
                <div style={{ fontSize: 40, fontWeight: 800, color: vc.text, marginTop: 4 }}>
                  {verdict}
                </div>
                <div style={{ fontSize: 12, color: vc.text, opacity: 0.75, marginTop: 4 }}>
                  {verdict === 'EXCELLENT' && 'High-quality response across all dimensions'}
                  {verdict === 'GOOD'      && 'Generally reliable with minor issues'}
                  {verdict === 'FAIR'      && 'Acceptable but with notable quality issues'}
                  {verdict === 'POOR'      && 'Significant quality problems detected'}
                </div>
              </div>
            </div>

            {/* Scoring formula breakdown */}
            <div style={{
              background: '#f9fafb', borderRadius: 10, padding: '16px 20px',
              fontSize: 13, color: '#6b7280', marginBottom: 20,
            }}>
              <strong style={{ color: '#374151' }}>Scoring formula: </strong>
              Final = 0.25 × Relevance + 0.30 × Accuracy + 0.25 × Hallucination-Free + 0.20 × Completeness
            </div>

            {/* Agent explanations */}
            {result.explanations && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#374151', marginBottom: 12 }}>
                  Agent Explanations
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {[
                    { key: 'relevance',        label: 'Relevance' },
                    { key: 'accuracy',         label: 'Accuracy' },
                    { key: 'hallucination_free', label: 'Hallucination-Free' },
                    { key: 'completeness',     label: 'Completeness' },
                  ].map(({ key, label }) => (
                    result.explanations[key] && (
                      <div key={key} style={{
                        background: '#f9fafb', borderRadius: 8,
                        padding: '12px 16px', fontSize: 13,
                      }}>
                        <span style={{ fontWeight: 600, color: '#4f46e5' }}>{label}: </span>
                        <span style={{ color: '#374151' }}>{result.explanations[key]}</span>
                      </div>
                    )
                  ))}
                </div>
              </div>
            )}

            {/* Evaluation ID */}
            <div style={{ fontSize: 12, color: '#9ca3af' }}>
              Evaluation ID: <code style={{ fontFamily: 'monospace' }}>{result.id}</code>
            </div>
          </div>
        )}

        {/* ── Demo hint ── */}
        {!result && !loading && !error && (
          <div style={{
            background: '#fff', borderRadius: 16, padding: '24px 36px',
            boxShadow: '0 1px 6px rgba(0,0,0,0.08)',
            borderLeft: '4px solid #6366f1',
          }}>
            <div style={{ fontWeight: 700, color: '#4f46e5', marginBottom: 10 }}>
              💡 Demo Test Cases
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                {
                  label: 'Case 1 — Correct Answer',
                  q: 'What is the capital of France?',
                  r: 'The capital of France is Paris.',
                  ref: 'Paris is the capital of France.',
                  note: 'Expected: high scores across all dimensions',
                },
                {
                  label: 'Case 2 — Incorrect Answer',
                  q: 'What is the capital of France?',
                  r: 'The capital of France is Berlin.',
                  ref: 'Paris is the capital of France.',
                  note: 'Expected: low accuracy and hallucination-free scores',
                },
                {
                  label: 'Case 3 — Incomplete Answer',
                  q: 'What are the three branches of the US government and the role of each?',
                  r: 'One branch is Congress, which makes laws.',
                  ref: 'Legislative (Congress — makes laws), Executive (President — enforces laws), Judicial (Supreme Court — interprets laws).',
                  note: 'Expected: lower completeness score',
                },
              ].map(({ label, q, r, ref, note }) => (
                <button
                  key={label}
                  type="button"
                  className="demo-card"
                  onClick={() => { setQuestion(q); setResponse(r); setReference(ref); setSource(''); setResult(null); setError(null); }}
                  style={{ width: '100%', textAlign: 'left', fontFamily: 'inherit' }}
                >
                  <div style={{ fontWeight: 600, fontSize: 13, color: '#4f46e5' }}>{label}</div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{note}</div>
                  <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 2 }}>Click to load →</div>
                </button>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* ── Footer ── */}
      <div style={{ textAlign: 'center', marginTop: 40, fontSize: 12, color: '#9ca3af' }}>
        LLM Evaluation Platform · Infosys Springboard Virtual Internship 7.0
      </div>
    </div>
  );
}
