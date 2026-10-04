/*
 * min:sek — rullende tal.
 *
 * Fire ciffer-hjul, ét pr. ciffer: min-tiere, min-enere, sek-tiere, sek-enere.
 * Hvert hjul ruller FORLÆNS gennem sin egen cyklus, som et mekanisk
 * kilometertæller-hjul: når sek-enere går 9 → 0, ruller den op gennem en
 * dublet-0 og sættes tilbage til den rigtige 0 bagefter — den springer ikke
 * baglæns gennem 8-7-6.
 *
 * Sek-tiere har cyklus 6 (0-5), de øvrige 10 (0-9). Det er dét der gør at
 * 59 → 00 ruller rigtigt i stedet for at vise et 6-tal undervejs.
 */
;(function () {
  'use strict'

  /** Ét ciffer-hjul. `cyklus` er antallet af tal på hjulet (6 eller 10). */
  function Hjul(el, cyklus) {
    this.el = el
    this.cyklus = cyklus
    this.vaerdi = 0
    this.indeks = 0

    var spor = document.createElement('div')
    spor.className = 'strip'
    // cyklus+1 brikker: 0..cyklus-1 plus en dublet-0 til at rulle ind i.
    for (var i = 0; i <= cyklus; i++) {
      var b = document.createElement('span')
      b.textContent = String(i % cyklus)
      spor.appendChild(b)
    }
    el.appendChild(spor)
    this.spor = spor
    // Start-positionen sættes gennem `_snap`, så den inline `transition: none`
    // ryddes igen. Blev den hængende, døde HELE rullingen: CSS-reglen på
    // `.strip` blev overtrumfet, og `transitionend` fyrede aldrig ved vikling.
    this._snap(0)
  }

  Hjul.prototype._saet = function (indeks) {
    this.indeks = indeks
    this.spor.style.transform = 'translateY(-' + indeks + 'em)'
  }

  /** Flyt uden animation — bruges efter en rullet dublet, og ved nulstilling. */
  Hjul.prototype._snap = function (indeks) {
    this.spor.style.transition = 'none'
    this._saet(indeks)
    void this.spor.offsetHeight // gennemtving en reflow, så næste rul starter herfra
    this.spor.style.transition = ''
  }

  Hjul.prototype.set = function (v, animeret) {
    if (animeret === undefined) animeret = true
    v = ((v % this.cyklus) + this.cyklus) % this.cyklus

    // Midt i en rullet dublet står hjulet allerede på 0. Vi rører det ikke.
    if (this.indeks === this.cyklus) { this.vaerdi = v; return }
    if (v === this.vaerdi) return

    var forrige = this.vaerdi
    this.vaerdi = v

    if (!animeret) { this._snap(v); return }
    if (v > forrige) { this._saet(v); return } // normal rul fremad

    // Vikling: 9 → 0. Rul ind i dublet-0, og sæt så tilbage til den ægte 0.
    var selv = this
    this._saet(this.cyklus)
    var faerdig = function () {
      selv.spor.removeEventListener('transitionend', faerdig)
      selv._snap(0)
    }
    this.spor.addEventListener('transitionend', faerdig)
    // Sikkerhedsnet: udebliver transitionend (fx et skjult panel), så snap alligevel.
    setTimeout(function () {
      if (selv.indeks === selv.cyklus) {
        selv.spor.removeEventListener('transitionend', faerdig)
        selv._snap(0)
      }
    }, 800)
  }

  // ── Hjulene ────────────────────────────────────────────────────────
  function byggHjul(container, cyklus, antal) {
    var ud = []
    for (var i = 0; i < antal; i++) {
      var d = document.createElement('div')
      d.className = 'digit'
      container.appendChild(d)
      ud.push(new Hjul(d, cyklus))
    }
    return ud
  }

  var minTiere = byggHjul(document.getElementById('minutter'), 10, 1)[0]
  var minEnere = byggHjul(document.getElementById('minutter'), 10, 1)[0]
  var sekTiere = byggHjul(document.getElementById('sekunder'), 6, 1)[0]
  var sekEnere = byggHjul(document.getElementById('sekunder'), 10, 1)[0]

  var vmin = document.getElementById('vmin')
  var vsek = document.getElementById('vsek')
  var vialt = document.getElementById('vialt')
  var colon = document.getElementById('colon')
  var clock = document.getElementById('clock')
  var btnKoer = document.getElementById('btnKoer')

  // ── Uret ───────────────────────────────────────────────────────────
  // Vi regner altid ud fra et tidsstempel, ikke ved at tælle ticks op —
  // ellers driver det, og et tabt tick bliver et tabt sekund.
  var akkumuleret = 0 // sekunder fra før en pause
  var startet = 0 // Date.now() da vi sidst satte i gang
  var koerer = false

  function iAlt() {
    return akkumuleret + (koerer ? Math.floor((Date.now() - startet) / 1000) : 0)
  }

  var vistSek = -1

  function vis(total) {
    if (total === vistSek) return
    var skiftedeSekund = Math.floor(total) !== Math.floor(vistSek)
    vistSek = total

    var m = Math.floor(total / 60)
    var s = total % 60
    minTiere.set(Math.floor(m / 10) % 10)
    minEnere.set(m % 10)
    sekTiere.set(Math.floor(s / 10) % 10)
    sekEnere.set(s % 10)

    vmin.textContent = String(m)
    vsek.textContent = String(s)
    vialt.textContent = String(total)
    clock.setAttribute('aria-label', String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0'))

    // Kolon-pulsen: ét svagt blink pr. sekund, så uret føles levende.
    if (skiftedeSekund && koerer) {
      colon.classList.add('tik')
      setTimeout(function () { colon.classList.remove('tik') }, 180)
    }
  }

  setInterval(function () { vis(iAlt()) }, 250)
  vis(0)

  // ── Kontroller ─────────────────────────────────────────────────────
  function saetKoerer(ny) {
    if (ny === koerer) return
    if (ny) {
      startet = Date.now()
      koerer = true
    } else {
      akkumuleret = iAlt()
      koerer = false
    }
    btnKoer.textContent = koerer ? 'Pause' : 'Start'
    btnKoer.setAttribute('aria-pressed', koerer ? 'true' : 'false')
  }

  btnKoer.addEventListener('click', function () { saetKoerer(!koerer) })

  document.getElementById('btnNul').addEventListener('click', function () {
    saetKoerer(false)
    akkumuleret = 0
    vistSek = -1
    // Nulstilling hopper direkte — ingen rulning gennem hele skalaen.
    minTiere.set(0, false); minEnere.set(0, false)
    sekTiere.set(0, false); sekEnere.set(0, false)
    vis(0)
  })

  function springFrem(sekunder) {
    akkumuleret = iAlt() + sekunder
    startet = Date.now()
    vis(iAlt())
  }
  document.getElementById('btnTi').addEventListener('click', function () { springFrem(10) })
  document.getElementById('btnMin').addEventListener('click', function () { springFrem(60) })
})()
