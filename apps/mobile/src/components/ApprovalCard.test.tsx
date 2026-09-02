import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { ApprovalCard } from './ApprovalCard'

// Bjørn 21. aug 2026: en lang bash-kommando gjorde kortet højere end skærmen,
// så "Tillad" ikke kunne trykkes. Runnet døde af approval-timeout uden at han
// kunne gøre noget. Kortet skal derfor tåle vilkårligt langt `detail` uden at
// knapperne flytter sig.
const LANG_KOMMANDO = [
  "cd /home/bs/apk-work && python3 << 'EOF' 2>&1 | grep -v DEBUG | grep -v INFO | tail -30",
  'import zipfile, os, sys, json, hashlib',
  'from pathlib import Path',
  'for p in sorted(Path(".").rglob("*.apk")):',
  '    with zipfile.ZipFile(p) as z:',
  '        for n in z.namelist():',
  '            print(n, z.getinfo(n).file_size)',
  'EOF'
].join('\n')

it('renders approval details and calls explicit decisions', async () => {
  const onApprove = jest.fn()
  const onDeny = jest.fn()
  const screen = await render(
    <ApprovalCard
      approval={{
        approvalId: 'approval-1',
        tool: 'shell',
        message: 'Jarvis vil køre en kommando.',
        detail: 'ls -la'
      }}
      onApprove={onApprove}
      onDeny={onDeny}
    />
  )

  await waitFor(() => expect(screen.getByText('shell')).toBeTruthy())
  expect(screen.getByText('Jarvis vil køre en kommando.')).toBeTruthy()
  expect(screen.getByText('ls -la')).toBeTruthy()

  await fireEvent.press(screen.getByText('Afvis'))
  await fireEvent.press(screen.getByText('Tillad'))

  expect(onDeny).toHaveBeenCalledTimes(1)
  expect(onApprove).toHaveBeenCalledTimes(1)
})

it('holder Tillad trykbar selv med en meget lang kommando', async () => {
  const onApprove = jest.fn()
  const screen = await render(
    <ApprovalCard
      approval={{
        approvalId: 'approval-2',
        tool: 'bash',
        message: 'Jarvis vil køre en kommando.',
        detail: LANG_KOMMANDO
      }}
      onApprove={onApprove}
      onDeny={jest.fn()}
    />
  )

  await fireEvent.press(screen.getByText('Tillad'))
  expect(onApprove).toHaveBeenCalledTimes(1)
})

it('klipper lang detail så knapperne ikke skubbes ud af skærmen', async () => {
  const screen = await render(
    <ApprovalCard
      approval={{
        approvalId: 'approval-3',
        tool: 'bash',
        message: 'Jarvis vil køre en kommando.',
        detail: LANG_KOMMANDO
      }}
      onApprove={jest.fn()}
      onDeny={jest.fn()}
    />
  )

  const detail = screen.getByText(LANG_KOMMANDO)
  expect(detail.props.numberOfLines).toBeGreaterThan(0)
  expect(detail.props.numberOfLines).toBeLessThan(12)
})

it('tilbyder Vis alt for lang detail — og kun for lang detail', async () => {
  const lang = await render(
    <ApprovalCard
      approval={{ approvalId: 'a', tool: 'bash', message: 'm', detail: LANG_KOMMANDO }}
      onApprove={jest.fn()}
      onDeny={jest.fn()}
    />
  )
  await waitFor(() => expect(lang.getByText('Vis alt')).toBeTruthy())

  await fireEvent.press(lang.getByText('Vis alt'))
  await waitFor(() => expect(lang.getByText('Vis mindre')).toBeTruthy())
  // Udvidet: ingen klipning, men ScrollView'ens maxHeight holder stadig kortet nede.
  expect(lang.getByText(LANG_KOMMANDO).props.numberOfLines).toBeUndefined()

  const kort = await render(
    <ApprovalCard
      approval={{ approvalId: 'b', tool: 'shell', message: 'm', detail: 'ls -la' }}
      onApprove={jest.fn()}
      onDeny={jest.fn()}
    />
  )
  expect(kort.queryByText('Vis alt')).toBeNull()
})

it('klarer sig uden detail', async () => {
  const onApprove = jest.fn()
  const screen = await render(
    <ApprovalCard
      approval={{ approvalId: 'c', tool: 'shell', message: 'Må jeg?' }}
      onApprove={onApprove}
      onDeny={jest.fn()}
    />
  )
  await fireEvent.press(screen.getByText('Tillad'))
  expect(onApprove).toHaveBeenCalledTimes(1)
  expect(screen.queryByText('Vis alt')).toBeNull()
})
