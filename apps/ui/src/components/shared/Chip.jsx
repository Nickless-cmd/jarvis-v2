export function Chip({ children, color = '#4e5262', bg }) {
  const style = {
    background: bg || `${color}18`,
    border: `1px solid ${color}35`,
    color,
  }
  return <span className="chip mono" style={style}>{children}</span>
}
