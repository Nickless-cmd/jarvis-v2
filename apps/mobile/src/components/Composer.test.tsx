import { act, fireEvent, render, waitFor } from '@testing-library/react-native'
import { Composer } from './Composer'

/**
 * Komponisten har to ÆGTE former: en hvilepille på én række, og en arbejdsform
 * på to rækker med det rigtige tekstfelt. Testene går derfor gennem den samme
 * vej som en finger: tryk på pillen først, skriv derefter. Går man direkte
 * efter feltet, tester man en tilstand brugeren aldrig starter i.
 */
async function openComposer(screen: Awaited<ReturnType<typeof render>>) {
  const rest = screen.queryByTestId('composer-rest')
  if (rest) {
    await act(async () => {
      fireEvent.press(rest)
    })
  }
  await waitFor(() => expect(screen.getByTestId('composer-input')).toBeTruthy())
}

describe('Composer', () => {
  it('starter i hvileformen — ét felt-attrap, intet rigtigt tekstfelt', async () => {
    const screen = await render(<Composer onSend={jest.fn()} onStop={jest.fn()} />)

    expect(screen.getByTestId('composer-rest')).toBeTruthy()
    expect(screen.queryByTestId('composer-input')).toBeNull()
  })

  it('et tryk på hvilepillen åbner arbejdsformen', async () => {
    const screen = await render(<Composer onSend={jest.fn()} onStop={jest.fn()} />)

    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-rest'))
    })

    await waitFor(() => expect(screen.getByTestId('composer-input')).toBeTruthy())
    expect(screen.queryByTestId('composer-rest')).toBeNull()
  })

  it('trims input, sends it, and clears the field', async () => {
    const onSend = jest.fn()
    const screen = await render(<Composer onSend={onSend} onStop={jest.fn()} />)
    await openComposer(screen)

    await act(async () => {
      screen.getByTestId('composer-input').props.onChangeText('  Hej Jarvis  ')
    })
    await waitFor(() => expect(screen.getByTestId('composer-input').props.value).toBe('  Hej Jarvis  '))
    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-button'))
    })

    expect(onSend).toHaveBeenCalledWith('Hej Jarvis')
    await waitFor(() => expect(screen.getByTestId('composer-input').props.value).toBe(''))
  })

  it('keeps the draft when async send fails', async () => {
    const onSend = jest.fn().mockRejectedValue(new Error('session create failed'))
    const screen = await render(<Composer onSend={onSend} onStop={jest.fn()} />)
    await openComposer(screen)

    await act(async () => {
      screen.getByTestId('composer-input').props.onChangeText('Hej Jarvis')
    })
    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-button'))
    })

    expect(onSend).toHaveBeenCalledWith('Hej Jarvis')
    expect(screen.getByTestId('composer-input').props.value).toBe('Hej Jarvis')
  })

  it('shows stop while working and calls onStop instead of sending', async () => {
    const onSend = jest.fn()
    const onStop = jest.fn()
    // `working` holder arbejdsformen åben af sig selv — man skal kunne afbryde
    // uden først at røre komponisten.
    const screen = await render(<Composer working onSend={onSend} onStop={onStop} />)

    await waitFor(() => expect(screen.getByTestId('composer-input')).toBeTruthy())
    expect(screen.queryByTestId('composer-rest')).toBeNull()

    await act(async () => {
      screen.getByTestId('composer-input').props.onChangeText('Hej')
    })
    await waitFor(() => expect(screen.getByTestId('composer-input').props.value).toBe('Hej'))
    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-button'))
    })

    expect(onSend).not.toHaveBeenCalled()
    expect(onStop).toHaveBeenCalledTimes(1)
  })

  it('does not send blank or disabled input', async () => {
    const onSend = jest.fn()
    const screen = await render(<Composer disabled onSend={onSend} onStop={jest.fn()} />)
    await openComposer(screen)

    await act(async () => {
      screen.getByTestId('composer-input').props.onChangeText('   ')
    })
    await waitFor(() => expect(screen.getByTestId('composer-input').props.value).toBe('   '))
    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-button'))
    })
    await act(async () => {
      screen.getByTestId('composer-input').props.onChangeText('Hej')
    })
    await waitFor(() => expect(screen.getByTestId('composer-input').props.value).toBe('Hej'))
    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-button'))
    })

    expect(onSend).not.toHaveBeenCalled()
  })

  it('en vedhæftning holder arbejdsformen åben uden fokus', async () => {
    const screen = await render(
      <Composer
        onSend={jest.fn()}
        onStop={jest.fn()}
        attachments={[{ id: '1', uri: 'file:///a.png', name: 'a.png', mime: 'image/png' }]}
      />
    )

    expect(screen.queryByTestId('composer-rest')).toBeNull()
    await waitFor(() => expect(screen.getByTestId('composer-input')).toBeTruthy())
  })

  it('viser en chip pr. vedhæftning og kan fjerne én ad gangen', async () => {
    const onRemove = jest.fn()
    const screen = await render(
      <Composer
        onSend={jest.fn()}
        onStop={jest.fn()}
        onRemoveAttachment={onRemove}
        attachments={[
          { id: 'a', uri: 'file:///a.png', name: 'a.png', mime: 'image/png' },
          { id: 'b', uri: 'file:///b.zip', name: 'b.zip', mime: 'application/zip' }
        ]}
      />
    )

    expect(screen.getByTestId('attach-chip-a')).toBeTruthy()
    expect(screen.getByTestId('attach-chip-b')).toBeTruthy()

    await act(async () => { fireEvent.press(screen.getByLabelText('Fjern b.zip')) })
    expect(onRemove).toHaveBeenCalledWith('b')
  })

  it('viser upload-progress og fejl direkte på billed-thumbnail', async () => {
    const screen = await render(
      <Composer
        onSend={jest.fn()}
        onStop={jest.fn()}
        attachments={[
          { id: 'a', uri: 'file:///a.png', name: 'a.png', mime: 'image/png', status: 'uploading', progress: 45 },
          { id: 'b', uri: 'file:///b.png', name: 'b.png', mime: 'image/png', status: 'error' }
        ]}
      />
    )

    expect(screen.getByText('45%')).toBeTruthy()
    expect(screen.getByText('Fejl')).toBeTruthy()
  })

  it('kan sende med KUN vedhæftninger og ingen tekst', async () => {
    const onSend = jest.fn()
    const screen = await render(
      <Composer
        onSend={onSend}
        onStop={jest.fn()}
        attachments={[{ id: 'a', uri: 'file:///a.png', name: 'a.png', mime: 'image/png' }]}
      />
    )
    await act(async () => { fireEvent.press(screen.getByTestId('composer-button')) })
    expect(onSend).toHaveBeenCalledWith('')
  })

  it('viser permissions, model og research som ikoner i den rækkefølge', async () => {
    const onResearchModeChange = jest.fn()
    const screen = await render(
      <Composer
        onSend={jest.fn()}
        onStop={jest.fn()}
        modelLabel="DeepSeek V4 Flash"
        onPressModel={jest.fn()}
        permission="ask"
        onPressPermission={jest.fn()}
        researchMode={false}
        onResearchModeChange={onResearchModeChange}
      />
    )
    await openComposer(screen)

    const row = screen.getByTestId('composer-control-row')
    const ids = row.props.children
      .filter(Boolean)
      .map((child: { props: { testID?: string } }) => child.props.testID)
      .filter(Boolean)
    expect(ids).toEqual(['composer-permission', 'composer-model', 'composer-research'])
    expect(screen.queryByText('Research')).toBeNull()
    expect(screen.queryByText('DeepSeek V4 Flash')).toBeNull()

    await act(async () => { fireEvent.press(screen.getByTestId('composer-research')) })

    expect(onResearchModeChange).toHaveBeenCalledWith(true)
  })

  it('bruger mikrofon til diktering og bølge til samtale', async () => {
    const onDictate = jest.fn()
    const onConversation = jest.fn()
    const screen = await render(
      <Composer onSend={jest.fn()} onStop={jest.fn()} onDictate={onDictate} onConversation={onConversation} />
    )

    await act(async () => { fireEvent.press(screen.getByLabelText('Dikter')) })
    await act(async () => { fireEvent.press(screen.getByLabelText('Start samtale')) })

    expect(onDictate).toHaveBeenCalledTimes(1)
    expect(onConversation).toHaveBeenCalledTimes(1)
  })

  it('viser permissions som et ikon og har ikke Chat/Code-badget', async () => {
    const onPressPermission = jest.fn()
    const screen = await render(
      <Composer
        onSend={jest.fn()}
        onStop={jest.fn()}
        permission="ask"
        onPressPermission={onPressPermission}
      />
    )
    await openComposer(screen)

    expect(screen.queryByText('Chat')).toBeNull()
    expect(screen.queryByText('Code')).toBeNull()
    await act(async () => { fireEvent.press(screen.getByTestId('composer-permission')) })

    expect(screen.getByTestId('icon-ShieldCheck')).toBeTruthy()
    expect(onPressPermission).toHaveBeenCalledTimes(1)
  })
})

describe('Composer: tekst udefra', () => {
  it('lægger delt tekst TIL det man har skrevet — ikke i stedet for', async () => {
    const screen = await render(
      <Composer onSend={jest.fn()} onStop={jest.fn()} indsaet={{ tekst: '', n: 0 }} />
    )
    await openComposer(screen)
    await act(async () => {
      fireEvent.changeText(screen.getByTestId('composer-input'), 'jeg står')
    })
    await act(async () => {
      screen.rerender(
        <Composer onSend={jest.fn()} onStop={jest.fn()} indsaet={{ tekst: 'Jeg er her: Aarhus', n: 1 }} />
      )
    })
    expect(screen.getByTestId('composer-input').props.value).toBe('jeg står\nJeg er her: Aarhus')
  })

  it('indsætter SAMME tekst igen — tælleren er signalet, ikke strengen', async () => {
    const screen = await render(
      <Composer onSend={jest.fn()} onStop={jest.fn()} indsaet={{ tekst: '', n: 0 }} />
    )
    await openComposer(screen)
    for (const n of [1, 2]) {
      await act(async () => {
        screen.rerender(
          <Composer onSend={jest.fn()} onStop={jest.fn()} indsaet={{ tekst: 'kl. 9', n }} />
        )
      })
    }
    expect(screen.getByTestId('composer-input').props.value).toBe('kl. 9\nkl. 9')
  })

  it('rører ikke feltet uden et nyt signal', async () => {
    const screen = await render(
      <Composer onSend={jest.fn()} onStop={jest.fn()} indsaet={{ tekst: 'noget', n: 4 }} />
    )
    await openComposer(screen)
    const foer = screen.getByTestId('composer-input').props.value
    await act(async () => {
      screen.rerender(
        <Composer onSend={jest.fn()} onStop={jest.fn()} indsaet={{ tekst: 'noget', n: 4 }} />
      )
    })
    expect(screen.getByTestId('composer-input').props.value).toBe(foer)
  })

  it('lægger dikteret tekst i kladden uden at sende', async () => {
    const onSend = jest.fn()
    const screen = await render(
      <Composer onSend={onSend} onStop={jest.fn()} indsaet={{ tekst: '', n: 0 }} />
    )
    await openComposer(screen)
    fireEvent.changeText(screen.getByTestId('composer-input'), 'eksisterende')
    await act(async () => {
      screen.rerender(
        <Composer onSend={onSend} onStop={jest.fn()} indsaet={{ tekst: 'dikteret tekst', n: 1 }} />
      )
    })
    expect(screen.getByTestId('composer-input').props.value).toBe('eksisterende\ndikteret tekst')
    expect(onSend).not.toHaveBeenCalled()
  })
})
