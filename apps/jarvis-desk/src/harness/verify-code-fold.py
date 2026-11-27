from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width":1000,"height":1100})
    page.goto('http://127.0.0.1:5199/src/harness/fold-audit.html')
    page.wait_for_load_state('networkidle')
    page.wait_for_selector('.rv-svar',state='attached')
    def stage(n): page.evaluate('(n)=>window.__auditStage(n)',n)
    def measure(label):
        v=page.evaluate('''() => ({
            texts:Array.from(document.querySelectorAll('.rv-svar p')).map(e=>({text:e.textContent, y:e.getBoundingClientRect().y})),
            rounds:Array.from(document.querySelectorAll('.rv-sen-runde')).map(e=>({height:e.getBoundingClientRect().height, opacity:getComputedStyle(e).opacity, phase:e.dataset.samles})),
            sameAnswer:window.answerNode ? window.answerNode===document.querySelector('.rv-svar-tekst'):null,
            fold:document.querySelector('.rv-gruppe-ydre')?.dataset.aaben
        })''')
        print(json.dumps({"stage":label,**v},ensure_ascii=False),flush=True)
        return v
    stage(-1)
    page.wait_for_selector('.rv-modelventer .jarvis-pulse.is-working')
    assert page.locator('.rv-tur').count() == 0
    assert page.locator('.rv-modelventer').inner_text() == ''
    assert page.locator('.rv-modelventer rect').first.evaluate('(e)=>getComputedStyle(e).animationName') == 'jarvis-puls'
    print('initial code state: animated Jarvis mark, no flat Working label', flush=True)
    stage(2);page.wait_for_timeout(600)
    page.evaluate("window.answerNode=document.querySelector('.rv-svar-tekst')")
    before=measure('live rounds')
    stage(3);page.wait_for_timeout(140)
    mid=measure('during exit')
    assert mid['sameAnswer']
    assert any(float(r['opacity'])<1 and r['height']>0 for r in mid['rounds'])
    page.wait_for_timeout(450)
    after=measure('after exit')
    assert after['sameAnswer']
    assert all(r['height']<1 for r in after['rounds'])
    assert any('SEN SYNTESE A' in t['text'] for t in after['texts'])
    assert any('SEN SYNTESE B' in t['text'] for t in after['texts'])
    stage(4);page.wait_for_timeout(500)
    saved=measure('saved phases')
    assert saved['sameAnswer']
    assert any('SLUTBESKEDEN' in t['text'] for t in saved['texts'])
    page.screenshot(path='/tmp/jarvis-fold-fixed.png',full_page=True)
    page.get_by_role('button',name='Pacing',exact=True).click()
    page.wait_for_timeout(100)
    stage(2);page.wait_for_timeout(70)
    behind=measure('server ahead of pacing')
    assert not behind['rounds']
    assert sum(len(t['text']) for t in behind['texts'])<700
    stage(3);page.wait_for_timeout(70)
    behind_done=measure('server done, pacing behind')
    assert not behind_done['rounds']
    assert not behind_done['texts'], 'Unreached commentary must stay in work even after server stop'
    page.wait_for_timeout(4500)
    done=measure('pacing caught up and exit finished')
    assert all(r['height']<1 for r in done['rounds'])
    assert any('SEN SYNTESE B' in t['text'] for t in done['texts'])
    print('PASS: text survives; only work fades/collapses; pacing gates later work; persisted marker survives')
    browser.close()
