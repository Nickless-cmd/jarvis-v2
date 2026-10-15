import { useContext } from 'react'
import { ChatFlowContext, type ChatFlowContextValue } from '../contexts/ChatFlowContext'

export function useChatFlow(): ChatFlowContextValue {
  return useContext(ChatFlowContext)
}
