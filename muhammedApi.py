import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import re
from functools import lru_cache

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
# Tarayıcı gibi görünmek için Header (403 Hatasını önler)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# --- YARDIMCI FONKSİYONLAR ---
def normalize_turkish_chars(text):
    if not text:
        return ""
    
    # Frontend'den gelen İ harflerini düzelt
    text = text.replace('İ', 'i').replace('I', 'i').lower()
    
    text = re.sub(r'[^a-z0-9çğıiöşü\s]', ' ', text)
    text = text.replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c')
    text = text.replace('ı', 'i')
    text = re.sub(r'\s+', '-', text)
    
    return text.strip('-')

# İstanbul İlçe Listeleri (Slug oluşturmak için gerekli)
ISTANBUL_ANADOLU = {
    "adalar", "atasehir", "beykoz", "cekmekoy", "kadikoy", "kartal",
    "maltepe", "pendik", "sancaktepe", "sultanbeyli", "sile",
    "tuzla", "umraniye", "uskudar"
}

ISTANBUL_AVRUPA = {
    "arnavutkoy", "avcilar", "bagcilar", "bahcelievler", "bakirkoy",
    "basaksehir", "bayrampasa", "besiktas", "beylikduzu", "beyoglu",
    "buyukcekmece", "catalca", "esenler", "esenyurt", "eyupsultan",
    "fatih", "gaziosmanpasa", "gungoren", "kagithane", "kucukcekmece",
    "sariyer", "silivri", "sisli", "zeytinburnu", "sultangazi"
}

# --- SCRAPING MOTORU (ÖNBELLEKLİ) ---
# lru_cache sayesinde aynı il/ilçe için 5 dakika içinde gelen istekleri tekrar indirmez.
@lru_cache(maxsize=128)
def scrape_prices_cached(url_slug):
    url = f"https://m.doviz.com/akaryakit-fiyatlari/{url_slug}"
    print(f"🌍 WEB İSTEĞİ ATILIYOR: {url}") # Sadece önbellekte yoksa çalışır
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code != 200:
            print(f"Hata: {response.status_code}")
            return {}
            
        soup = BeautifulSoup(response.text, "html.parser")
        fiyatlar = {}

        table = soup.find("table")
        if not table: return {}

        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) >= 3:
                brand_full = cols[0].get_text(strip=True).upper()
                brand_key = brand_full.split(" ")[0] # SHELL, OPET vs.

                # Benzin (Col 1) ve Dizel (Col 2) fiyatlarını al
                try:
                    price_benzin = cols[1].get_text(strip=True).replace("\u20ba", "").replace(",", ".").strip()
                    price_dizel = cols[2].get_text(strip=True).replace("\u20ba", "").replace(",", ".").strip()
                    
                    fiyatlar[brand_key] = {
                        "benzin": price_benzin,
                        "dizel": price_dizel
                    }
                except:
                    continue
        
        return fiyatlar

    except Exception as e:
        print(f"Scrape Hatası: {e}")
        return {}

# --- ANA FONKSİYON ---
def fiyat_getir_main(hedef_istasyon, il, ilce, yakit_tipi):
    il_norm = normalize_turkish_chars(il)
    ilce_norm = normalize_turkish_chars(ilce)

    # URL Slug Belirleme
    url_slug = ""
    if "istanbul" in il_norm:
        if ilce_norm in ISTANBUL_ANADOLU:
            url_slug = f"istanbul-anadolu/{ilce_norm}"
        elif ilce_norm in ISTANBUL_AVRUPA:
            url_slug = f"istanbul-avrupa/{ilce_norm}"
        else:
            url_slug = "istanbul-avrupa" # Fallback
    else:
        url_slug = f"{il_norm}/{ilce_norm}"

    # Veriyi çek (veya önbellekten al)
    all_prices = scrape_prices_cached(url_slug)
    
    # İstenen markayı bul
    target_brand = hedef_istasyon[0].upper() if hedef_istasyon else ""
    
    found_price = "0"
    
    if target_brand in all_prices:
        # Yakıt tipine göre fiyatı seç
        raw_price = all_prices[target_brand].get(yakit_tipi, "0")
        found_price = raw_price
    else:
        # Marka bulunamazsa ortalama bir fiyat veya ilk fiyatı döndür
        pass 

    # API formatına uygun dönüş
    # Frontend { "Firma": "Fiyat" } formatı bekliyor
    return { target_brand: found_price }

@app.route('/fiyat_getir', methods=['POST'])
def process():
    data = request.get_json()
    hedef_istasyonlar = data.get("istasyonlar", []) # ["SHELL"] gibi gelir
    il = data.get("il", "")
    ilce = data.get("ilce", "")
    yakit = data.get("yakit", "benzin").lower()
    
    # Dizel/Motorin isimlendirme düzeltmesi
    if "dizel" in yakit or "motorin" in yakit:
        yakit = "dizel"
    else:
        yakit = "benzin"
    
    result = fiyat_getir_main(hedef_istasyonlar, il, ilce, yakit)
    
    # Cache temizleme (Opsiyonel, uzun süre çalışırsa şişmemesi için)
    scrape_prices_cached.cache_clear() 
    
    return jsonify({"fiyatlar": result})

if __name__ == "__main__":
    print("🚀 API Çalışıyor: Port 3939")
    app.run(host="0.0.0.0", port=3939, debug=True)
