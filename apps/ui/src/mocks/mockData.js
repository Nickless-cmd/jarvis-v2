export const mockSessions = [
  { id: 's-1', title: 'Workspace scan', lastMessage: '2m ago' },
  { id: 's-2', title: 'Jarvis UI direction', lastMessage: '14m ago' },
  { id: 's-3', title: 'GitHub Copilot OAuth', lastMessage: '1h ago' },
]

export const mockSelection = {
  source: 'provider_router.main_agent_selection',
  selectionAuthority: 'runtime.settings',
  currentProvider: 'openai',
  currentModel: 'gpt-5',
  currentAuthProfile: 'main',
  availableConfiguredTargets: [
    { provider: 'openai', model: 'gpt-5', authProfile: 'main', authMode: 'api-key', readinessHint: 'auth-required' },
    { provider: 'github-copilot', model: 'gpt-4.1', authProfile: 'copilot', authMode: 'oauth', readinessHint: 'auth-required' },
    { provider: 'ollama', model: 'qwen2.5-coder:7b', authProfile: '', authMode: 'none', readinessHint: 'configured' },
  ],
}

export const mockChat = {
  title: 'Jarvis',
  subtitle: 'Unified shell mock built from your Chat + Mission Control references',
  messages: [
    {
      id: 'm-1',
      role: 'assistant',
      content: 'Jarvis online. Unified shell loaded. Main agent selection is visible in the right panel and Mission Control lives in the same application.',
      ts: '18:21',
    },
    {
      id: 'm-2',
      role: 'user',
      content: 'Show me the direction for the unified frontend.',
      ts: '18:22',
    },
    {
      id: 'm-3',
      role: 'assistant',
      content: 'Chat is the front door. Mission Control is the control room. Same sidebar, same palette, same product family.',
      ts: '18:22',
    },
  ],
}

export const mockMissionControl = {
  overview: [
    { label: 'Health', value: 'Stable', tone: 'green' },
    { label: 'Main Agent', value: 'OpenAI / gpt-5', tone: 'accent' },
    { label: 'Coding Lane', value: 'Copilot OAuth stub', tone: 'amber' },
    { label: 'Local Lane', value: 'Ollama probe ready', tone: 'blue' },
  ],
  events: [
    'provider_router.main_agent_selection loaded',
    'coding lane auth path github-copilot-oauth visible',
    'local lane readiness available',
    'operational preference alignment visible',
  ],
  panels: [
    {
      title: 'Execution Authority',
      body: 'Shows the current main-agent provider, model, auth profile, and configured alternatives.',
    },
    {
      title: 'Runtime Truth',
      body: 'Mission Control keeps the dense operator-facing surfaces. Chat keeps only summaries and immediate controls.',
    },
    {
      title: 'Next Backend Hook',
      body: 'Replace the adapter file only. The rest of the UI should stay mostly untouched.',
    },
  ],
}
