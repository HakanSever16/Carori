from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import os
import re

def get_user_car_info():
    
    models_raw = input("Model?: ").strip()

    
    models = [m.strip() for m in models_raw.split(',') if m.strip()]
    if not models:
        
        models = [""]

    return {
        "year": "",
        "brand": "",
        "models": models,
        "engine": "",
        "body": ""
    }


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _click_best_result(driver, brand, model, wait=10):
    
    model_norm = _normalize(model)
    brand_norm = _normalize(brand)

    
    try:
        elements = WebDriverWait(driver, wait).until(
            EC.presence_of_all_elements_located((By.XPATH, "//a"))
        )
    except TimeoutException:
        return False

    for el in elements:
        try:
            text = _normalize(el.text)
            
            if model_norm and model_norm in text:
                try:
                    el.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", el)
                return True
            
            if brand_norm and model_norm and (brand_norm + " " + model_norm) in text:
                try:
                    el.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", el)
                return True
        except Exception:
            continue

    
    try:
        
        candidates = sorted(elements, key=lambda e: len(_normalize(e.text)), reverse=True)
        if candidates:
            try:
                candidates[0].click()
            except Exception:
                driver.execute_script("arguments[0].click();", candidates[0])
            return True
    except Exception:
        pass

    return False


def _extract_largest_table_text(driver):
    
    tables = driver.find_elements(By.XPATH, "//table")
    best_table = None
    best_rows = 0
    for t in tables:
        try:
            rows = t.find_elements(By.XPATH, ".//tr")
            if len(rows) > best_rows:
                best_rows = len(rows)
                best_table = t
        except Exception:
            continue

    if not best_table:
        
        try:
            body_text = driver.find_element(By.TAG_NAME, 'body').text
            return '\n'.join([line.strip() for line in body_text.splitlines() if line.strip()][:40])
        except Exception:
            return ''

    
    rows = best_table.find_elements(By.XPATH, ".//tr")
    out_lines = []
    for r in rows:
        try:
            cells = r.find_elements(By.XPATH, ".//th|.//td")
            line = ' | '.join([c.text.strip() for c in cells if c.text.strip()])
            if line:
                out_lines.append(line)
        except Exception:
            continue

    return '\n'.join(out_lines)


def _extract_fuel_info(text: str):
    
    if not text:
        return []

    keywords = [
        'fuel', 'consumption', 'consumo', 'verbrauch', 'tank', 'l/100', 'mpg',
        'fuel type', 'fuel tank', 'tank capacity', 'combined', 'city', 'highway',
        'average consumption'
    ]

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    found = []
    for ln in lines:
        low = ln.lower()
        for k in keywords:
            if k in low:
                if ln not in found:
                    found.append(ln)
                break

    
    if not found:
        for ln in lines:
            low = ln.lower()
            if 'l/100' in low or 'km/l' in low or 'mpg' in low:
                if ln not in found:
                    found.append(ln)

    return found


def _to_float(num_str: str):
    try:
        return float(num_str.replace(',', '.'))
    except Exception:
        return None


def _extract_consumptions_from_line(line: str):
    
    if not line:
        return []

    parts = [p.strip() for p in re.split(r"\s*\|\s*|\s*;\s*", line) if p.strip()]
    
    has_direct_l100 = bool(re.search(r"\d+[\.,]?\d*\s*l\s*/\s*100", line.lower()))
    out = []
    for p in parts:
        low = p.lower()
        
        m = re.search(r"(\d+[\.,]?\d*)\s*l\s*/\s*100\s*km", low)
        if m:
            val = _to_float(m.group(1))
            if val is not None:
                category = 'combined'
                if any(k in low for k in ['city', 'urban']):
                    category = 'city'
                elif any(k in low for k in ['highway', 'extra', 'motorway', 'country', 'rural']):
                    category = 'highway'
                out.append({'label': 'l/100 km', 'value': val, 'category': category})
                continue

        
        m = None
        if not has_direct_l100:
            m = re.search(r"(\d+[\.,]?\d*)\s*km\s*/\s*l", low) or re.search(r"(\d+[\.,]?\d*)\s*kmperl", low)
        if m:
            km_per_l = _to_float(m.group(1))
            if km_per_l and km_per_l != 0:
                l_per_100 = 100.0 / km_per_l
                category = 'combined'
                if any(k in low for k in ['city', 'urban']):
                    category = 'city'
                elif any(k in low for k in ['highway', 'extra', 'motorway', 'country', 'rural']):
                    category = 'highway'
                out.append({'label': 'km/l -> l/100 km', 'value': l_per_100, 'category': category})
                continue

        
        m = None
        if not has_direct_l100:
            m = re.search(r"(\d+[\.,]?\d*)\s*us\s*mpg", low)
        if m:
            mpg = _to_float(m.group(1))
            if mpg and mpg != 0:
                l_per_100 = 235.214583 / mpg
                category = 'combined'
                if any(k in low for k in ['city', 'urban']):
                    category = 'city'
                elif any(k in low for k in ['highway', 'extra', 'motorway', 'country', 'rural']):
                    category = 'highway'
                out.append({'label': 'US mpg -> l/100 km', 'value': l_per_100, 'category': category})
                continue
        m = None
        if not has_direct_l100:
            m = re.search(r"(\d+[\.,]?\d*)\s*uk\s*mpg", low)
        if m:
            mpg = _to_float(m.group(1))
            if mpg and mpg != 0:
                l_per_100 = 282.480936 / mpg
                category = 'combined'
                if any(k in low for k in ['city', 'urban']):
                    category = 'city'
                elif any(k in low for k in ['highway', 'extra', 'motorway', 'country', 'rural']):
                    category = 'highway'
                out.append({'label': 'UK mpg -> l/100 km', 'value': l_per_100, 'category': category})
                continue

        
        m = None
        if not has_direct_l100:
            m = re.search(r"(\d+[\.,]?\d*)\s*mpg", low)
        if m:
            mpg = _to_float(m.group(1))
            if mpg and mpg != 0:
                l_per_100 = 235.214583 / mpg
                category = 'combined'
                if any(k in low for k in ['city', 'urban']):
                    category = 'city'
                elif any(k in low for k in ['highway', 'extra', 'motorway', 'country', 'rural']):
                    category = 'highway'
                out.append({'label': 'mpg(assumed US) -> l/100 km', 'value': l_per_100, 'category': category})
                continue

        
        m = re.search(r"(\d+[\.,]?\d*)\s*(l|litre|litres|liters)", low)
        if m:
            val = _to_float(m.group(1))
            if val is not None:
                
                if '100' in low:
                    category = 'combined'
                    if any(k in low for k in ['city', 'urban']):
                        category = 'city'
                    elif any(k in low for k in ['highway', 'extra', 'motorway', 'country', 'rural']):
                        category = 'highway'
                    out.append({'label': 'l/100 km (inferred)', 'value': val, 'category': category})
                else:
                    
                    pass

    return out


def _extract_city_highway_from_full(full_text: str):
    
    if not full_text:
        return {}

    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    found = {}

    
    for ln in lines:
        low = ln.lower()
        
        m = re.search(r"(city|urban|urban cycle)[^\d\n]{0,30}(\d+[\.,]?\d*)\s*l\s*/\s*100", low)
        if m and 'city' not in found:
            val = _to_float(m.group(2))
            if val is not None:
                found['city'] = val
                continue
        m = re.search(r"(extra-urban|extra urban|extra|highway|motorway|extraurban|country)[^\d\n]{0,30}(\d+[\.,]?\d*)\s*l\s*/\s*100", low)
        if m and 'highway' not in found:
            val = _to_float(m.group(2))
            if val is not None:
                found['highway'] = val
                continue
        m = re.search(r"(combined|average|average consumption|combined consumption)[^\d\n]{0,30}(\d+[\.,]?\d*)\s*l\s*/\s*100", low)
        if m and 'combined' not in found:
            val = _to_float(m.group(2))
            if val is not None:
                found['combined'] = val
                continue

    
    for ln in lines:
        low = ln.lower()
        m = re.search(r"(\d+[\.,]?\d*)\s*l\s*/\s*100", low)
        if m and 'combined' not in found:
            val = _to_float(m.group(1))
            if val is not None:
                found['combined'] = val
                break

    
    return found


def _extract_image_links(driver):
    """
    Sayfadaki /images/ dizinindeki görüntülerin linklerini çıkar.
    """
    image_links = []
    try:
        # Sayfanın base URL'sini al
        current_url = driver.current_url
        base_domain = '/'.join(current_url.split('/')[:3])
        
        # Tüm <img> tag'larını bul
        img_elements = driver.find_elements(By.XPATH, "//img[@src]")
        
        for img in img_elements:
            try:
                src = img.get_attribute('src') or ''
                if '/images/' in src.lower():
                    # Eğer relative URL ise, absolute URL'ye dönüştür
                    if src.startswith('/'):
                        full_url = base_domain + src
                    elif src.startswith('http'):
                        full_url = src
                    else:
                        full_url = current_url.rstrip('/') + '/' + src
                    
                    if full_url not in image_links:
                        image_links.append(full_url)
            except Exception:
                continue
        
        # Ayrıca <a> tag'larındaki resim linklerini de kontrol et
        link_elements = driver.find_elements(By.XPATH, "//a[@href]")
        for link in link_elements:
            try:
                href = link.get_attribute('href') or ''
                if '/images/' in href.lower() and (href.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'))):
                    # Eğer relative URL ise, absolute URL'ye dönüştür
                    if href.startswith('/'):
                        full_url = base_domain + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = current_url.rstrip('/') + '/' + href
                    
                    if full_url not in image_links:
                        image_links.append(full_url)
            except Exception:
                continue
                
    except Exception:
        pass
    
    return image_links


def _collect_result_links(driver, brand=None, model=None, max_links=6):
    
    links = []
    try:
        elements = driver.find_elements(By.XPATH, "//a[@href]")
    except Exception:
        return links

    brand_norm = _normalize(brand)
    model_norm = _normalize(model)

    
    blacklist = {'advanced', 'home', 'login', 'register', 'autocatalog', 'car specs api',
                 'search', 'privacy', 'cookie', 'contact', 'terms', 'terms of use',
                 'change privacy settings', 'change privacy', 'cookies'}

    seen = set()
    for el in elements:
        try:
            href = el.get_attribute('href') or ''
            text = (el.text or '').strip()
            if not href or href in seen or not text:
                continue

            low_text = text.lower()
            
            if low_text in blacklist:
                continue

            
            score = 0
            if model_norm and model_norm in low_text:
                score += 3
            if brand_norm and brand_norm in low_text:
                score += 2
            
            if any(k in low_text for k in ['hp', 'multijet', 'tdi', 'tdci', 'tsi', 'mpi', 'diesel', 'petrol', 'gasoline', 'turbo']):
                score += 2
            
            import re
            if re.search(r"\(\s*\d{2,4}\s*\)", text):
                score += 2
            
            href_low = href.lower()
            if any(piece in href_low for piece in ['/en/car', '/en/vehicle', '/car/', '/vehicle/', '/model/']):
                score += 2
            if brand_norm and brand_norm in href_low:
                score += 1
            if model_norm and model_norm in href_low:
                score += 1

            
            if any(b in low_text for b in blacklist):
                score -= 10

            
            if len(low_text.split()) <= 2 and len(low_text) < 25 and score <= 0:
                continue

            
            if score > -5:
                links.append({'text': text, 'href': href, 'score': score})
            seen.add(href)
            if len(links) >= max_links:
                break
        except Exception:
            continue

    
    links = sorted(links, key=lambda x: x.get('score', 0), reverse=True)
    
    out = [{'text': l['text'], 'href': l['href']} for l in links[:max_links]]
    return out


def _sanitize_list_title(text: str) -> str:
    
    if not text:
        return ''
    t = text.strip()
    
    t = ' - '.join([ln.strip() for ln in t.splitlines() if ln.strip()])
    
    t = re.sub(r"\|\s*[\d.,]+\s*(us\s*mpg|uk\s*mpg|mpg|km/l|l/100\s*km)?", "", t, flags=re.I)
    
    t = re.sub(r"[\-|\|]\s*[\d.,]+\s*(l/100\s*km|km/l|us\s*mpg|uk\s*mpg|mpg)?\s*$", "", t, flags=re.I)
    
    t = re.sub(r"[\-|\|]+\s*$", "", t).strip()
    
    if len(t) > 140:
        t = t[:137] + '...'
    return t


def _translate_drive_terms(text: str):
    """
    Metin içinde yaygın çekiş terimlerini bulur ve Türkçe karşılıklarını döndürür.
    Dönen değer liste şeklindedir (aynı terim birden fazla yerde bulunursa tekil sonuç).
    """
    if not text:
        return []

    mapping = {
        'front-wheel drive': 'Önden çekişli',
        'front wheel drive': 'Önden çekişli',
        'fwd': 'Önden çekişli',
        'rear-wheel drive': 'Arkadan itişli',
        'rear wheel drive': 'Arkadan itişli',
        'rwd': 'Arkadan itişli',
        'all-wheel drive': 'Tüm tekerlekten çekişli',
        'all wheel drive': 'Tüm tekerlekten çekişli',
        'awd': 'Tüm tekerlekten çekişli',
        'four-wheel drive': 'Dört tekerlekten çekişli',
        'four wheel drive': 'Dört tekerlekten çekişli',
        '4wd': 'Dört tekerlekten çekişli',
        '4x4': 'Dört tekerlekten çekişli',
    }

    found = []
    low = (text or '').lower()
    for k, v in mapping.items():
        if k in low and v not in found:
            found.append(v)

    return found


def _remove_english_drive_terms(text: str):
    """
    Metin içindeki İngilizce çekiş terimlerini kaldırır.
    """
    if not text:
        return text

    terms_to_remove = [
        ', Front wheel drive',
        ', front wheel drive',
        ', Rear wheel drive',
        ', rear wheel drive',
        ', All-wheel drive',
        ', all-wheel drive',
        ', Four-wheel drive',
        ', four-wheel drive',
        ', AWD',
        ', awd',
        ', FWD',
        ', fwd',
        ', RWD',
        ', rwd',
        ', 4WD',
        ', 4wd',
        ', 4x4',
    ]

    result = text
    for term in terms_to_remove:
        result = result.replace(term, '')

    return result



def AutoSearch(car_info):
    base_url = "https://www.auto-data.net/en/"
    results = []
    seen_urls_global = set()
    seen_titles_global = set()

    
    models = car_info.get('models', [])
    if len(models) > 1:
        print('\nGirilen modeller:')
        for i, m in enumerate(models, start=1):
            print(f"{i}. {m}")
        print("all - Hepsini ara")

        while True:
            choice = input("Hangi modelleri aramak istersiniz? (örn: 1 veya 1,3 ya da all): ").strip().lower()
            if choice == 'all':
                selected_models = models
                break
            
            parts = [p.strip() for p in choice.split(',') if p.strip()]
            sel = []
            ok = True
            for p in parts:
                if not p.isdigit():
                    ok = False
                    break
                idx = int(p)
                if idx < 1 or idx > len(models):
                    ok = False
                    break
                sel.append(models[idx-1])
            if not ok or not sel:
                print('Geçersiz seçim, lütfen tekrar deneyin.')
                continue
            selected_models = sel
            break
    else:
        selected_models = models

    
    for model in selected_models:
        driver = webdriver.Chrome()
        try:
            search_term = f"{car_info['year']} {car_info['brand']} {model} {car_info['engine']} {car_info['body']}".strip()
            print(f"\nAranıyor: {search_term}")

            try:
                driver.get(base_url)
            except Exception as e:
                print(f"Siteye erişilemedi: {e}")
                driver.quit()
                continue

            
            try:
                vignette_close_xpath = "//div[@id='google_vignette']/div/div[1]"
                close_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, vignette_close_xpath))
                )
                close_button.click()
                time.sleep(0.3)
            except Exception:
                pass

            
            try:
                search_box_xpath = '//input[@type="text" and (contains(@placeholder, "Search") or contains(@placeholder, "Ara") or contains(@id, "search"))]'
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, search_box_xpath))
                )
            except TimeoutException:
                try:
                    search_box = driver.find_element(By.XPATH, '//input')
                except Exception:
                    print("Arama kutusu bulunamadı.")
                    driver.quit()
                    continue

            search_box.clear()
            search_box.send_keys(search_term)

            
            try:
                submit = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']|//button[contains(., 'Search') or contains(., 'Ara')]|//span[contains(@class,'search')]") )
                )
                try:
                    submit.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", submit)
            except Exception:
                try:
                    search_box.send_keys('\n')
                except Exception:
                    pass

            
            try:
                
                WebDriverWait(driver, 6).until(
                    EC.presence_of_element_located((By.XPATH, "//a[@href]") )
                )
            except Exception:
                pass

            links = _collect_result_links(driver, max_links=100)
            if not links:
                print("Uygun sonuç bulunamadı, sonraki modele geçiliyor.")
                driver.quit()
                continue

            
            for ln in links:
                
                href_norm = (ln['href'] or '').split('#')[0].split('?')[0]
                title_norm = _normalize(ln['text'])
                if href_norm in seen_urls_global or title_norm in seen_titles_global:
                    continue
                seen_urls_global.add(href_norm)
                seen_titles_global.add(title_norm)

                
                summary = (ln['text'] or '').splitlines()[0][:200]
                results.append({
                    'model': model,
                    'title': ln['text'],
                    'url': ln['href'],
                    'summary': summary,
                    'full': None
                })

        except Exception as e:
            print(f"Beklenmedik hata ({model}): {e}")
        finally:
            time.sleep(0.5)
            driver.quit()

    
    if not results:
        print("Hiçbir model için uygun sonuç bulunamadı.")
        return

    print('\nBulunan seçenekler:')
    for i, r in enumerate(results, start=1):
        list_title = _sanitize_list_title(r['title'] or r['summary'] or '')
        # İngilizce çekiş terimlerini kaldır
        list_title_cleaned = _remove_english_drive_terms(list_title)
        # Çekiş türünü tespit et ve Türkçeye çevir
        drive_terms = _translate_drive_terms(r.get('title') or r.get('summary') or '')
        if drive_terms:
            print(f"{i}. {list_title_cleaned} - Çekiş: {', '.join(drive_terms)}")
        else:
            print(f"{i}. {list_title_cleaned}")
        
        # Her sonuç için fotoğrafları çek ve göster
        if not r.get('images'):
            url = r['url']
            if url.startswith('/'):
                url = base_url.rstrip('/') + url
            try:
                print(f"   Fotoğraflar yükleniyor...")
                driver = webdriver.Chrome()
                driver.get(url)
                time.sleep(1)
                image_links = _extract_image_links(driver)
                r['images'] = image_links
                driver.quit()
                
                if image_links:
                    for img_url in image_links[:1]:  # İlk 1 fotoğrafı göster
                        print(f"      - {img_url}")
                else:
                    print("   Fotoğraf bulunamadı.")
            except Exception as e:
                print(f"   Fotoğraflar çekilirken hata: {e}")
                r['images'] = []

    print('\nGörüntülemek için bir numara seçin (iptal için 0): ')
    while True:
        sel = input().strip()
        if not sel.isdigit():
            print('Lütfen sayı girin.')
            continue
        idx = int(sel)
        if idx == 0:
            print('İşlem iptal edildi.')
            return
        if 1 <= idx <= len(results):
            chosen = results[idx-1]
            print('\nSeçilen:', chosen['model'] or '(belirtilmemiş)')
            # Başlıkta İngilizce çekiş terimlerini kaldır
            title_display = _sanitize_list_title(chosen.get('title') or chosen.get('summary') or '')
            title_display = _remove_english_drive_terms(title_display)
            print('Başlık:', title_display)
            print('URL:', chosen['url'])

            # Çekiş türünü tespit et ve Türkçeye çevir
            drive_info_src = ' '.join([str(chosen.get('full') or ''), str(chosen.get('title') or ''), str(chosen.get('summary') or '')])
            drive_terms = _translate_drive_terms(drive_info_src)
            if drive_terms:
                print('Çekiş türü:', ', '.join(drive_terms))

            
            if not chosen.get('full'):
                url = chosen['url']
                if url.startswith('/'):
                    url = base_url.rstrip('/') + url
                print('\nSeçilen link açılıyor ve veri çekiliyor...')
                driver = webdriver.Chrome()
                try:
                    driver.get(url)
                    time.sleep(1)
                    full_scraped = _extract_largest_table_text(driver)
                    chosen['full'] = full_scraped
                    
                    # Görüntü linklerini çıkar
                    image_links = _extract_image_links(driver)
                    chosen['images'] = image_links
                except Exception as e:
                    print('Veri çekilirken hata:', e)
                finally:
                    driver.quit()

            
            fuel_lines = _extract_fuel_info(chosen.get('full') or '')
            consumptions = []
            for ln in fuel_lines:
                parsed = _extract_consumptions_from_line(ln)
                for p in parsed:
                    
                    consumptions.append(p)

            
            full_text = chosen.get('full') or ''
            direct = _extract_city_highway_from_full(full_text)

            # Görüntü linklerini göster (sadece ilk bulunan fotoğraf)
            image_links = chosen.get('images', [])
            print('\n=== Bulunan Fotoğraf ===')
            if image_links:
                print(f"1. {image_links[0]}")
            else:
                print("Fotoğraf bulunamadı.")

            # Birleştirilmiş yakıt verisi gösterimi: Combined, Urban, Extra-urban
            # Önce doğrudan bulunan değerleri (direct) kullan, yoksa elde edilen parsed değerlerden al
            grouped = {'combined': [], 'city': [], 'highway': []}
            if not consumptions and chosen.get('full'):
                for full_ln in (chosen['full'] or '').splitlines():
                    parsed = _extract_consumptions_from_line(full_ln)
                    for p in parsed:
                        consumptions.append(p)

            for c in consumptions:
                cat = c.get('category') or 'other'
                if cat not in grouped:
                    continue
                val = c.get('value')
                if val is None:
                    continue
                grouped[cat].append(val)

            def first_unique(lst):
                seen = set()
                out = []
                for v in lst:
                    s = f"{v:.2f}"
                    if s in seen:
                        continue
                    seen.add(s)
                    out.append(v)
                return out

            for k in grouped:
                grouped[k] = first_unique(grouped[k])

            display = {'combined': None, 'city': None, 'highway': None}
            # use direct values first
            for k in list(display.keys()):
                if k in direct and isinstance(direct.get(k), (int, float)):
                    display[k] = direct.get(k)

            # fallback to grouped parsed values
            for k in list(display.keys()):
                if display[k] is None and grouped.get(k):
                    display[k] = grouped[k][0]

            print('\nYakıt verileri (sadece l/100 km):')
            labels = [('combined', 'Ortalama)'), ('city', 'Şehir İçi)'), ('highway', 'Şehir Dışı)')]
            any_shown = False
            for k, label in labels:
                v = display.get(k)
                if v is not None:
                    print(f"- {label}: {v:.2f} l/100 km")
                    any_shown = True
                else:
                    print(f"- {label}: Bulunamadı")

            if not any_shown:
                print('Sayfada l/100 km cinsinden veya dönüştürülebilecek yakıt verisi bulunamadı.')

            return
        else:
            print(f'Geçersiz seçim. 1-{len(results)} arası bir sayı girin veya 0 ile iptal edin.')


if __name__ == '__main__':
    car_data = get_user_car_info()
    AutoSearch(car_data)