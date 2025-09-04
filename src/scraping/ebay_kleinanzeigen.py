from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from src.scraping.selectors import selector_accept, selector_search

SEARCH_TERM = "Gaming PC"
HEADLESS = False

def fill_search(page, term):
    # Mehrere robuste Wege, das Suchfeld zu finden:
    tried = 0
    selectors = [
        lambda: page.get_by_placeholder("Was suchst du?"),
        lambda: page.locator("input[name='keywords']").first,
        lambda: page.get_by_role("textbox").filter(has_text="").first,
        lambda: page.locator("input[type='search']").first,
    ]
    for fn in selectors:
        try:
            el = fn()
            el.wait_for(timeout=2000)
            el.fill(term)
            print(f"Suchfeld gefunden mit Methode {tried + 1}")
            return True
        except Exception:
            tried += 1
    return False

def fill_location():
    pass

def main_search():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        page.set_default_timeout(10000)

        # 1) Startseite
        page.goto("https://www.kleinanzeigen.de/")

        # ggf. Cookie-Banner wegklicken (best effort)
        for sel in selector_accept:
            try:
                if page.locator(sel).first.is_visible():
                    page.locator(sel).first.click()
                    break
            except Exception:
                pass

        # 2) Suchfeld befüllen
        if not fill_search(page, SEARCH_TERM):
            raise RuntimeError("Kein Suchfeld gefunden – Selektoren anpassen?")

        # 3) Suche absenden
        # Enter-Submit oder auf Suchbutton klicken (beides versuchen)
        submitted = False
        try:
            page.keyboard.press("Enter")
            submitted = True
        except Exception:
            pass
        if not submitted:
            for sel in selector_search:
                try:
                    if page.locator(sel).first.is_enabled():
                        page.locator(sel).first.click()
                        submitted = True
                        break
                except Exception:
                    pass
        if not submitted:
            raise RuntimeError("Suche konnte nicht abgesendet werden.")

        # 4) Auf Ergebnisse warten und erstes Resultat öffnen
        try:
            page.wait_for_selector("a[href*='/s-anzeige/']", timeout=15000) # Kleinanzeigen Links sehen so aus
        except PWTimeout:
            raise RuntimeError("Keine Ergebnisse gefunden oder Seite zu langsam.")

        first_result = page.locator("a[href*='/s-anzeige/']").first
        # Titel vor dem Klick sichern, falls möglich
        title_preview = None
        try:
            title_preview = first_result.locator("h2, span, div").first.inner_text(timeout=1000) # Name der Anzeige aus dem html code
        except Exception:
            pass

        first_url = first_result.get_attribute("href")
        if first_url and first_url.startswith("/"):
            first_url = "https://www.kleinanzeigen.de" + first_url

        first_result.click()

        # 5) Auf der Detailseite Titel + URL ausgeben
        page.wait_for_load_state("domcontentloaded")
        try:
            ad_title = page.locator("h1, [data-testid='ad-title']").first.inner_text(timeout=5000)
        except Exception:
            ad_title = title_preview or "(kein Titel gefunden)"

        print("=== Erstes Ergebnis ===")
        print("Titel:", " ".join(ad_title.split()))
        print("URL:  ", page.url if page.url else first_url)

        # Fenster offen lassen, damit du schauen kannst
        input("\nDrück Enter zum Schließen… ")
        browser.close()
