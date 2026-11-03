import { useState } from 'react';
import type { Recommendation } from '../types/models';
import { api } from '../services/api';

interface Props {
  rec: Recommendation;
  onExecuted?: (id: string, status: string) => void;
}

export default function RecommendationCard({ rec, onExecuted }: Props) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<string>(rec.status);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const execute = async (role: string) => {
    setBusy(true);
    setMessage(null);
    try {
      const res = await api.executeAction(rec.recommendation_id, role);
      setStatus(res.status);
      setMessage(res.reason ?? (res.executed ? 'Approved.' : 'Blocked by guardrails.'));
      onExecuted?.(rec.recommendation_id, res.status);
    } catch (e: any) {
      setMessage(e.message);
    } finally {
      setBusy(false);
    }
  };

  const metrics = Object.entries(rec.supporting_metrics).filter(
    ([, v]) => typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean',
  );

  return (
    <article className={`rec-card p-${rec.priority.toLowerCase()}`}>
      <header>
        <span className={`badge p-${rec.priority.toLowerCase()}`}>{rec.priority}</span>
        <span className="action-tag">{rec.action_type}</span>
        <h3>{rec.title}</h3>
      </header>
      <p className="why">{rec.justification}</p>
      <div className="rec-row">
        <div><span className="k">Revenue impact</span><strong>${rec.expected_sales_impact.toLocaleString()}</strong></div>
        <div><span className="k">Margin impact</span><strong>${rec.expected_margin_impact.toLocaleString()}</strong></div>
        <div><span className="k">Confidence</span><strong>{Math.round(rec.confidence * 100)}%</strong></div>
        <div><span className="k">Owner</span><strong>{rec.responsible_role.replace('_', ' ')}</strong></div>
      </div>
      <footer>
        <button className="link" onClick={() => setOpen(!open)}>
          {open ? 'Hide evidence' : 'View evidence'}
        </button>
        <div className="actions">
          <span className="status">Status: {status}</span>
          <button
            className="btn btn-primary"
            disabled={busy || status === 'Executed'}
            onClick={() => execute(rec.required_approval)}
          >
            {status === 'Executed' ? 'Executed' : `Approve as ${rec.required_approval.replace('_', ' ')}`}
          </button>
        </div>
      </footer>
      {message && <div className="rec-message">{message}</div>}
      {open && (
        <div className="evidence">
          <div className="evidence-grid">
            <section>
              <h4>Supporting metrics</h4>
              <ul>
                {metrics.map(([k, v]) => (
                  <li key={k}><strong>{k.replace(/_/g, ' ')}:</strong> {String(v)}</li>
                ))}
              </ul>
            </section>
            <section>
              <h4>Risks</h4>
              <ul>{rec.risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </section>
            <section>
              <h4>Assumptions</h4>
              <ul>{rec.assumptions.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </section>
          </div>
          <div className="success-kpi">Success KPI: {rec.success_kpi}</div>
        </div>
      )}
    </article>
  );
}
