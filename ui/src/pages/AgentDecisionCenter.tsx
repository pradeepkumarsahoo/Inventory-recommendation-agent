import { useStore } from '../state/StoreContext';

export default function AgentDecisionCenter() {
  const { dailyPlan, loading, error } = useStore();
  if (loading) return <div className="loader">Running agents…</div>;
  if (error) return <div className="error-box">Error: {error}</div>;
  if (!dailyPlan) return <div className="empty">No agent run yet.</div>;

  const agentSummary = dailyPlan.agent_trace.reduce<Record<string, number>>((acc, step) => {
    acc[step.agent] = (acc[step.agent] ?? 0) + 1;
    return acc;
  }, {});

  const confidenceHisto: Record<string, number> = { high: 0, med: 0, low: 0 };
  for (const r of dailyPlan.recommendations) {
    if (r.confidence >= 0.75) confidenceHisto.high++;
    else if (r.confidence >= 0.55) confidenceHisto.med++;
    else confidenceHisto.low++;
  }

  return (
    <div className="page-wrap">
      <h1>AI Agent Decision Center</h1>
      <p className="muted">Visibility into the agent supervisor, specialists, confidence, and audit trail.</p>

      <section>
        <h2>Agent participation</h2>
        <div className="chip-row">
          {Object.entries(agentSummary).map(([agent, count]) => (
            <div className="chip" key={agent}><strong>{agent}</strong><span>{count} steps</span></div>
          ))}
        </div>
      </section>

      <section>
        <h2>Confidence distribution</h2>
        <div className="chip-row">
          <div className="chip"><strong>High (≥75%)</strong><span>{confidenceHisto.high}</span></div>
          <div className="chip"><strong>Medium (55–74%)</strong><span>{confidenceHisto.med}</span></div>
          <div className="chip"><strong>Low (&lt;55%)</strong><span>{confidenceHisto.low}</span></div>
        </div>
      </section>

      <section>
        <h2>Agent trace</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>#</th><th>Agent</th><th>Step</th><th>Detail</th></tr>
            </thead>
            <tbody>
              {dailyPlan.agent_trace.map((t, i) => (
                <tr key={i}>
                  <td>{i + 1}</td>
                  <td>{t.agent}</td>
                  <td>{t.step}</td>
                  <td className="mono">{JSON.stringify(t.detail)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
