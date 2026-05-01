import { createRoot } from 'react-dom/client'
import App from './App'
// Load the existing apps/ui global stylesheet so the embedded
// ChatTranscript / Composer / ChatHeader components keep their styling
// without us re-declaring it. JarvisX's own Tailwind layer wraps around
// it via index.css below.
import '@ui/styles/global.css'
import './styles/index.css'

// StrictMode intentionally NOT used — it double-invokes effects which
// compounds badly with the existing useUnifiedShell polling cycle and
// the markdown-heavy chat transcript. The webchat ships without it
// for the same reason.
const root = document.getElementById('root')
if (!root) throw new Error('#root not found')
createRoot(root).render(<App />)
