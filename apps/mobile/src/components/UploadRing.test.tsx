import { render } from '@testing-library/react-native'
import { UploadRing, samletUploadAndel } from './UploadRing'

// Fremdriften blev maalt hele tiden - uploadAttachment kalder tilbage med en
// broekdel - men den stod som et lille tal paa miniaturen. Den store knap blev
// ved med at vaere boelge-ikonet, og det er den knap oejet hviler paa mens man
// venter. Bjoern: "ellers virker det bare som om appen haenger".

describe('samletUploadAndel', () => {
  it('null naar ingenting uploader — ikke 0', () => {
    // Forskellen er hele pointen: 0 ville tegne en tom ring paa skaermen
    // naar der slet ikke sker noget.
    expect(samletUploadAndel([])).toBeNull()
    expect(samletUploadAndel(undefined)).toBeNull()
    expect(samletUploadAndel([{ status: 'done', progress: 1 }])).toBeNull()
  })

  it('gennemsnit over dem der er i gang', () => {
    // Sender man tre filer, er det den SAMLEDE ventetid man maerker.
    expect(samletUploadAndel([
      { status: 'uploading', progress: 0.2 },
      { status: 'uploading', progress: 0.8 },
    ])).toBeCloseTo(0.5)
  })

  it('faerdige filer traekker ikke gennemsnittet ned', () => {
    expect(samletUploadAndel([
      { status: 'done', progress: 1 },
      { status: 'uploading', progress: 0.4 },
    ])).toBeCloseTo(0.4)
  })

  it('vaerdier uden for [0,1] klemmes', () => {
    expect(samletUploadAndel([{ status: 'uploading', progress: 5 }])).toBe(1)
    expect(samletUploadAndel([{ status: 'uploading', progress: -3 }])).toBe(0)
  })

  it('manglende progress regnes som 0, ikke som NaN', () => {
    expect(samletUploadAndel([{ status: 'uploading' }])).toBe(0)
  })
})

describe('UploadRing', () => {
  it('siger procenten hoejt for skaermlaesere', async () => {
    const s = await render(<UploadRing andel={0.42} />)
    expect(s.getByLabelText('Uploader 42 procent')).toBeTruthy()
  })

  it('en ugyldig andel vaelter ikke ringen', async () => {
    const s = await render(<UploadRing andel={Number.NaN} />)
    expect(s.getByLabelText('Uploader 0 procent')).toBeTruthy()
  })

  it('Composer bytter boelgen ud med ringen under upload', () => {
    // Koblingen. Ringen kan vaere rigtig og knappen stadig vise en boelge —
    // og saa ser appen stadig ud som om den haenger.
    const kilde = require('fs').readFileSync(
      require('path').join(__dirname, 'Composer.tsx'), 'utf8') as string
    expect(kilde).toContain('uploadAndel !== null')
    expect(kilde).toContain('<UploadRing')
  })
})
