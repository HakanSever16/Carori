import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import requests
import concurrent.futures

# Matplotlib için Türkçe karakter ve stil ayarları
# Eğer sisteminizde bu font yoksa 'Arial' veya 'sans-serif' kullanabilirsiniz.
plt.rcParams['font.family'] = 'DejaVu Sans'

# --- AYARLAR ---
API_URL = "http://192.168.1.110:3939/fiyat_getir"  # muhammedApi.py adresi

# API'nin tanıdığı marka anahtarları (Web sitesindeki isimlerin ilk kelimesi)
# Key: API'ye gönderilecek isim, Value: Grafikte görünecek isim
BRANDS_MAP = {
    "SHELL": "Shell",
    "OPET": "Opet",
    "PETROL": "Petrol Ofisi", 
    "BP": "BP",
    "TOTAL": "Total"
}

def fetch_single_price(brand_key, fuel_type, city, district):
    """
    Tek bir marka ve yakıt türü için API'den fiyat çeker.
    """
    try:
        payload = {
            "istasyonlar": [brand_key],
            "il": city,
            "ilce": district,
            "yakit": fuel_type  # 'benzin' veya 'dizel'
        }
        # Timeout kısa tutuldu ki grafik hızlı dönsün
        response = requests.post(API_URL, json=payload, timeout=4)
        
        if response.status_code == 200:
            data = response.json()
            # API Dönüş Formatı: {"fiyatlar": {"SHELL": "42.50"}}
            prices = data.get("fiyatlar", {})
            price_str = prices.get(brand_key, "0")
            
            # String'i float'a çevir (Virgül/Nokta kontrolü)
            if price_str:
                return float(str(price_str).replace(",", "."))
    except Exception as e:
        print(f"Veri çekme hatası ({brand_key}-{fuel_type}): {e}")
    
    return 0.0

def get_real_fuel_data(city, district):
    """
    Belirtilen konum için tüm markaların verilerini paralel isteklerle toplar.
    """
    data_list = []
    
    # ThreadPool ile istekleri aynı anda atalım (Hız kazandırır)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_map = {}
        
        for key, name in BRANDS_MAP.items():
            # Hem Benzin hem Dizel için istek oluştur
            f_benzin = executor.submit(fetch_single_price, key, "benzin", city, district)
            f_dizel = executor.submit(fetch_single_price, key, "dizel", city, district)
            
            future_map[f_benzin] = (name, "Benzin")
            future_map[f_dizel]  = (name, "Dizel")
            
        # Sonuçları topla
        for future in concurrent.futures.as_completed(future_map):
            brand_name, fuel_type = future_map[future]
            price = 0.0
            try:
                price = future.result()
            except:
                pass
            
            data_list.append({
                "Marka": brand_name,
                "Yakıt Türü": fuel_type,
                "Fiyat": price
            })
            
    df = pd.DataFrame(data_list)
    return df

def create_chic_chart(city, district):
    """
    Matplotlib kullanarak şık bir karşılaştırma grafiği oluşturur.
    """
    # 1. Girdileri Kontrol Et
    if not city or not district:
        city, district = "istanbul", "kadikoy" # Varsayılan
        
    # 2. Veriyi Çek
    df = get_real_fuel_data(city, district)
    
    # Eğer veri yoksa veya hepsi 0 ise bilgi ver
    if df.empty or df['Fiyat'].sum() == 0:
        fig_empty, ax_empty = plt.subplots(figsize=(8, 4))
        ax_empty.text(0.5, 0.5, "Veri Bulunamadı veya API Kapalı\n(Lütfen API'nin çalıştığından emin olun)", 
                      ha='center', va='center', fontsize=12)
        ax_empty.axis('off')
        return fig_empty

    # 3. Veriyi Grafiğe Hazırla (Pivot)
    # Satırlar: Markalar, Sütunlar: Benzin/Dizel
    df_pivot = df.pivot(index='Marka', columns='Yakıt Türü', values='Fiyat')
    # Sıralamayı garantiye al
    cols = [c for c in ["Benzin", "Dizel"] if c in df_pivot.columns]
    df_pivot = df_pivot[cols]

    # 4. Stil ve Grafik Oluşturma
    plt.style.use('seaborn-v0_8-darkgrid') # Modern ve temiz bir tema
    
    fig, ax = plt.subplots(figsize=(11, 6))
    
    # Renk Paleti: Benzin (Turuncu/Sarı), Dizel (Yeşil/Koyu)
    colors = ['#F39C12', '#2ECC71'] 
    
    # Çubuk Grafiği Çiz
    df_pivot.plot(
        kind='bar', 
        ax=ax, 
        color=colors, 
        width=0.75, 
        edgecolor='white', 
        linewidth=1.2,
        rot=0 # X ekseni yazıları dik durmasın
    )

    # 5. Başlık ve Eksenler
    ax.set_title(f"⛽ {city.upper()} / {district.upper()} Akaryakıt Fiyatları", 
                 fontsize=16, fontweight='bold', pad=20, color='#34495E')
    
    ax.set_xlabel("İstasyon Markası", fontsize=12, labelpad=10, color='#555')
    ax.set_ylabel("Litre Fiyatı (TL)", fontsize=12, labelpad=10, color='#555')
    
    # Arka plan rengini hafif gri yaparak grafiği öne çıkar
    fig.patch.set_facecolor('#FDFFE6') 
    ax.set_facecolor('white')

    # Y Ekseni limitleri (Fiyatlar birbirine yakın olduğu için min değeri biraz yukarı çekiyoruz)
    # Böylece farklar daha net görünür.
    vals = df[df['Fiyat'] > 0]['Fiyat']
    if len(vals) > 0:
        y_min = vals.min() * 0.95
        y_max = vals.max() * 1.02
        ax.set_ylim(y_min, y_max)

    # 6. Çubukların Üzerine Etiket Ekleme
    for container in ax.containers:
        # Etiketleri çubuğun içine değil hemen üstüne yaz
        ax.bar_label(container, fmt='%.2f', padding=3, fontsize=10, fontweight='bold', color='#2C3E50')

    # Lejant Ayarı
    ax.legend(title=None, frameon=True, facecolor='white', framealpha=0.9, loc='lower right', fontsize=11)
    
    plt.tight_layout()
    
    return fig

# --- GRADIO ARAYÜZÜ ---
with gr.Blocks(title="Akaryakıt Fiyat Analizi", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 📊 Canlı Akaryakıt Fiyat Karşılaştırması
        Bu araç, belirtilen İl ve İlçe için **canlı API verilerini** kullanarak markaların fiyatlarını karşılaştırır.
        """
    )
    
    with gr.Row():
        city_input = gr.Textbox(label="Şehir (İl)", placeholder="Örn: istanbul", value="istanbul")
        dist_input = gr.Textbox(label="İlçe", placeholder="Örn: kadikoy", value="kadikoy")
    
    btn_analiz = gr.Button("🔍 Fiyatları Getir ve Grafiği Çiz", variant="primary")
    
    plot_output = gr.Plot(label="Fiyat Grafiği")
    
    # Buton Aksiyonu
    btn_analiz.click(
        fn=create_chic_chart, 
        inputs=[city_input, dist_input], 
        outputs=plot_output
    )
    
    # Sayfa yüklenince otomatik çalıştır
    demo.load(fn=create_chic_chart, inputs=[city_input, dist_input], outputs=plot_output)

if __name__ == "__main__":
    demo.launch()
