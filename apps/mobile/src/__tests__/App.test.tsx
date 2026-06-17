import React from 'react'
import { render, waitFor } from '@testing-library/react-native'
import App from '../App'

let mockAuthState: {
  config: { apiBaseUrl: string; authToken: string } | null
  loading: boolean
} = {
  config: null,
  loading: false
}

let mockProviderInstance = 0

jest.mock('../screens/LoginScreen', () => ({
  LoginScreen: () => {
    const ReactLib = jest.requireActual('react')
    const { Text } = jest.requireActual('react-native')
    return ReactLib.createElement(Text, null, 'Login screen')
  }
}))

jest.mock('../state/AuthContext', () => {
  const ReactLib = jest.requireActual('react')

  return {
    AuthProvider: ({ children }: { children: React.ReactNode }) =>
      ReactLib.createElement(ReactLib.Fragment, null, children),
    useAuth: () => mockAuthState
  }
})

jest.mock('../state/SessionContext', () => {
  const ReactLib = jest.requireActual('react')
  const { Text } = jest.requireActual('react-native')

  return {
    SessionProvider: ({ children }: { children: React.ReactNode }) => {
      const [instance] = ReactLib.useState(() => {
        mockProviderInstance += 1
        return mockProviderInstance
      })

      return ReactLib.createElement(
        ReactLib.Fragment,
        null,
        ReactLib.createElement(Text, null, `session-provider-${instance}`),
        children
      )
    }
  }
})

beforeEach(() => {
  mockAuthState = {
    config: null,
    loading: false
  }
  mockProviderInstance = 0
})

it('does not mount session state while signed out', async () => {
  const screen = await render(<App />)

  expect(screen.getByText('Login screen')).toBeTruthy()
  expect(screen.queryByText('session-provider-1')).toBeNull()
})

it('remounts session state when the auth token changes', async () => {
  mockAuthState = {
    config: {
      apiBaseUrl: 'https://api.srvlab.dk/',
      authToken: 'token-a'
    },
    loading: false
  }

  const screen = await render(<App />)

  expect(screen.getByText('session-provider-1')).toBeTruthy()

  mockAuthState = {
    config: {
      apiBaseUrl: 'https://api.srvlab.dk/',
      authToken: 'token-b'
    },
    loading: false
  }

  screen.rerender(<App />)

  await waitFor(() => expect(screen.queryByText('session-provider-1')).toBeNull())
  expect(screen.getByText('session-provider-2')).toBeTruthy()
})
