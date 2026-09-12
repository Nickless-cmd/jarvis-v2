import { render } from '@testing-library/react-native'
import { ResearchStatus } from './ResearchStatus'

it('viser fase og konkret fremdrift uden chain-of-thought', async () => {
  const screen = await render(<ResearchStatus research={{
    runId: 'r1', tier: 'orchestrated', phase: 'researching',
    completedTasks: 2, totalTasks: 4, sources: 7, warning: '', quality: '',
  }} />)
  expect(screen.getByText('Research 2/4')).toBeTruthy()
  expect(screen.getByText('7 kilder')).toBeTruthy()
})

it('rendererer intet uden et aktivt eller afsluttet research-run', async () => {
  const screen = await render(<ResearchStatus research={null} />)
  expect(screen.toJSON()).toBeNull()
})
