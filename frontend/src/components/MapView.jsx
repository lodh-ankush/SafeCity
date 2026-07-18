import { useEffect, useMemo, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { TYPE_COLOR_VAR } from "../theme";

function useIsDark() {
  const [isDark, setIsDark] = useState(
    () => document.documentElement.getAttribute("data-theme") === "dark" ||
      window.matchMedia?.("(prefers-color-scheme: dark)").matches
  );
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setIsDark(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return isDark;
}

function makeIcon(type, typeMeta) {
  const icon = typeMeta?.[type]?.icon ?? "❓";
  const color = TYPE_COLOR_VAR[type] ?? "var(--text-muted)";
  return L.divIcon({
    className: "",
    html: `<div class="marker-pin" style="background:${color}"><span>${icon}</span></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -26],
  });
}

export default function MapView({ center, zoom, incidents, typeMeta }) {
  const isDark = useIsDark();
  const tileUrl = isDark
    ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";

  const icons = useMemo(() => {
    const cache = {};
    for (const type of Object.keys(typeMeta ?? {})) cache[type] = makeIcon(type, typeMeta);
    return cache;
  }, [typeMeta]);

  if (!center) return <p className="panel-empty">Loading map…</p>;

  return (
    <MapContainer center={[center.lat, center.lon]} zoom={zoom ?? 13} className="map-container">
      <TileLayer
        url={tileUrl}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
      />
      {incidents
        .filter((i) => i.lat != null && i.lon != null)
        .map((incident) => (
          <Marker
            key={incident.id ?? `${incident.timestamp}-${incident.lat}-${incident.lon}`}
            position={[incident.lat, incident.lon]}
            icon={icons[incident.type] ?? makeIcon(incident.type, typeMeta)}
          >
            <Popup>
              <div className="map-popup">
                <b>{incident.type.replace("_", " ")}</b> · score {Number(incident.fused_score).toFixed(2)}
                <br />
                <span>{incident.timestamp}</span>
                {incident.raw_text ? <p>{incident.raw_text}</p> : null}
              </div>
            </Popup>
          </Marker>
        ))}
    </MapContainer>
  );
}
