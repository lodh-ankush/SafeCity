const STATUS_LABEL = {
  open: "Live",
  connecting: "Connecting…",
  closed: "Disconnected",
};

export default function Header({ status }) {
  return (
    <header className="header">
      <div className="header-title">
        <span className="header-emoji">🛡️</span>
        <div>
          <h1>SafeCity AI</h1>
          <p className="header-subtitle">Real-time urban safety intelligence</p>
        </div>
      </div>
      <div className={`ws-badge ws-badge--${status}`}>
        <span className="ws-dot" />
        {STATUS_LABEL[status] ?? status}
      </div>
    </header>
  );
}
