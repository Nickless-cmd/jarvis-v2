import { forael, underSti } from './workspaceApi'

it('sammensaetter uden dobbelt skraastreg', () => {
  // «/» + «home» gav «//home», og operator_list_dir svarer ikke det samme
  // paa de to.
  expect(underSti('/', 'home')).toBe('/home')
  expect(underSti('/home/bs/', 'projekt')).toBe('/home/bs/projekt')
  expect(underSti('/home/bs', 'projekt')).toBe('/home/bs/projekt')
})

it('gaar ét niveau op', () => {
  expect(forael('/home/bs/projekt')).toBe('/home/bs')
  expect(forael('/home/bs/projekt/')).toBe('/home/bs')
  expect(forael('/home')).toBe('/')
})

it('roden er sin egen foraelder — man kan ikke gaa over «/»', () => {
  expect(forael('/')).toBe('/')
  expect(forael('')).toBe('/')
})
