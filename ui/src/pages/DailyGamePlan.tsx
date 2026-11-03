import { useMemo } from 'react';
import { useStore } from '../state/StoreContext';
import RecommendationCard from '../components/RecommendationCard';

export default function DailyGamePlan() {
  const { dailyPlan, loading, error } = useStore();
  const grouped = useMemo(() => {
    const g: Record<string, typeof dailyPlan.recommendations> = { HIGH: [], MEDIUM: [], LOW: [] } as any;
    if (!dailyPlan) return g;
    for (const r of dailyPlan.recommendations) {
      (g[r.priority] ??= []).push(r);
    }
    for (const key of Object.keys(g)) {
      g[key].sort((a, b) => b.expected_margin_impact - a.expected_margin_impact);
    }
    return g;
  }, [dailyPlan]);

  if (loading) return <div className="loader">Generating the daily plan…</div>;
  if (error) return <div className="error-box">Error: {error}</div>;
  if (!dailyPlan) return <div className="empty">No plan yet.</div>;

  return (
    <div className="page-wrap">
      <h1>Daily Store Game Plan</h1>
      <p className="muted">
        Prioritized actions for store {dailyPlan.store_id} · generated {new Date(dailyPlan.generated_at).toLocaleString()}.
      </p>

      {(['HIGH', 'MEDIUM', 'LOW'] as const).map((p) => (
        <section key={p}>
          <h2 className={`priority-h p-${p.toLowerCase()}`}>{p} PRIORITY · {grouped[p]?.length ?? 0}</h2>
          <div className="rec-list">
            {(grouped[p] ?? []).map((r) => <RecommendationCard key={r.recommendation_id} rec={r} />)}
          </div>
        </section>
      ))}
    </div>
  );
}
