import { useCallback, useEffect, useState } from "react";
import "./App.css";
import {
  getForecast,
  getIncidents,
  getIncidentTypes,
  getMapIncidents,
  getStats,
  normalizeIncident,
} from "./api";
import { useLiveAlerts } from "./hooks/useLiveAlerts";
import Header from "./components/Header";
import StatTiles from "./components/StatTiles";
import IncidentTypeChart from "./components/IncidentTypeChart";
import HourlyChart from "./components/HourlyChart";
import MapView from "./components/MapView";
import Filters from "./components/Filters";
import IncidentFeed from "./components/IncidentFeed";

const FEED_LIMIT = 60;

function App() {
  const [typeMeta, setTypeMeta] = useState(null);
  const [stats, setStats] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [mapData, setMapData] = useState({ center: null, zoom: 13 });
  const [mapIncidents, setMapIncidents] = useState([]);
  const [feedIncidents, setFeedIncidents] = useState([]);
  const [filters, setFilters] = useState({ type: "", minScore: "" });

  // Static-ish reference data, fetched once.
  useEffect(() => {
    getIncidentTypes().then(setTypeMeta).catch(console.error);
    getMapIncidents()
      .then((d) => {
        setMapData({ center: d.center, zoom: d.zoom });
        setMapIncidents(d.incidents.map(normalizeIncident));
      })
      .catch(console.error);
  }, []);

  const refreshAggregates = useCallback(() => {
    getStats().then(setStats).catch(console.error);
    getForecast().then(setForecast).catch(console.error);
  }, []);

  useEffect(refreshAggregates, [refreshAggregates]);

  // Feed refetches whenever the filter row changes.
  useEffect(() => {
    getIncidents({
      limit: FEED_LIMIT,
      type: filters.type || undefined,
      minScore: filters.minScore !== "" ? Number(filters.minScore) : undefined,
    })
      .then((d) => setFeedIncidents(d.incidents.map(normalizeIncident)))
      .catch(console.error);
  }, [filters]);

  const handleLiveIncident = useCallback(
    (raw) => {
      const incident = normalizeIncident(raw);

      setFeedIncidents((prev) => {
        const matchesType = !filters.type || incident.type === filters.type;
        const matchesScore = filters.minScore === "" || incident.fused_score >= Number(filters.minScore);
        if (!matchesType || !matchesScore) return prev;
        return [incident, ...prev].slice(0, FEED_LIMIT);
      });

      if (incident.lat != null && incident.lon != null) {
        setMapIncidents((prev) => [incident, ...prev]);
      }

      refreshAggregates();
    },
    [filters, refreshAggregates]
  );

  const wsStatus = useLiveAlerts(handleLiveIncident);

  return (
    <div className="app">
      <Header status={wsStatus} />
      <StatTiles stats={stats} />

      <div className="main-grid">
        <div className="grid-col">
          <section className="panel">
            <h2>Incidents by type</h2>
            <IncidentTypeChart stats={stats} typeMeta={typeMeta} />
          </section>
          <section className="panel">
            <h2>Hourly distribution</h2>
            <HourlyChart forecast={forecast} />
          </section>
          <section className="panel">
            <h2>Live incident feed</h2>
            <Filters filters={filters} onChange={setFilters} typeMeta={typeMeta} />
            <div style={{ height: 12 }} />
            <IncidentFeed incidents={feedIncidents} typeMeta={typeMeta} />
          </section>
        </div>

        <section className="panel">
          <h2>Incident map</h2>
          <MapView
            center={mapData.center}
            zoom={mapData.zoom}
            incidents={mapIncidents}
            typeMeta={typeMeta}
          />
        </section>
      </div>
    </div>
  );
}

export default App;
