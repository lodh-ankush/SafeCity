export default function Filters({ filters, onChange, typeMeta }) {
  return (
    <div className="filters">
      <label>
        Type
        <select
          value={filters.type}
          onChange={(e) => onChange({ ...filters, type: e.target.value })}
        >
          <option value="">All types</option>
          {Object.keys(typeMeta ?? {}).map((type) => (
            <option key={type} value={type}>
              {typeMeta[type].icon} {type.replace("_", " ")}
            </option>
          ))}
        </select>
      </label>
      <label>
        Min score
        <input
          type="number"
          min={0}
          max={1}
          step={0.05}
          value={filters.minScore}
          onChange={(e) => onChange({ ...filters, minScore: e.target.value })}
          placeholder="0.0"
        />
      </label>
    </div>
  );
}
