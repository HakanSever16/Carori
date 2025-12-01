from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import re
from flask import Flask, request, jsonify


def _normalize(text: str) -> str:
    return (text or "").strip().lower()

def _to_float(num_str: str):
    try:
        return float(num_str.replace(',', '.'))
    except Exception:
        return None

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
    mapping = {
        'front-wheel drive': 'Önden çekişli', 'fwd': 'Önden çekişli',
        'rear-wheel drive': 'Arkadan itişli', 'rwd': 'Arkadan itişli',
        'all-wheel drive': 'Tüm tekerlekten çekişli', 'awd': 'Tüm tekerlekten çekişli',
        'four-wheel drive': 'Dört tekerlekten çekişli', '4wd': 'Dört tekerlekten çekişli', '4x4': 'Dört tekerlekten çekişli',
    }
    found = []
    low = (text or '').lower()
    for k, v in mapping.items():
        if k in low and v not in found:
            found.append(v)
    return found

def _remove_english_drive_terms(text: str):
    terms_to_remove = [
        ', Front wheel drive', ', front wheel drive', ', Rear wheel drive',
        ', rear wheel drive', ', All-wheel drive', ', all-wheel drive',
        ', Four-wheel drive', ', four-wheel drive', ', AWD', ', awd',
        ', FWD', ', fwd', ', RWD', ', rwd', ', 4WD', ', 4wd', ', 4x4',
    ]
    result = text
    for term in terms_to_remove:
        result = result.replace(term, '')
    return result

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

def get_user_car_info_from_request_minimal():
    """
    Sadece 'models' bilgisini JSON'dan alır, diğerlerini boş bırakır.
    """
    if not request.json:
        return None

    data = request.json
    models_raw = data.get("models", "")
    
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


def AutoSearch(car_info):
    base_url = "https://www.auto-data.net/en/"
    results = []
    seen_urls_global = set()
    seen_titles_global = set()

    selected_models = car_info.get('models', [""])
    
    final_results = []
    
    for model in selected_models:
        driver = webdriver.Chrome()
        try:
            search_term = model.strip()
            
            
            try:
                driver.get(base_url)
            except Exception:
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

            links = _collect_result_links(driver, brand=car_info['brand'], model=model, max_links=100)
            if not links:
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
            pass
        finally:
            time.sleep(0.5)
            driver.quit()
            
    for r in results:
        list_title = _sanitize_list_title(r['title'] or r['summary'] or '')
        list_title_cleaned = _remove_english_drive_terms(list_title)
        drive_terms = _translate_drive_terms(r.get('title') or r.get('summary') or '')
        
        final_results.append({
            'title': list_title_cleaned,
            'url': r['url'],
            'model_searched': r['model']
        })

    return final_results

app = Flask(__name__)

@app.route('/arac', methods=['POST'])
def arac_endpoint():
    
    car_data = get_user_car_info_from_request_minimal()
    
    if car_data is None:
        return jsonify({"error": "Geçersiz JSON formatı."}), 400
    
    if not car_data['models'] or car_data['models'] == [""]:
         return jsonify({"error": "JSON gövdesinde 'models' anahtarı sağlanmalıdır."}), 400

    try:
        search_results = AutoSearch(car_data)

        if not search_results:
             return jsonify({"message": f"Arama sonuç vermedi. Aranan modeller: {car_data['models']}"}), 200
             
        return jsonify(search_results), 200

    except Exception as e:
        print(f"Hata oluştu: {e}") 
        return jsonify({"error": "Sunucu hatası: Arama sırasında bir sorun oluştu."}), 500


if __name__ == '__main__':
    print("Flask Sunucusu Başlatılıyor...")
    app.run(host='0.0.0.0', port=5000, debug=True)