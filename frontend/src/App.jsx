import { useEffect, useMemo, useState } from 'react';
import {
  submitEvaluation,
  submitBatchEvaluation,
  getEvaluationHistory,
  getHistoryDetail,
  getDashboardOverview,
} from './api';
import './index.css';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
const LOADING_STEPS = [
  'Evaluating response...',
  'Analyzing relevance...',
  'Checking accuracy...',
  'Detecting hallucinations...',
  'Checking completeness...',
  'Calculating final verdict...',
];

const VERDICT_META = {
  PASS: {
    tone: 'success',
    label: 'PASS',
    summary: 'The response meets the configured quality threshold.',
    icon: '✓',
  },
  NEEDS_IMPROVEMENT: {
    tone: 'warning',
    label: 'NEEDS IMPROVEMENT',
    summary: 'The response has quality issues that should be reviewed.',
    icon: '!',
  },
  FAIL: {
    tone: 'danger',
    label: 'FAIL',
    summary: 'Critical response quality problems were detected.',
    icon: '×',
  },
};

const DIMENSIONS = [
  {
    key: 'relevance',
    label: 'Relevance',
    description: 'Alignment with the user question',
    icon: '↗',
  },
  {
    key: 'accuracy',
    label: 'Accuracy',
    description: 'Factual correctness of the answer',
    icon: '✓',
  },
  {
    key: 'hallucination_free',
    label: 'Hallucination-free',
    description: 'Freedom from unsupported claims',
    icon: '◌',
  },
  {
    key: 'completeness',
    label: 'Completeness',
    description: 'Coverage of the expected answer',
    icon: '◒',
  },
];

function Icon({ children, className = '' }) {
  return (
    <span className={`icon ${className}`} aria-hidden="true">
      {children}
    </span>
  );
}

function scoreValue(value) {
  const numeric = Number(value);

  return Number.isFinite(numeric)
    ? Math.max(0, Math.min(1, numeric))
    : 0;
}

function scoreTone(value) {
  if (value >= 0.85) return 'success';
  if (value >= 0.7) return 'info';
  if (value >= 0.5) return 'warning';
  return 'danger';
}

function ScoreBar({ value }) {
  const safeValue = scoreValue(value);

  return (
    <div
      className="score-track"
      aria-label={`${Math.round(safeValue * 100)} percent`}
    >
      <div
        className={`score-fill ${scoreTone(safeValue)}`}
        style={{ width: `${safeValue * 100}%` }}
      />
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  rows = 4,
  required = false,
  hint,
}) {
  return (
    <label className="field">
      <span className="field-label">
        {label} {required && <span className="required">*</span>}
      </span>

      {hint && <span className="field-hint">{hint}</span>}

      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows={rows}
        required={required}
      />

      <span className="character-count">
        {value.length > 0 ? `${value.length} characters` : 'Ready for input'}
      </span>
    </label>
  );
}

function ScoreCard({ dimension, value }) {
  const safeValue = scoreValue(value);
  const percentage = Math.round(safeValue * 100);

  return (
    <article className="score-card">
      <div className="score-card-top">
        <div className={`metric-icon ${scoreTone(safeValue)}`}>
          <Icon>{dimension.icon}</Icon>
        </div>

        <span className="metric-status">
          {percentage >= 70 ? 'Strong' : percentage >= 50 ? 'Review' : 'Low'}
        </span>
      </div>

      <div className="metric-label">{dimension.label}</div>

      <div className="metric-value-row">
        <strong>{safeValue.toFixed(2)}</strong>
        <span>{percentage}%</span>
      </div>

      <ScoreBar value={safeValue} />

      <p>{dimension.description}</p>
    </article>
  );
}

function QualityRadar({ scores = {} }) {
  const values = DIMENSIONS.map((dimension) =>
    scoreValue(scores[dimension.key])
  );

  const center = 110;
  const radius = 78;

  const angles = values.map(
    (_, index) =>
      -Math.PI / 2 +
      (index * Math.PI * 2) / values.length
  );

  const point = (angle, distance) =>
    `${center + Math.cos(angle) * distance},${
      center + Math.sin(angle) * distance
    }`;

  const grid = [1, 0.75, 0.5, 0.25].map((level) =>
    angles
      .map((angle) => point(angle, radius * level))
      .join(' ')
  );

  const dataPoints = values
    .map((value, index) =>
      point(
        angles[index],
        radius * value
      )
    )
    .join(' ');

  return (
    <section className="quality-graph analysis-panel">
      <div className="analysis-heading">
        <div>
          <span className="section-kicker">
            LIVE SCORE MAP
          </span>

          <h2>Quality signal</h2>
        </div>

        <span className="analysis-caption">
          Four-dimensional view
        </span>
      </div>

      <div className="radar-layout">
        <div
          className="radar-chart"
          aria-label="Quality score radar graph"
        >
          <svg
            viewBox="0 0 220 220"
            role="img"
          >
            <defs>
              <linearGradient
                id="radar-fill"
                x1="0"
                x2="1"
                y1="0"
                y2="1"
              >
                <stop
                  offset="0%"
                  stopColor="#36c9b5"
                  stopOpacity="0.38"
                />

                <stop
                  offset="100%"
                  stopColor="#65b4ed"
                  stopOpacity="0.08"
                />
              </linearGradient>
            </defs>

            {grid.map((points, index) => (
              <polygon
                key={index}
                points={points}
                className="radar-grid"
              />
            ))}

            {angles.map((angle, index) => (
              <line
                key={index}
                x1={center}
                y1={center}
                x2={
                  center +
                  Math.cos(angle) *
                    radius
                }
                y2={
                  center +
                  Math.sin(angle) *
                    radius
                }
                className="radar-axis"
              />
            ))}

            <polygon
              points={dataPoints}
              className="radar-data"
            />

            {values.map((value, index) => (
              <circle
                key={index}
                cx={
                  center +
                  Math.cos(angles[index]) *
                    radius *
                    value
                }
                cy={
                  center +
                  Math.sin(angles[index]) *
                    radius *
                    value
                }
                r="4"
                className="radar-point"
              />
            ))}
          </svg>
        </div>

        <div className="radar-legend">
          {DIMENSIONS.map(
            (dimension, index) => (
              <div
                className="radar-legend-item"
                key={dimension.key}
              >
                <span
                  className={`radar-dot ${scoreTone(
                    values[index]
                  )}`}
                />

                <span>
                  {dimension.label}
                </span>

                <strong>
                  {Math.round(
                    values[index] * 100
                  )}
                  %
                </strong>
              </div>
            )
          )}
        </div>
      </div>
    </section>
  );
}

function AgentPipeline({ activeStep }) {
  const steps = [
    'INPUT',
    'RELEVANCE',
    'ACCURACY',
    'HALLUCINATION',
    'COMPLETENESS',
    'VERDICT',
  ];

  return (
    <div
      className="agent-pipeline"
      aria-label="Evaluation agent pipeline"
    >
      {steps.map((step, index) => (
        <div
          className={`pipeline-node ${
            index < activeStep
              ? 'complete'
              : ''
          } ${
            index === activeStep
              ? 'current'
              : ''
          }`}
          key={step}
        >
          <span className="pipeline-node-icon">
            {index < activeStep
              ? '✓'
              : index === activeStep
                ? '◌'
                : String(index + 1).padStart(
                    2,
                    '0'
                  )}
          </span>

          <span>{step}</span>

          {index < steps.length - 1 && (
            <i className="pipeline-connector" />
          )}
        </div>
      ))}
    </div>
  );
}

function CompletenessAnalysis({
  analysis,
  score,
}) {
  if (!analysis) return null;

  const addressed = Array.isArray(
    analysis.addressed_aspects
  )
    ? analysis.addressed_aspects
    : [];

  const missing = Array.isArray(
    analysis.missing_aspects
  )
    ? analysis.missing_aspects
    : [];

  return (
    <section className="analysis-panel completeness-panel">
      <div className="analysis-heading">
        <div>
          <span className="section-kicker">
            05 / COVERAGE ANALYSIS
          </span>

          <h2>Completeness Analysis</h2>
        </div>

        <span className="analysis-caption">
          Requirement coverage
        </span>
      </div>

      {analysis.explanation && (
        <p className="analysis-main-explanation">
          {analysis.explanation}
        </p>
      )}

      <div className="coverage-meter">
        <div className="coverage-meter-heading">
          <span>Coverage signal</span>

          <strong>
            {Math.round(
              scoreValue(score) * 100
            )}
            %
          </strong>
        </div>

        <div className="coverage-meter-track">
          <div
            className="coverage-meter-fill"
            style={{
              width: `${
                scoreValue(score) * 100
              }%`,
            }}
          />
        </div>

        <div className="coverage-meter-meta">
          <span>
            Addressed: {addressed.length}
          </span>

          <span>
            Missing: {missing.length}
          </span>
        </div>
      </div>

      <div className="coverage-grid">
        <div className="coverage-column addressed">
          <div className="coverage-heading">
            <span className="coverage-icon">
              ✓
            </span>

            <div>
              <strong>
                Addressed aspects
              </strong>

              <small>
                Requirements covered by the
                response
              </small>
            </div>
          </div>

          {addressed.length > 0 ? (
            <ul>
              {addressed.map(
                (item, index) => (
                  <li
                    key={`${item}-${index}`}
                  >
                    <span>✓</span>
                    {item}
                  </li>
                )
              )}
            </ul>
          ) : (
            <div className="empty-coverage">
              No addressed aspects were
              identified.
            </div>
          )}
        </div>

        <div className="coverage-column missing">
          <div className="coverage-heading">
            <span className="coverage-icon">
              !
            </span>

            <div>
              <strong>
                Missing aspects
              </strong>

              <small>
                Requirements not sufficiently
                addressed
              </small>
            </div>
          </div>

          {missing.length > 0 ? (
            <ul>
              {missing.map(
                (item, index) => (
                  <li
                    key={`${item}-${index}`}
                  >
                    <span>!</span>
                    {item}
                  </li>
                )
              )}
            </ul>
          ) : (
            <div className="empty-coverage success-empty">
              No missing aspects identified.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function HallucinationAnalysis({
  analysis,
}) {
  if (!analysis) return null;

  const status = String(
    analysis.status || 'unknown'
  ).toLowerCase();

  const statusLabel =
    status === 'supported'
      ? 'Supported'
      : status === 'contradicted'
        ? 'Contradicted'
        : status ===
            'partially_supported'
          ? 'Partially supported'
          : status === 'unsupported'
            ? 'Unsupported'
            : 'Needs review';

  const statusTone =
    status === 'supported'
      ? 'success'
      : status === 'contradicted' ||
          status === 'unsupported'
        ? 'danger'
        : 'warning';

  const flaggedClaims = Array.isArray(
    analysis.flagged_claims
  )
    ? analysis.flagged_claims
    : [];

  return (
    <section className="analysis-panel hallucination-panel">
      <div className="analysis-heading">
        <div>
          <span className="section-kicker">
            04 / CLAIM VALIDATION
          </span>

          <h2>Hallucination Analysis</h2>
        </div>

        <span
          className={`hallucination-status ${statusTone}`}
        >
          {statusLabel}
        </span>
      </div>

      {analysis.explanation && (
        <p className="analysis-main-explanation">
          {analysis.explanation}
        </p>
      )}

      {flaggedClaims.length > 0 ? (
        <div className="claim-list">
          {flaggedClaims.map(
            (item, index) => (
              <article
                className="claim-card"
                key={`${item.claim}-${index}`}
              >
                <div className="claim-card-header">
                  <span className="claim-number">
                    Claim{' '}
                    {String(index + 1).padStart(
                      2,
                      '0'
                    )}
                  </span>

                  <span className="claim-label">
                    Review required
                  </span>
                </div>

                <div className="claim-section">
                  <strong>Claim</strong>

                  <p>
                    {item.claim ||
                      'No claim provided.'}
                  </p>
                </div>

                {item.reason && (
                  <div className="claim-section">
                    <strong>
                      Why it was flagged
                    </strong>

                    <p>{item.reason}</p>
                  </div>
                )}

                {item.evidence && (
                  <div className="claim-section evidence-section">
                    <strong>
                      Supporting evidence
                    </strong>

                    <p>{item.evidence}</p>
                  </div>
                )}
              </article>
            )
          )}
        </div>
      ) : (
        <div className="no-claims-message">
          <span>✓</span>

          <p>
            No unsupported or contradicted
            claims were identified.
          </p>
        </div>
      )}
    </section>
  );
}

function BatchAnalyticsVisual({
  stats,
}) {
  const dimensions = [
    [
      'Relevance',
      stats.average_relevance,
    ],
    [
      'Accuracy',
      stats.average_accuracy,
    ],
    [
      'Hallucination-free',
      stats.average_hallucination_free,
    ],
    [
      'Completeness',
      stats.average_completeness,
    ],
  ];

  const verdicts = [
    [
      'PASS',
      stats.pass_count,
      'success',
    ],
    [
      'NEEDS IMPROVEMENT',
      stats.needs_improvement_count,
      'warning',
    ],
    [
      'FAIL',
      stats.fail_count,
      'danger',
    ],
  ];

  const totalVerdicts =
    verdicts.reduce(
      (sum, [, value]) =>
        sum + Number(value || 0),
      0
    );

  return (
    <div className="batch-visuals">
      <div className="batch-chart-card">
        <div className="batch-chart-heading">
          <span className="section-kicker">
            DIMENSION COMPARISON
          </span>

          <small>Average score</small>
        </div>

        <div className="dimension-bars">
          {dimensions.map(
            ([label, value]) => {
              const safeValue =
                scoreValue(value);

              return (
                <div
                  className="dimension-bar-row"
                  key={label}
                >
                  <span>{label}</span>

                  <div className="dimension-bar-track">
                    <div
                      className="dimension-bar-fill"
                      style={{
                        width: `${
                          safeValue * 100
                        }%`,
                      }}
                    />
                  </div>

                  <strong>
                    {safeValue.toFixed(2)}
                  </strong>
                </div>
              );
            }
          )}
        </div>
      </div>

      <div className="batch-chart-card verdict-chart-card">
        <div className="batch-chart-heading">
          <span className="section-kicker">
            VERDICT DISTRIBUTION
          </span>

          <small>
            {totalVerdicts} evaluated
          </small>
        </div>

        <div className="verdict-bars">
          {verdicts.map(
            ([label, value, tone]) => {
              const count = Number(
                value || 0
              );

              const width =
                totalVerdicts
                  ? (count /
                      totalVerdicts) *
                    100
                  : 0;

              return (
                <div
                  className="verdict-bar-row"
                  key={label}
                >
                  <div>
                    <span
                      className={`verdict-bar-dot ${tone}`}
                    />

                    <span>{label}</span>

                    <strong>{count}</strong>
                  </div>

                  <div className="verdict-bar-track">
                    <div
                      className={`verdict-bar-fill ${tone}`}
                      style={{
                        width: `${width}%`,
                      }}
                    />
                  </div>
                </div>
              );
            }
          )}
        </div>
      </div>
    </div>
  );
}

function ConsolidatedSummary({
  result,
}) {
  if (!result) return null;

  const score = scoreValue(
    result.final_score
  );

  const verdict = String(
    result.verdict || ''
  ).toUpperCase();

  let message;

  if (verdict === 'PASS') {
    message =
      'The evaluated response achieved the required overall quality threshold across relevance, accuracy, hallucination-free content, and completeness.';
  } else if (
    verdict === 'NEEDS_IMPROVEMENT'
  ) {
    message =
      'The response addresses the task but contains quality gaps that should be reviewed before being considered fully reliable.';
  } else {
    message =
      'The response contains significant quality problems. Accuracy or hallucination issues may require correction before the response can be trusted.';
  }

  return (
    <section className="analysis-panel consolidated-panel">
      <div className="analysis-heading">
        <div>
          <span className="section-kicker">
            06 / CONSOLIDATED RESULT
          </span>

          <h2>Evaluation Summary</h2>
        </div>

        <span className="analysis-caption">
          Weighted score:{' '}
          {score.toFixed(2)}
        </span>
      </div>

      <div className="consolidated-content">
        <div
          className={`summary-indicator ${scoreTone(
            score
          )}`}
        >
          {verdict === 'PASS'
            ? '✓'
            : verdict === 'FAIL'
              ? '×'
              : '!'}
        </div>

        <div>
          <strong>
            {verdict === 'PASS'
              ? 'Response meets quality requirements'
              : verdict === 'FAIL'
                ? 'Response requires correction'
                : 'Response requires review'}
          </strong>

          <p>{message}</p>
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   M3.4 - BATCH RESULTS
   ========================================================= */

function BatchResults({
  batchResult,
  selectedBatchItem,
  setSelectedBatchItem,
  onDownloadBatchPdf,
}) {
  if (!batchResult) return null;

  const stats =
    batchResult.statistics || {};

  const getVerdictClass = (
    verdict
  ) => {
    const value = String(
      verdict || ''
    ).toUpperCase();

    if (value === 'PASS')
      return 'batch-pass';

    if (
      value === 'NEEDS_IMPROVEMENT'
    ) {
      return 'batch-warning';
    }

    return 'batch-fail';
  };

  return (
    <section className="batch-results-panel">
      <div className="batch-section-heading">
        <div>
          <span className="section-kicker">
            BATCH RESULTS
          </span>

          <h2>Evaluation overview</h2>
        </div>

        <div
          style={{
            display: 'flex',
            gap: '10px',
            alignItems: 'center',
          }}
        >
          <button
            type="button"
            className="secondary-button"
            onClick={onDownloadBatchPdf}
          >
            <Icon>↓</Icon>
            Download Batch PDF
          </button>

          <span
            className={`batch-status batch-${batchResult.status}`}
          >
            {String(
              batchResult.status || ''
            ).replaceAll('_', ' ')}
          </span>
        </div>
      </div>

      <div className="batch-stat-grid">
        <div className="batch-stat">
          <span>Total rows</span>

          <strong>
            {batchResult.total_rows}
          </strong>
        </div>

        <div className="batch-stat">
          <span>Completed</span>

          <strong>
            {batchResult.completed_rows}
          </strong>
        </div>

        <div className="batch-stat">
          <span>Failed</span>

          <strong>
            {batchResult.failed_rows}
          </strong>
        </div>

        <div className="batch-stat">
          <span>Invalid</span>

          <strong>
            {batchResult.invalid_rows}
          </strong>
        </div>
      </div>

      <div className="batch-analytics">
        <div className="batch-analytics-card">
          <span>Average relevance</span>

          <strong>
            {Number(
              stats.average_relevance || 0
            ).toFixed(2)}
          </strong>
        </div>

        <div className="batch-analytics-card">
          <span>Average accuracy</span>

          <strong>
            {Number(
              stats.average_accuracy || 0
            ).toFixed(2)}
          </strong>
        </div>

        <div className="batch-analytics-card">
          <span>
            Average hallucination-free
          </span>

          <strong>
            {Number(
              stats.average_hallucination_free ||
                0
            ).toFixed(2)}
          </strong>
        </div>

        <div className="batch-analytics-card">
          <span>
            Average completeness
          </span>

          <strong>
            {Number(
              stats.average_completeness ||
                0
            ).toFixed(2)}
          </strong>
        </div>

        <div className="batch-analytics-card">
          <span>
            Average final score
          </span>

          <strong>
            {Number(
              stats.average_final_score ||
                0
            ).toFixed(2)}
          </strong>
        </div>

        <div className="batch-analytics-card">
          <span>Hallucination cases</span>

          <strong>
            {stats.hallucination_count ||
              0}
          </strong>
        </div>
      </div>

      <BatchAnalyticsVisual
        stats={stats}
      />

      <div className="batch-verdict-summary">
        <div>
          <span>PASS</span>

          <strong>
            {stats.pass_count || 0}
          </strong>
        </div>

        <div>
          <span>NEEDS IMPROVEMENT</span>

          <strong>
            {stats.needs_improvement_count ||
              0}
          </strong>
        </div>

        <div>
          <span>FAIL</span>

          <strong>
            {stats.fail_count || 0}
          </strong>
        </div>
      </div>

      {batchResult.invalid_row_details
        ?.length > 0 && (
        <div className="batch-invalid-box">
          <strong>Invalid rows</strong>

          {batchResult.invalid_row_details.map(
            (item) => (
              <div key={item.row_number}>
                Row {item.row_number}:{' '}
                {item.error}
              </div>
            )
          )}
        </div>
      )}

      <div className="batch-table-wrapper">
        <table className="batch-table">
          <thead>
            <tr>
              <th>Row</th>
              <th>Question</th>
              <th>Response</th>
              <th>Relevance</th>
              <th>Accuracy</th>
              <th>
                Hallucination-free
              </th>
              <th>Completeness</th>
              <th>Overall</th>
              <th>Verdict</th>
            </tr>
          </thead>

          <tbody>
            {batchResult.results?.map(
              (item) => {
                const itemResult =
                  item.result;

                return (
                  <tr
                    key={item.row_number}
                    className={
                      selectedBatchItem?.row_number ===
                      item.row_number
                        ? 'selected-batch-row'
                        : ''
                    }
                    onClick={() =>
                      setSelectedBatchItem(
                        item
                      )
                    }
                  >
                    <td>
                      {item.row_number}
                    </td>

                    <td className="batch-question-cell">
                      {item.question ||
                        '—'}
                    </td>

                    <td className="batch-response-cell">
                      {item.response ||
                        '—'}
                    </td>

                    <td>
                      {itemResult
                        ? Number(
                            itemResult
                              .scores
                              ?.relevance ||
                              0
                          ).toFixed(2)
                        : '—'}
                    </td>

                    <td>
                      {itemResult
                        ? Number(
                            itemResult
                              .scores
                              ?.accuracy ||
                              0
                          ).toFixed(2)
                        : '—'}
                    </td>

                    <td>
                      {itemResult
                        ? Number(
                            itemResult
                              .scores
                              ?.hallucination_free ||
                              0
                          ).toFixed(2)
                        : '—'}
                    </td>

                    <td>
                      {itemResult
                        ? Number(
                            itemResult
                              .scores
                              ?.completeness ||
                              0
                          ).toFixed(2)
                        : '—'}
                    </td>

                    <td>
                      {itemResult
                        ? Number(
                            itemResult.final_score ||
                              0
                          ).toFixed(2)
                        : '—'}
                    </td>

                    <td>
                      <span
                        className={`batch-verdict ${getVerdictClass(
                          itemResult?.verdict
                        )}`}
                      >
                        {itemResult?.verdict ||
                          String(
                            item.status ||
                              ''
                          ).replaceAll(
                            '_',
                            ' '
                          )}
                      </span>
                    </td>
                  </tr>
                );
              }
            )}
          </tbody>
        </table>
      </div>

      {selectedBatchItem && (
        <div className="batch-detail-panel">
          <div className="batch-section-heading">
            <div>
              <span className="section-kicker">
                ROW{' '}
                {String(
                  selectedBatchItem.row_number
                ).padStart(2, '0')}
              </span>

              <h2>
                Detailed evaluation
              </h2>
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={() =>
                setSelectedBatchItem(
                  null
                )
              }
            >
              Close
            </button>
          </div>

          {selectedBatchItem.result ? (
            <>
              <div className="batch-detail-content">
                <div>
                  <strong>
                    Question
                  </strong>

                  <p>
                    {
                      selectedBatchItem.question
                    }
                  </p>
                </div>

                <div>
                  <strong>
                    AI Response
                  </strong>

                  <p>
                    {
                      selectedBatchItem.response
                    }
                  </p>
                </div>
              </div>

              <div className="batch-detail-analysis">
                {Object.entries(
                  selectedBatchItem.result
                    .explanations || {}
                ).map(
                  ([key, explanation]) => (
                    <article key={key}>
                      <span>
                        {key.replaceAll(
                          '_',
                          ' '
                        )}
                      </span>

                      <p>
                        {explanation}
                      </p>
                    </article>
                  )
                )}
              </div>

              {selectedBatchItem.result
                .hallucination_analysis && (
                <div className="batch-detail-box">
                  <strong>
                    Hallucination analysis
                  </strong>

                  <p>
                    {
                      selectedBatchItem
                        .result
                        .hallucination_analysis
                        .explanation
                    }
                  </p>

                  {selectedBatchItem
                    .result
                    .hallucination_analysis
                    .flagged_claims
                    ?.length > 0 && (
                    <ul>
                      {selectedBatchItem
                        .result
                        .hallucination_analysis
                        .flagged_claims.map(
                          (
                            claim,
                            index
                          ) => (
                            <li
                              key={index}
                            >
                              <strong>
                                {
                                  claim.claim
                                }
                              </strong>

                              <span>
                                {
                                  claim.reason
                                }
                              </span>
                            </li>
                          )
                        )}
                    </ul>
                  )}
                </div>
              )}

              {selectedBatchItem.result
                .completeness_analysis && (
                <div className="batch-detail-box">
                  <strong>
                    Completeness analysis
                  </strong>

                  <p>
                    {
                      selectedBatchItem
                        .result
                        .completeness_analysis
                        .explanation
                    }
                  </p>

                  {selectedBatchItem
                    .result
                    .completeness_analysis
                    .missing_aspects
                    ?.length > 0 && (
                    <ul>
                      {selectedBatchItem
                        .result
                        .completeness_analysis
                        .missing_aspects.map(
                          (
                            item,
                            index
                          ) => (
                            <li
                              key={index}
                            >
                              {item}
                            </li>
                          )
                        )}
                    </ul>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="batch-failed-detail">
              <strong>
                Evaluation failed
              </strong>

              <p>
                {selectedBatchItem.error ||
                  'No result available.'}
              </p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function HistoryView({ onOpen }) {
  const [items, setItems] = useState(
    []
  );

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState(null);

  const [query, setQuery] =
    useState('');

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);

      const data =
        await getEvaluationHistory();

      setItems(
        Array.isArray(data)
          ? data
          : data?.items ||
              data?.history ||
              []
      );
    } catch (err) {
      setError(
        err.message ||
          'Unable to load evaluation history.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const filteredItems =
    useMemo(() => {
      const value =
        query.trim().toLowerCase();

      return items.filter(
        (item) =>
          !value ||
          JSON.stringify(item)
            .toLowerCase()
            .includes(value)
      );
    }, [items, query]);

  return (
    <section className="history-page">
      <div className="history-heading">
        <div>
          <span className="section-kicker">
            03 / HISTORY
          </span>

          <h2>Evaluation history</h2>

          <p>
            Browse previous evaluations and
            reopen their detailed analysis.
          </p>
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={loadHistory}
        >
          ↻ Refresh
        </button>
      </div>

      <div className="history-toolbar">
        <input
          className="history-search-input"
          value={query}
          onChange={(event) =>
            setQuery(event.target.value)
          }
          placeholder="Search evaluations..."
          aria-label="Search evaluations"
        />
      </div>

      {loading ? (
        <div className="history-state">
          <div className="history-loader" />

          Loading evaluation history...
        </div>
      ) : error ? (
        <div className="history-state history-error-state">
          {error}
        </div>
      ) : filteredItems.length ===
        0 ? (
        <div className="history-state">
          No evaluations found.
        </div>
      ) : (
        <div className="history-list">
          {filteredItems.map(
            (item, index) => {
              const id =
                item.id ||
                item.evaluation_id ||
                item.history_id ||
                item.batch_id;

              const isBatch =
                Boolean(item?.batch_id) ||
                Array.isArray(item?.results) ||
                Boolean(item?.statistics) ||
                String(
                  item?.type || ''
                ).toUpperCase() === 'BATCH';

              const verdict = String(
                item.verdict ||
                  item.final_verdict ||
                  'UNKNOWN'
              ).replaceAll(
                '_',
                ' '
              );

              const score =
                item.final_score ??
                item.score ??
                item.overall_score;

              return (
                <button
                  type="button"
                  className="history-card"
                  key={id || index}
                  onClick={() =>
                    onOpen(id)
                  }
                >
                  <span className="history-card-content">
                    <span className="history-card-topline">
                      <span className="history-type">
                        {item.type ||
                          (item.batch_id
                            ? 'BATCH'
                            : 'SINGLE')}
                      </span>

                      <span className="history-date">
                        {item.created_at ||
                          item.timestamp ||
                          ''}
                      </span>
                    </span>

                    <strong>
                      {item.question ||
                        item.title ||
                        `Evaluation ${
                          index + 1
                        }`}
                    </strong>

                    <small>
                      {item.response ||
                        item.description ||
                        'Open detailed evaluation analysis.'}
                    </small>
                  </span>

                  <span
                    className={`history-result ${scoreTone(
                      score
                    )}`}
                  >
                    {isBatch ? (
                      'OPEN BATCH →'
                    ) : Number.isFinite(
                      Number(score)
                    )
                      ? scoreValue(
                          score
                        ).toFixed(2)
                      : verdict}
                  </span>
                </button>
              );
            }
          )}
        </div>
      )}
    </section>
  );
}



function InteractiveVerdictChart({ stats }) {
  const verdicts = stats?.verdicts || {};

  const data = [
    {
      name: 'PASS',
      value: verdicts.pass ?? 0,
    },
    {
      name: 'NEEDS IMPROVEMENT',
      value: verdicts.needs_improvement ?? 0,
    },
    {
      name: 'FAIL',
      value: verdicts.fail ?? 0,
    },
  ];

  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="dashboard-chart-card">
      <div className="dashboard-chart-header">
        <div>
          <span className="dashboard-chart-eyebrow">
            VERDICT ANALYTICS
          </span>

          <h3>Evaluation outcomes</h3>

          <p>
            Interactive distribution of evaluation verdicts.
          </p>
        </div>

        <div className="dashboard-chart-total">
          <strong>{total}</strong>
          <span>Total</span>
        </div>
      </div>

      <div className="dashboard-chart-container">
        <ResponsiveContainer width="100%" height={320}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={80}
              outerRadius={120}
              paddingAngle={4}
              animationDuration={900}
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={
                    index === 0
                      ? '#22c55e'
                      : index === 1
                        ? '#f59e0b'
                        : '#ef4444'
                  }
                />
              ))}
            </Pie>

            <Tooltip
              formatter={(value, name) => [
                value,
                name,
              ]}
            />

            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}


function InteractiveQualityChart({ stats }) {
  const scores = stats?.average_scores || {};

  const data = [
    {
      name: 'Relevance',
      score: scores.relevance ?? 0,
    },
    {
      name: 'Accuracy',
      score: scores.accuracy ?? 0,
    },
    {
      name: 'Hallucination-free',
      score: scores.hallucination_free ?? 0,
    },
    {
      name: 'Completeness',
      score: scores.completeness ?? 0,
    },
  ];

  return (
    <div className="dashboard-chart-card">
      <div className="dashboard-chart-header">
        <div>
          <span className="dashboard-chart-eyebrow">
            QUALITY ANALYTICS
          </span>

          <h3>Average quality dimensions</h3>

          <p>
            Compare the core quality dimensions interactively.
          </p>
        </div>
      </div>

      <div className="dashboard-chart-container">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart
            data={data}
            margin={{
              top: 20,
              right: 20,
              left: 0,
              bottom: 20,
            }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              opacity={0.25}
            />

            <XAxis
              dataKey="name"
              tick={{ fontSize: 12 }}
              interval={0}
            />

            <YAxis
              domain={[0, 1]}
              tick={{ fontSize: 12 }}
            />

            <Tooltip
              formatter={(value) => [
                Number(value).toFixed(2),
                'Score',
              ]}
            />

            <Bar
              dataKey="score"
              name="Average score"
              radius={[8, 8, 0, 0]}
              animationDuration={1000}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}


function InteractiveTrendChart({ stats }) {
  const trends = stats?.trends || [];

  const data = Array.isArray(trends)
    ? trends.map((item, index) => ({
        name:
          item.date ||
          item.day ||
          item.label ||
          `Period ${index + 1}`,

        evaluations:
          item.count ??
          item.evaluations ??
          item.total ??
          0,

        score:
          item.average_score ??
          item.final_score ??
          item.score ??
          0,
      }))
    : [];

  return (
    <div className="dashboard-chart-card dashboard-chart-wide">
      <div className="dashboard-chart-header">
        <div>
          <span className="dashboard-chart-eyebrow">
            PERFORMANCE TRENDS
          </span>

          <h3>Evaluation activity</h3>

          <p>
            Track evaluation volume and quality over time.
          </p>
        </div>
      </div>

      <div className="dashboard-chart-container">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height={340}>
            <LineChart
              data={data}
              margin={{
                top: 20,
                right: 20,
                left: 0,
                bottom: 20,
              }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                opacity={0.25}
              />

              <XAxis
                dataKey="name"
                tick={{ fontSize: 12 }}
              />

              <YAxis
                yAxisId="left"
                tick={{ fontSize: 12 }}
              />

              <YAxis
                yAxisId="right"
                orientation="right"
                domain={[0, 1]}
                tick={{ fontSize: 12 }}
              />

              <Tooltip />

              <Legend />

              <Line
                yAxisId="left"
                type="monotone"
                dataKey="evaluations"
                name="Evaluations"
                stroke="#6366f1"
                strokeWidth={3}
                dot={{ r: 4 }}
                activeDot={{ r: 7 }}
                animationDuration={1000}
              />

              <Line
                yAxisId="right"
                type="monotone"
                dataKey="score"
                name="Average score"
                stroke="#14b8a6"
                strokeWidth={3}
                dot={{ r: 4 }}
                activeDot={{ r: 7 }}
                animationDuration={1000}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="dashboard-chart-empty">
            No trend data available for the selected filters.
          </div>
        )}
      </div>
    </div>
  );
}
/* =========================================================
   M4 - DASHBOARD
   ========================================================= */

function DashboardView() {
  const [dashboard, setDashboard] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState(null);

  const [filters, setFilters] =
    useState({
      verdict: '',
      min_score: '',
      max_score: '',
      batch_id: '',
    });

  const loadDashboard = async (
    activeFilters = filters
  ) => {
    try {
      setLoading(true);
      setError(null);

      const cleanFilters =
        Object.fromEntries(
          Object.entries(
            activeFilters
          ).filter(
            ([, value]) =>
              value !== '' &&
              value !== null &&
              value !== undefined
          )
        );

      const data =
        await getDashboardOverview(
          cleanFilters
        );

      setDashboard(data);
    } catch (err) {
      setError(
        err.message ||
          'Unable to load dashboard data.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const handleFilterChange = (
    event
  ) => {
    const {
      name,
      value,
    } = event.target;

    setFilters(
      (previous) => ({
        ...previous,
        [name]: value,
      })
    );
  };

  const handleApplyFilters = () => {
    loadDashboard(filters);
  };

  const handleClearFilters = () => {
    const clearedFilters = {
      verdict: '',
      min_score: '',
      max_score: '',
      batch_id: '',
    };

    setFilters(clearedFilters);

    loadDashboard(
      clearedFilters
    );
  };

  const stats = dashboard || {};

  /*
   * IMPORTANT:
   * Dashboard backend returns normalized verdicts:
   *
   * {
   *   pass: 82,
   *   needs_improvement: 12,
   *   fail: 49,
   *   unknown: 0
   * }
   *
   * Do NOT use raw_verdict_counts here.
   */
  const verdicts =
    stats.verdicts || {};

  /*
   * Backend returns:
   *
   * average_scores: {
   *   relevance,
   *   accuracy,
   *   hallucination_free,
   *   completeness,
   *   final_score
   * }
   */
  const averageScores =
    stats.average_scores || {};

  /*
   * Backend hallucination data.
   */
  const hallucination =
    stats.hallucination || {};

  const dimensions = [
    [
      'Relevance',
      averageScores.relevance ??
        averageScores.average_relevance ??
        0,
    ],
    [
      'Accuracy',
      averageScores.accuracy ??
        averageScores.average_accuracy ??
        0,
    ],
    [
      'Hallucination-free',
      averageScores.hallucination_free ??
        averageScores.average_hallucination_free ??
        0,
    ],
    [
      'Completeness',
      averageScores.completeness ??
        averageScores.average_completeness ??
        0,
    ],
  ];

  /*
   * CORRECT normalized verdict counts.
   */
  const passCount =
    stats.verdicts?.pass ?? 0;

  const needsImprovement =
    stats.verdicts
      ?.needs_improvement ?? 0;

  const failCount =
    stats.verdicts?.fail ?? 0;

  /*
   * CORRECT average final score.
   */
  const finalScore =
    stats.average_scores
      ?.final_score ?? 0;

  /*
   * CORRECT hallucination count.
   *
   * Backend field:
   * responses_with_hallucination
   */
  const hallucinationCount =
    stats.hallucination
      ?.responses_with_hallucination ??
    hallucination.count ??
    hallucination.total ??
    stats.hallucination_count ??
    0;

  const availableBatches =
    Array.isArray(
      stats.available_batches
    )
      ? stats.available_batches
      : [];

  return (
    <section className="dashboard-page">
      <div className="dashboard-heading">
        <div>
          <span className="section-kicker">
            04 / DASHBOARD
          </span>

          <h2>
            Evaluation intelligence
          </h2>

          <p>
            Monitor quality, verdict
            distribution, and evaluation
            patterns from one live view.
          </p>
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={() =>
            loadDashboard()
          }
          disabled={loading}
        >
          ↻{' '}
          {loading
            ? 'Refreshing...'
            : 'Refresh data'}
        </button>
      </div>

      {/* =====================================================
          DASHBOARD FILTERS - M4.3
          ===================================================== */}

      <section className="dashboard-section">
        <div className="dashboard-section-heading">
          <div>
            <span className="section-kicker">
              FILTERS
            </span>

            <h2>
              Refine evaluation data
            </h2>
          </div>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns:
              'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '12px',
            alignItems: 'end',
          }}
        >
          {/* VERDICT */}

          <label>
            <span
              style={{
                display: 'block',
                marginBottom: '6px',
              }}
            >
              Verdict
            </span>

            <select
              name="verdict"
              value={
                filters.verdict
              }
              onChange={
                handleFilterChange
              }
              style={{
                width: '100%',
                padding:
                  '10px 12px',
                borderRadius:
                  '8px',
                border:
                  '1px solid #d1d5db',
                background:
                  'white',
              }}
            >
              <option value="">
                All verdicts
              </option>

              <option value="PASS">
                PASS
              </option>

              <option value="NEEDS_IMPROVEMENT">
                NEEDS IMPROVEMENT
              </option>

              <option value="FAIL">
                FAIL
              </option>
            </select>
          </label>

          {/* MINIMUM SCORE */}

          <label>
            <span
              style={{
                display: 'block',
                marginBottom: '6px',
              }}
            >
              Minimum score
            </span>

            <input
              type="number"
              name="min_score"
              min="0"
              max="1"
              step="0.01"
              placeholder="0.00"
              value={
                filters.min_score
              }
              onChange={
                handleFilterChange
              }
              style={{
                width: '100%',
                padding:
                  '10px 12px',
                borderRadius:
                  '8px',
                border:
                  '1px solid #d1d5db',
              }}
            />
          </label>

          {/* MAXIMUM SCORE */}

          <label>
            <span
              style={{
                display: 'block',
                marginBottom: '6px',
              }}
            >
              Maximum score
            </span>

            <input
              type="number"
              name="max_score"
              min="0"
              max="1"
              step="0.01"
              placeholder="1.00"
              value={
                filters.max_score
              }
              onChange={
                handleFilterChange
              }
              style={{
                width: '100%',
                padding:
                  '10px 12px',
                borderRadius:
                  '8px',
                border:
                  '1px solid #d1d5db',
              }}
            />
          </label>

          {/* BATCH */}

          <label>
            <span
              style={{
                display: 'block',
                marginBottom: '6px',
              }}
            >
              Batch
            </span>

            <select
              name="batch_id"
              value={
                filters.batch_id
              }
              onChange={
                handleFilterChange
              }
              style={{
                width: '100%',
                padding:
                  '10px 12px',
                borderRadius:
                  '8px',
                border:
                  '1px solid #d1d5db',
                background:
                  'white',
              }}
            >
              <option value="">
                All batches
              </option>

              {availableBatches.map(
                (batch) => (
                  <option
                    key={
                      batch.batch_id
                    }
                    value={
                      batch.batch_id
                    }
                  >
                    {batch.filename ||
                      batch.batch_id}
                  </option>
                )
              )}
            </select>
          </label>

          {/* BUTTONS */}

          <div
            style={{
              display: 'flex',
              gap: '8px',
            }}
          >
            <button
              type="button"
              className="primary-button"
              onClick={
                handleApplyFilters
              }
              disabled={loading}
            >
              Apply filters
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={
                handleClearFilters
              }
              disabled={loading}
            >
              Clear
            </button>
          </div>
        </div>
      </section>

      {/* =====================================================
          DASHBOARD CONTENT
          ===================================================== */}

      {loading && !dashboard ? (
        <div className="dashboard-state">
          <div className="history-loader" />

          Loading dashboard data...
        </div>
      ) : error ? (
        <div className="dashboard-state dashboard-error-state">
          {error}
        </div>
      ) : (
        <>
          {/* TOP METRICS */}

          <div className="dashboard-metric-grid">
            <div className="dashboard-metric-card">
              <span>
                Total responses
              </span>

              <strong>
                {stats.total_responses ??
                  stats.total ??
                  0}
              </strong>
            </div>

            <div className="dashboard-metric-card">
              <span>
                Average final score
              </span>

              <strong>
                {scoreValue(
                  finalScore
                ).toFixed(2)}
              </strong>
            </div>

            <div className="dashboard-metric-card">
              <span>
                Hallucination cases
              </span>

              <strong>
                {hallucinationCount}
              </strong>
            </div>
          </div>

          {/* QUALITY DIMENSIONS */}

          <section className="dashboard-section">
            <div className="dashboard-section-heading">
              <div>
                <span className="section-kicker">
                  QUALITY DIMENSIONS
                </span>

                <h2>
                  Average dimension scores
                </h2>
              </div>
            </div>

            <div className="dashboard-dimension-grid">
              {dimensions.map(
                ([label, value]) => (
                  <div
                    className="dashboard-dimension-card"
                    key={label}
                  >
                    <div className="dashboard-dimension-top">
                      <span>
                        {label}
                      </span>

                      <strong>
                        {scoreValue(
                          value
                        ).toFixed(2)}
                      </strong>
                    </div>

                    <ScoreBar
                      value={value}
                    />
                  </div>
                )
              )}
            </div>
          </section>

          {/* VERDICT DISTRIBUTION */}

          <section className="dashboard-section">
            <div className="dashboard-section-heading">
              <div>
                <span className="section-kicker">
                  VERDICT DISTRIBUTION
                </span>

                <h2>
                  Evaluation outcomes
                </h2>
              </div>
            </div>

            <div className="dashboard-verdict-list">
              <div>
                <span>PASS</span>

                <strong>
                  {passCount}
                </strong>
              </div>

              <div>
                <span>
                  NEEDS IMPROVEMENT
                </span>

                <strong>
                  {needsImprovement}
                </strong>
              </div>

              <div>
                <span>FAIL</span>

                <strong>
                  {failCount}
                </strong>
              </div>
            </div>
          </section>
        </>
      )}
    </section>
  );
}

/* =========================================================
   MAIN APP
   ========================================================= */

function App() {
  const [activeTab, setActiveTab] =
    useState('single');

  const [question, setQuestion] =
    useState('');

  const [response, setResponse] =
    useState('');

  const [
    referenceAnswer,
    setReference,
  ] = useState('');

  const [
    sourceDocument,
    setSource,
  ] = useState('');

  const [loading, setLoading] =
    useState(false);

  const [loadingStep, setLoadingStep] =
    useState(0);

  const [result, setResult] =
    useState(null);

  const [error, setError] =
    useState(null);

  const [batchFile, setBatchFile] =
    useState(null);

  const [
    batchLoading,
    setBatchLoading,
  ] = useState(false);

  const [
    batchResult,
    setBatchResult,
  ] = useState(null);

  const [
    batchError,
    setBatchError,
  ] = useState(null);

  const [
    selectedBatchItem,
    setSelectedBatchItem,
  ] = useState(null);

  const startLoadingCycle = () => {
    setLoadingStep(0);

    let step = 0;

    const interval = setInterval(
      () => {
        step =
          (step + 1) %
          LOADING_STEPS.length;

        setLoadingStep(step);
      },
      900
    );

    return interval;
  };

  const handleSubmit = async (
    event
  ) => {
    event.preventDefault();

    if (
      !question.trim() ||
      !response.trim()
    ) {
      return;
    }

    setLoading(true);
    setResult(null);
    setError(null);

    const interval =
      startLoadingCycle();

    try {
      const data =
        await submitEvaluation({
          question:
            question.trim(),

          response:
            response.trim(),

          reference_answer:
            referenceAnswer.trim() ||
            null,

          source_document:
            sourceDocument.trim() ||
            null,
        });

      setResult(data);
    } catch (err) {
      setError(
        err.message ||
          'An unexpected error occurred.'
      );
    } finally {
      clearInterval(interval);
      setLoading(false);
    }
  };

  const handleBatchSubmit =
    async () => {
      if (
        !batchFile ||
        batchLoading
      ) {
        return;
      }

      setBatchLoading(true);
      setBatchError(null);
      setBatchResult(null);
      setSelectedBatchItem(null);

      try {
        const data =
          await submitBatchEvaluation(
            batchFile
          );

        setBatchResult(data);
      } catch (err) {
        setBatchError(
          err.message ||
            'Batch evaluation failed.'
        );
      } finally {
        setBatchLoading(false);
      }
    };

  const reset = () => {
    setQuestion('');
    setResponse('');
    setReference('');
    setSource('');
    setResult(null);
    setError(null);
    setLoadingStep(0);
  };

  const downloadSinglePdf = () => {
    if (!result?.id) return;

    const url = `http://127.0.0.1:8000/api/evaluation/result/${result.id}/pdf`;

    window.open(url, '_blank');
  };

  const downloadBatchPdf = () => {
    if (!batchResult?.batch_id) return;

    const url = `http://127.0.0.1:8000/api/evaluation/batch/${batchResult.batch_id}/pdf`;

    window.open(url, '_blank');
  };

  const canSubmit =
    question.trim().length > 0 &&
    response.trim().length > 0 &&
    !loading;

  const verdict = String(
    result?.verdict || ''
  ).toUpperCase();

  const verdictMeta =
    VERDICT_META[verdict] || {
      tone: 'warning',
      label: verdict || 'Pending',
      summary:
        'Review the returned evaluation.',
      icon: '!',
    };

  const hallucinationAnalysis =
    result?.hallucination_analysis ||
    result?.hallucinationAnalysis ||
    null;

  return (
    <main className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="topbar page-width">
        <div className="brand">
          <div className="brand-mark">
            <Icon>✦</Icon>
          </div>

          <div>
            <strong>
              VALI<span>D</span>
            </strong>

            <small>
              AI response intelligence
            </small>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          Evaluation engine ready
        </div>
      </header>

      <div className="page-width content">
        <section className="hero">
          <div className="eyebrow">
            <span /> AI QUALITY ASSURANCE WORKSPACE
          </div>

          <h1>
            AI Response <em>Validation System</em>
          </h1>

          <p>
            Hallucination Detection Assistance
          </p>

          <div className="hero-description">
            Evaluate AI-generated responses
            for relevance, accuracy,
            completeness and hallucination.
          </div>

          <div
            className="hero-signal"
            aria-hidden="true"
          >
            <div className="signal-glow" />

            <svg
              viewBox="0 0 560 170"
              role="presentation"
            >
              <path
                className="signal-grid-line"
                d="M0 132H560M0 92H560M0 52H560"
              />

              <path
                className="signal-wave signal-wave-back"
                d="M0 119C52 119 53 71 104 71S156 126 209 126 261 52 315 52s52 70 105 70 54-44 140-44"
              />

              <path
                className="signal-wave"
                d="M0 133C50 133 53 100 105 100s54 38 105 38 53-83 105-83 53 62 105 62 54-25 140-25"
              />

              <circle
                className="signal-pulse"
                cx="420"
                cy="117"
                r="5"
              />
            </svg>

            <span>
              REAL-TIME QUALITY SIGNAL
            </span>
          </div>
        </section>

        <nav
          className="workspace-tabs"
          aria-label="Evaluation mode"
        >
          <button
            type="button"
            className={`workspace-tab ${
              activeTab === 'single'
                ? 'active'
                : ''
            }`}
            onClick={() =>
              setActiveTab('single')
            }
            aria-selected={
              activeTab === 'single'
            }
          >
            <span className="workspace-tab-index">
              01
            </span>

            <span>
              <strong>
                Single Evaluation
              </strong>

              <small>
                Evaluate one AI response
              </small>
            </span>
          </button>

          <button
            type="button"
            className={`workspace-tab ${
              activeTab === 'batch'
                ? 'active'
                : ''
            }`}
            onClick={() =>
              setActiveTab('batch')
            }
            aria-selected={
              activeTab === 'batch'
            }
          >
            <span className="workspace-tab-index">
              02
            </span>

            <span>
              <strong>
                Batch Evaluation
              </strong>

              <small>
                Evaluate multiple AI
                responses from a dataset
              </small>
            </span>
          </button>

          <button
            type="button"
            className={`workspace-tab ${
              activeTab === 'history'
                ? 'active'
                : ''
            }`}
            onClick={() =>
              setActiveTab('history')
            }
            aria-selected={
              activeTab === 'history'
            }
          >
            <span className="workspace-tab-index">
              03
            </span>

            <span>
              <strong>
                Evaluation History
              </strong>

              <small>
                Browse previous evaluations
              </small>
            </span>
          </button>

          <button
            type="button"
            className={`workspace-tab ${
              activeTab === 'dashboard'
                ? 'active'
                : ''
            }`}
            onClick={() =>
              setActiveTab('dashboard')
            }
            aria-selected={
              activeTab === 'dashboard'
            }
          >
            <span className="workspace-tab-index">
              04
            </span>

            <span>
              <strong>Dashboard</strong>

              <small>
                Monitor evaluation
                intelligence
              </small>
            </span>
          </button>
        </nav>

        {/* =====================================================
            SINGLE EVALUATION WORKSPACE
            ===================================================== */}

        {activeTab === 'single' && (
          <>
            <div className="workspace-grid">
              <section className="panel input-panel">
                <div className="panel-heading">
                  <div>
                    <span className="section-kicker">
                      01 / INPUT
                    </span>

                    <h2>
                      Evaluation workspace
                    </h2>
                  </div>

                  <span className="secure-label">
                    <Icon>◈</Icon> Local session
                  </span>
                </div>

                <p className="panel-intro">
                  Provide the response and
                  supporting context you want
                  the evaluation engine to
                  assess.
                </p>

                <form
                  onSubmit={handleSubmit}
                >
                  <Field
                    label="Question"
                    value={question}
                    onChange={setQuestion}
                    placeholder="What would you like to validate?"
                    rows={3}
                    required
                    hint="The original user prompt or question"
                  />

                  <Field
                    label="AI Generated Response"
                    value={response}
                    onChange={setResponse}
                    placeholder="Paste the AI-generated response here..."
                    rows={6}
                    required
                    hint="The answer produced by the AI system"
                  />

                  <div className="field-row">
                    <Field
                      label="Reference Answer"
                      value={
                        referenceAnswer
                      }
                      onChange={
                        setReference
                      }
                      placeholder="Expected answer (optional)"
                      rows={4}
                      hint="Improves accuracy comparison"
                    />

                    <Field
                      label="Source Document"
                      value={
                        sourceDocument
                      }
                      onChange={setSource}
                      placeholder="Paste source context..."
                      rows={4}
                      hint="Optional grounding material"
                    />
                  </div>

                  <div className="form-footer">
                    <span className="required-note">
                      <span className="required">
                        *
                      </span>{' '}
                      Required fields
                    </span>

                    <button
                      className="primary-button"
                      type="submit"
                      disabled={
                        !canSubmit
                      }
                    >
                      <span>
                        {loading
                          ? 'Evaluating response'
                          : 'Evaluate response'}
                      </span>

                      <Icon>
                        {loading
                          ? '◌'
                          : '→'}
                      </Icon>
                    </button>
                  </div>
                </form>
              </section>

              <aside className="side-rail">
                <div className="rail-card methodology">
                  <span className="section-kicker">
                    HOW IT WORKS
                  </span>

                  <h3>
                    Four dimensions. <br />
                    One clear verdict.
                  </h3>

                  <div className="method-list">
                    {DIMENSIONS.map(
                      (item, index) => (
                        <div
                          className="method-item"
                          key={item.key}
                        >
                          <span>
                            {String(
                              index + 1
                            ).padStart(
                              2,
                              '0'
                            )}
                          </span>

                          <div>
                            <strong>
                              {
                                item.label
                              }
                            </strong>

                            <small>
                              {
                                item.description
                              }
                            </small>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </div>

                <div className="rail-card note-card">
                  <div className="note-icon">
                    ✦
                  </div>

                  <div>
                    <strong>
                      Designed for
                      trustworthy AI
                    </strong>

                    <p>
                      Evidence-led evaluation
                      for clearer, safer model
                      outputs.
                    </p>
                  </div>
                </div>
              </aside>
            </div>
          </>
        )}

        {/* =====================================================
            BATCH EVALUATION - M3.4
            ===================================================== */}

        {activeTab === 'batch' && (
          <>
            <section className="batch-panel">
              <div className="batch-section-heading">
                <div>
                  <span className="section-kicker">
                    M3.4 / BATCH EVALUATION
                  </span>

                  <h2>
                    Evaluate multiple
                    responses
                  </h2>
                </div>

                <span className="batch-file-label">
                  CSV input
                </span>
              </div>

              <p className="batch-description">
                Upload a CSV containing
                question and response columns.
                Reference answer and source
                are optional.
              </p>

              <div className="batch-upload-area">
                <input
                  id="batch-file"
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(event) => {
                    const file =
                      event.target.files?.[0] ||
                      null;

                    setBatchFile(file);
                    setBatchResult(
                      null
                    );
                    setBatchError(null);
                    setSelectedBatchItem(
                      null
                    );
                  }}
                />

                <label
                  htmlFor="batch-file"
                  className="batch-file-button"
                >
                  Choose CSV
                </label>

                <div className="batch-file-info">
                  {batchFile ? (
                    <>
                      <strong>
                        {batchFile.name}
                      </strong>

                      <span>
                        {(
                          batchFile.size /
                          1024
                        ).toFixed(1)}{' '}
                        KB
                      </span>
                    </>
                  ) : (
                    <>
                      <strong>
                        No file selected
                      </strong>

                      <span>
                        Required columns:
                        question, response
                      </span>
                    </>
                  )}
                </div>

                <button
                  type="button"
                  className="primary-button batch-run-button"
                  disabled={
                    !batchFile ||
                    batchLoading
                  }
                  onClick={
                    handleBatchSubmit
                  }
                >
                  <span>
                    {batchLoading
                      ? 'Processing batch'
                      : 'Run batch evaluation'}
                  </span>

                  <Icon>
                    {batchLoading
                      ? '◌'
                      : '→'}
                  </Icon>
                </button>
              </div>

              {batchLoading && (
                <div className="batch-progress">
                  <div className="batch-progress-orbit" />

                  <div>
                    <strong>
                      Batch evaluation in
                      progress
                    </strong>

                    <p>
                      Each valid CSV row is
                      being evaluated through
                      the multi-agent pipeline.
                    </p>
                  </div>
                </div>
              )}

              {batchError &&
                !batchLoading && (
                  <div className="batch-error">
                    <strong>
                      Batch evaluation error
                    </strong>

                    <p>
                      {batchError}
                    </p>
                  </div>
                )}
            </section>

            {batchResult &&
              !batchLoading && (
                <BatchResults
                  batchResult={
                    batchResult
                  }
                  selectedBatchItem={
                    selectedBatchItem
                  }
                  setSelectedBatchItem={
                    setSelectedBatchItem
                  }
                  onDownloadBatchPdf={
                    downloadBatchPdf
                  }
                />
              )}
          </>
        )}

        {/* =====================================================
            HISTORY
            ===================================================== */}

        {activeTab === 'history' && (
          <HistoryView
            onOpen={async (id) => {
              if (!id) return;

              try {
                const detail =
                  await getHistoryDetail(
                    id
                  );

                const isBatch =
                  Boolean(detail?.batch_id) ||
                  Array.isArray(detail?.results) ||
                  Boolean(detail?.statistics) ||
                  String(
                    detail?.type || ''
                  ).toUpperCase() === 'BATCH';

                if (isBatch) {
                  setBatchResult(
                    detail
                  );

                  setSelectedBatchItem(
                    null
                  );

                  setBatchError(null);

                  setActiveTab(
                    'batch'
                  );
                } else {
                  setResult(detail);

                  setActiveTab(
                    'single'
                  );
                }
              } catch (err) {
                setError(
                  err.message ||
                    'Unable to open evaluation details.'
                );
              }
            }}
          />
        )}

        {/* =====================================================
            DASHBOARD
            ===================================================== */}

        {activeTab === 'dashboard' && (
          <DashboardView />
        )}

        {/* =====================================================
            SINGLE EVALUATION LOADING
            ===================================================== */}

        {activeTab === 'single' &&
          loading && (
            <section className="panel state-panel loading-panel">
              <div className="loader-orbit">
                <span />
                <span />
                <span />
              </div>

              <div>
                <span className="section-kicker">
                  ANALYSIS IN PROGRESS
                </span>

                <h2>
                  {
                    LOADING_STEPS[
                      loadingStep
                    ]
                  }
                </h2>

                <p>
                  Reviewing your response
                  across four quality
                  dimensions.
                </p>
              </div>

              <div className="step-line">
                {LOADING_STEPS.map(
                  (_, index) => (
                    <span
                      key={index}
                      className={
                        index <=
                        loadingStep
                          ? 'active'
                          : ''
                      }
                    />
                  )
                )}
              </div>

              <AgentPipeline
                activeStep={
                  loadingStep
                }
              />
            </section>
          )}

        {/* =====================================================
            SINGLE EVALUATION ERROR
            ===================================================== */}

        {activeTab === 'single' &&
          error &&
          !loading && (
            <section className="panel state-panel error-panel">
              <div className="state-icon">
                !
              </div>

              <div>
                <span className="section-kicker">
                  EVALUATION ERROR
                </span>

                <h2>
                  We couldn’t complete this
                  evaluation
                </h2>

                <p>{error}</p>

                <button
                  className="text-button"
                  onClick={() =>
                    setError(null)
                  }
                >
                  Dismiss message
                </button>
              </div>
            </section>
          )}

        {/* =====================================================
            SINGLE EVALUATION RESULTS
            ===================================================== */}

        {activeTab === 'single' &&
          result &&
          !loading && (
            <section className="results-section">
              <div className="results-heading">
                <div>
                  <span className="section-kicker">
                    02 / OUTPUT
                  </span>

                  <h2>
                    Evaluation results
                  </h2>
                </div>

                <div
                  style={{
                    display: 'flex',
                    gap: '10px',
                    alignItems: 'center',
                  }}
                >
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={downloadSinglePdf}
                  >
                    <Icon>↓</Icon>
                    Download PDF
                  </button>

                  <button
                    type="button"
                    className="secondary-button"
                    onClick={reset}
                  >
                    <Icon>＋</Icon>
                    New evaluation
                  </button>
                </div>
              </div>

              <div className="score-grid">
                {DIMENSIONS.map(
                  (dimension) => (
                    <ScoreCard
                      key={
                        dimension.key
                      }
                      dimension={
                        dimension
                      }
                      value={
                        result.scores?.[
                          dimension.key
                        ]
                      }
                    />
                  )
                )}
              </div>

              <div className="summary-grid">
                <article className="final-score-card">
                  <div>
                    <span className="section-kicker">
                      FINAL SCORE
                    </span>

                    <p>
                      Weighted across all
                      evaluation dimensions
                    </p>
                  </div>

                  <strong>
                    {scoreValue(
                      result.final_score
                    ).toFixed(2)}
                  </strong>

                  <ScoreBar
                    value={
                      result.final_score
                    }
                  />
                </article>

                <article
                  className={`verdict-card ${verdictMeta.tone}`}
                >
                  <div className="verdict-orb">
                    {
                      verdictMeta.icon
                    }
                  </div>

                  <div>
                    <span className="section-kicker">
                      VERDICT
                    </span>

                    <h3>
                      {
                        verdictMeta.label
                      }
                    </h3>

                    <p>
                      {
                        verdictMeta.summary
                      }
                    </p>
                  </div>
                </article>
              </div>

              <QualityRadar
                scores={
                  result.scores
                }
              />

              {result.explanations && (
                <section className="analysis-panel">
                  <div className="analysis-heading">
                    <div>
                      <span className="section-kicker">
                        03 / EXPLANATION
                      </span>

                      <h2>
                        Agent Analysis
                      </h2>
                    </div>

                    <span className="analysis-caption">
                      Dimension-level
                      reasoning
                    </span>
                  </div>

                  <div className="explanation-grid">
                    {DIMENSIONS.map(
                      (dimension) =>
                        result
                          .explanations[
                          dimension.key
                        ] && (
                          <article
                            key={
                              dimension.key
                            }
                            className="explanation-card"
                          >
                            <div
                              className={`metric-icon ${scoreTone(
                                scoreValue(
                                  result
                                    .scores?.[
                                    dimension
                                      .key
                                  ]
                                )
                              )}`}
                            >
                              {
                                dimension.icon
                              }
                            </div>

                            <div>
                              <strong>
                                {
                                  dimension.label
                                }
                              </strong>

                              <p>
                                {
                                  result
                                    .explanations[
                                    dimension
                                      .key
                                  ]
                                }
                              </p>
                            </div>
                          </article>
                        )
                    )}
                  </div>
                </section>
              )}

              <HallucinationAnalysis
                analysis={
                  hallucinationAnalysis
                }
              />

              <CompletenessAnalysis
                analysis={
                  result.completeness_analysis
                }
                score={
                  result.scores
                    ?.completeness
                }
              />

              <ConsolidatedSummary
                result={result}
              />

              <div className="result-meta">
                <span>
                  Evaluation ID
                </span>

                <code>
                  {result.id}
                </code>

                <span className="meta-divider" />

                <span>
                  Scoring model: weighted
                  dimension analysis
                </span>
              </div>
            </section>
          )}

        {/* =====================================================
            QUICK START
            ===================================================== */}

        {activeTab === 'single' &&
          !result &&
          !loading &&
          !error && (
            <section className="demo-section">
              <div>
                <span className="section-kicker">
                  QUICK START
                </span>

                <h2>
                  Explore a test case
                </h2>

                <p>
                  Load an example to see the
                  workspace in action.
                </p>
              </div>

              <div className="demo-list">
                {[
                  {
                    label:
                      'Correct answer',

                    q:
                      'What is the capital of France?',

                    r:
                      'The capital of France is Paris.',

                    ref:
                      'Paris is the capital of France.',
                  },

                  {
                    label:
                      'Incorrect answer',

                    q:
                      'What is the capital of France?',

                    r:
                      'The capital of France is Berlin.',

                    ref:
                      'Paris is the capital of France.',
                  },

                  {
                    label:
                      'Incomplete answer',

                    q:
                      'What are the three branches of the US government and the role of each?',

                    r:
                      'One branch is Congress, which makes laws.',

                    ref:
                      'Legislative (Congress — makes laws), Executive (President — enforces laws), Judicial (Supreme Court — interprets laws).',
                  },
                ].map(
                  (item, index) => (
                    <button
                      className="demo-item"
                      type="button"
                      key={
                        item.label
                      }
                      onClick={() => {
                        setQuestion(
                          item.q
                        );

                        setResponse(
                          item.r
                        );

                        setReference(
                          item.ref
                        );

                        setSource('');
                        setResult(null);
                        setError(null);
                      }}
                    >
                      <span className="demo-number">
                        0
                        {index + 1}
                      </span>

                      <span>
                        <strong>
                          {
                            item.label
                          }
                        </strong>

                        <small>
                          Load example{' '}
                          <Icon>
                            →
                          </Icon>
                        </small>
                      </span>
                    </button>
                  )
                )}
              </div>
            </section>
          )}

        <footer>
          <span>
            VALID / AI response intelligence
          </span>

          <span>
            Focused evaluation for responsible
            AI
          </span>
        </footer>
      </div>
    </main>
  );
}

export default App;
