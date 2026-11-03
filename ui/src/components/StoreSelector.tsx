import { useStore } from '../state/StoreContext';

export default function StoreSelector() {
  const { stores, selectedStoreId, setSelectedStoreId, loading, refreshPlan } = useStore();
  return (
    <div className="store-selector">
      <label className="label">Store</label>
      <select
        value={selectedStoreId}
        onChange={(e) => setSelectedStoreId(e.target.value)}
        aria-label="Select store"
      >
        {stores.map((s) => (
          <option key={s.storeId} value={s.storeId}>
            {s.storeId} · {s.name}
          </option>
        ))}
      </select>
      <button className="btn" onClick={refreshPlan} disabled={loading}>
        {loading ? 'Running agents…' : 'Re-run analysis'}
      </button>
    </div>
  );
}
