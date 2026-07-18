import { useEffect, useRef, useState } from "react";
import { wsAlertsUrl } from "../api";

// Connects to /ws/alerts and calls onIncident for every live-broadcast
// incident (see backend/api/routes.py ingest_event -> manager.broadcast()).
// Auto-reconnects with a fixed backoff so a backend restart during dev
// doesn't permanently strand the UI in "disconnected".
export function useLiveAlerts(onIncident) {
  const [status, setStatus] = useState("connecting");
  const onIncidentRef = useRef(onIncident);
  onIncidentRef.current = onIncident;

  useEffect(() => {
    let ws;
    let retryTimer;
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      setStatus("connecting");
      ws = new WebSocket(wsAlertsUrl());

      ws.onopen = () => setStatus("open");
      ws.onclose = () => {
        if (cancelled) return;
        setStatus("closed");
        retryTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (event) => {
        try {
          onIncidentRef.current?.(JSON.parse(event.data));
        } catch {
          // ignore malformed frames
        }
      };
    }

    connect();
    return () => {
      cancelled = true;
      clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);

  return status;
}
