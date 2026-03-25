export default function FormField({ label, children }) {
  return (
    <div className="portal-field">
      <div className="portal-label">{label}</div>
      {children}
    </div>
  );
}
