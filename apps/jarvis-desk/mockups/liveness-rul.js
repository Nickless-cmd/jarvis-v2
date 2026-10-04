/*
 * Rullende tal i liveness-linjen — preview.
 *
 * Samme mekanik som mockup'en, men generisk: hvert CIFER er et hjul, og
 * hjulet kan rulle BAADE op og ned. Det er kravet her, fordi token-tallet
 * kan falde (kontekst-komprimering), hvor uret kun stiger.
 *
 *   stigning, lige vej      -> sporet glider op, naeste ciffer kommer nedefra
 *   stigning, baerende 9->0 -> rul frem gennem en dublet-0 og snap tilbage
 *   fald                    -> sporet glider ned, cifferet kommer ovenfra
 */
;(function () {
  'use strict'

  function Ciffer(el, cyklus) {
    this.el = el
    this.cyklus = cyklus
    this.indeks = 0

    var spor = document.createElement('div')
    spor.className = 'hjul-spor'
    for (var i = 0; i <= cyklus; i++) {
      var b = document.createElement('span')
      b.textContent = String(i % cyklus)
      spor.appendChild(b)
    }
    el.appendChild(spor)
    this.spor = spor
    this._snap(0)
  }

  Ciffer.prototype._saet = function (i) {
    this.indeks = i
    this.spor.style.transform = 'translateY(-' + i + 'em)'
  }

  Ciffer.prototype._snap = function (i) {
    this.spor.style.transition = 'none'
    this._saet(i)
    void this.spor.offsetHeight // gennemtving reflow, saa naeste rul starter herfra
    this.spor.style.transition = ''
  }

  Ciffer.prototype.saet = function (v, retning) {
    v = ((v % this.cyklus) + this.cyklus) % this.cyklus
    // Staar hjulet paa dubletten, er en vikling i gang: afslut den foerst.
    if (this.indeks === this.cyklus) this._snap(0)

    var nu = this.indeks
    if (v === nu) return

    if (retning === 'ned') { this._saet(v); return } // fald: sporet glider ned
    if (v > nu) { this._saet(v); return } // stigning, lige vej

    // Stigning hvor cifferet gaar 9 -> 0: rul FREMME gennem dubletten.
    var selv = this
    this._saet(this.cyklus)
    var faerdig = function () {
      selv.spor.removeEventListener('transitionend', faerdig)
      selv._snap(0)
    }
    this.spor.addEventListener('transitionend', faerdig)
    setTimeout(function () {
      if (selv.indeks === selv.cyklus) {
        selv.spor.removeEventListener('transitionend', faerdig)
        selv._snap(0)
      }
    }, 900)
  }

  /* Et tal som en raekke ciffer-hjul. Ikke-cifre (':', '.', 'k') staar stille. */
  function Rulle(el) {
    this.el = el
    this.hjul = []
    this.form = null
  }

  Rulle.prototype.vis = function (tekst, retning, cyklusser) {
    var tegn = String(tekst).split('')
    var form = tegn
      .map(function (c, i) {
        if (!/\d/.test(c)) return c
        var k = cyklusser && cyklusser[i] ? cyklusser[i] : 10
        return 'd' + k
      })
      .join('|')

    if (form !== this.form) {
      this.el.innerHTML = ''
      this.hjul = []
      for (var i = 0; i < tegn.length; i++) {
        if (/\d/.test(tegn[i])) {
          var d = document.createElement('span')
          d.className = 'hjul'
          this.el.appendChild(d)
          this.hjul.push({ node: d, ciffer: new Ciffer(d, cyklusser && cyklusser[i] ? cyklusser[i] : 10) })
        } else {
          var s = document.createElement('span')
          s.className = 'tegn'
          s.textContent = tegn[i]
          this.el.appendChild(s)
          this.hjul.push({ node: s, ciffer: null })
        }
      }
      this.form = form
    }

    for (var j = 0; j < tegn.length; j++) {
      var h = this.hjul[j]
      if (h && h.ciffer) h.ciffer.saet(Number(tegn[j]), retning)
    }
  }

  // ── Ur ──────────────────────────────────────────────────────────────
  var ur = new Rulle(document.getElementById('ur'))
  var forrigeSek = 0

  function visUr(sek) {
    var m = Math.floor(sek / 60)
    var s = sek % 60
    var tekst = String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0')
    ur.vis(tekst, sek >= forrigeSek ? 'op' : 'ned', [10, 10, null, 6, 10])
    forrigeSek = sek
  }

  // ── Token-tal ───────────────────────────────────────────────────────
  function fmtTokens(n) {
    return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n)
  }

  function maaler(id, cyklusVenstre) {
    var r = new Rulle(document.getElementById(id))
    var forrige = 0
    return function (n) {
      r.vis(fmtTokens(n), n >= forrige ? 'op' : 'ned', cyklusVenstre)
      forrige = n
    }
  }

  var visTokA = maaler('tokA', null)
  var visTokB = maaler('tokB', null)
  var visTokC = maaler('tokC', null)

  // ── Simulation ──────────────────────────────────────────────────────
  var start = Date.now()
  var sidsteB = 0
  var sidsteC = 0

  function tick() {
    var t = (Date.now() - start) / 1000
    visUr(Math.floor(t))

    // ~60 tokens/sek — realistisk under streaming.
    var n = Math.floor(t * 60)

    visTokA(n) // ulaempet: ruller ved HVER aendring
    if (Date.now() - sidsteB > 250) { sidsteB = Date.now(); visTokB(n) } // ~4/s
    if (Date.now() - sidsteC > 1000) { sidsteC = Date.now(); visTokC(n) } // ~1/s
  }

  setInterval(tick, 60)
  tick()

  // ── Maaling ─────────────────────────────────────────────────────────
  window.__maal = function () {
    var ur_el = document.getElementById('ur')
    var hjul = document.querySelector('.hjul')
    var linje = document.getElementById('linjeB')
    var cs = linje ? getComputedStyle(linje) : null
    return {
      ur_tekst: ur_el ? ur_el.parentElement.textContent.trim() : null,
      ur_rect: ur_el ? JSON.stringify(ur_el.getBoundingClientRect()) : null,
      hjul_rect: hjul ? JSON.stringify(hjul.getBoundingClientRect()) : null,
      hjul_h: hjul ? getComputedStyle(hjul).height : null,
      linje_fs: cs ? cs.fontSize : null,
      linje_lh: cs ? cs.lineHeight : null,
      tokA: document.getElementById('tokA').parentElement.textContent.trim(),
      tokB: document.getElementById('tokB').parentElement.textContent.trim(),
      tokC: document.getElementById('tokC').parentElement.textContent.trim(),
    }
  }
})()
