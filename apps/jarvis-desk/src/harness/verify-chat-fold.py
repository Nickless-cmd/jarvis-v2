"""Real-browser audit: ordered merge, stable answer DOM and independent pacing."""
import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1000, "height": 1100})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:5199/src/harness/chat-fold-audit.html')
    page.wait_for_load_state('networkidle')
    def stage(n): page.evaluate('(n)=>window.__auditStage(n)', n)
    def measure(label):
        value = page.evaluate('''() => ({
          fold:document.querySelector('.chat-flow-gruppe-ydre')?.dataset.aaben,
          same:window.answerNode ? window.answerNode===document.querySelector('.chat-flow-answer-text'):null,
          texts:[...document.querySelectorAll('.chat-flow-answer-text')].map(e=>({text:e.textContent,y:e.getBoundingClientRect().y,opacity:getComputedStyle(e).opacity})),
          rounds:[...document.querySelectorAll('.chat-flow-answer > .chat-flow-runde')].map(e=>({height:e.getBoundingClientRect().height,opacity:getComputedStyle(e).opacity,phase:e.dataset.levetid}))
        })''')
        print(json.dumps({'stage': label, **value}, ensure_ascii=False), flush=True)
        return value
    stage(2)
    page.wait_for_timeout(600)
    page.evaluate("window.answerNode=document.querySelector('.chat-flow-answer-text')")
    before = measure('live')
    assert len(before['texts']) == 3 and len(before['rounds']) == 2
    assert before['fold'] == 'false'
    stage(3)
    page.wait_for_timeout(140)
    mid = measure('exit')
    assert mid['same'] and all(t['opacity'] == '1' for t in mid['texts'])
    assert all(0 < float(r['opacity']) < 1 and r['height'] > 0 for r in mid['rounds'])
    page.wait_for_timeout(500)
    after = measure('merged')
    assert after['same'] and all(r['height'] < 1 for r in after['rounds'])
    assert after['texts'][1]['y'] < before['texts'][1]['y']
    assert after['texts'][2]['y'] < before['texts'][2]['y']
    page.locator('.rv-tur').click()
    page.wait_for_timeout(500)
    assert page.locator('.chat-flow-work-details .rv-arbejdsrunde').count() == 2
    page.screenshot(path='/tmp/jarvis-chat-fold-details.png', full_page=True)
    page.get_by_role('button', name='Pacing', exact=True).click()
    stage(2)
    page.wait_for_timeout(80)
    early = measure('server ahead')
    assert early['fold'] == 'true' and len(early['rounds']) == 0
    stage(3)
    page.wait_for_timeout(80)
    assert measure('server done before pace')['fold'] == 'true'
    page.wait_for_function("document.querySelector('.chat-flow-answer-text')?.textContent.includes('SLUTBESKEDEN')", timeout=30000)
    assert measure('first paced answer')['fold'] == 'false'
    assert not errors, errors
    browser.close()
