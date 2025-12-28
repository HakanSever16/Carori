import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import requests
import concurrent.futures
import os

# --- CONFIGURATION ---
# Language(Example: turkish) character and style settings for Matplotlib
plt.rcParams['font.family'] = 'DejaVu Sans' # If in your system's dont have this font, you can use 'Arial' or 'sans-serif'. 

# --- SETTINGS ---
# API Configuration
# NOTE: This IP is local. Users must update this or run the backend locally.
DEFAULT_API_URL = "http://192.168.1.110:3939/fiyat_getir"   # The muhammedApi.py adress
API_URL = os.getenv("FUEL_API_URL", DEFAULT_API_URL)

# Brand keys recognized by the API (The first word of the names on the website)
Key: The name to be sent to the API, Value: The name to be displayed in the graph.
# Mapping: API Key -> Display Name
BRANDS_MAP = {
    "SHELL": "Shell",
    "OPET": "Opet",
    "PETROL": "Petrol Ofisi", 
    "BP": "BP",
    "TOTAL": "Total"
}

def fetch_single_price(brand_key, fuel_type, city, district):
    """
    It retrieves prices from the API for a single brand and fuel type.
    Fetches the price for a specific brand.
    Note: Payload keys must remain in Turkish to match the backend API requirements.
    """
    try:
        # --- CRITICAL: DO NOT CHANGE THESE KEYS ---
        # The backend API specifically expects 'istasyonlar', 'il', 'ilce', 'yakit'.
        payload = {
            "istasyonlar": [brand_key],
            "il": city,
            "ilce": district,
            "yakit": fuel_type  # API expects 'benzin' or 'dizel'
        }
        # ------------------------------------------
        
        # The timeout was kept short so that the graph would spin quickly.
        response = requests.post(API_URL, json=payload, timeout=4)
        
        if response.status_code == 200:
            data = response.json()
            # API returns data in structure: {"fiyatlar": {"SHELL": "42.50"}}
            # Keeping 'fiyatlar' as expected by the API response schema
            prices = data.get("fiyatlar", {})
            price_str = prices.get(brand_key, "0")
            
            # Covering from String to float (Comma/Dot Chek)
            if price_str:
                return float(str(price_str).replace(",", "."))
    except Exception as e:
        print(f"Error fetching data ({brand_key}-{fuel_type}): {e}")
    
    return 0.0

def get_real_fuel_data(city, district):
    """
    It collects data from all brands for the specified location through parallel requests.
    Aggregates data using parallel requests.
    """
    data_list = []
    
    # Let's send the requests simultaneously using ThreadPool (It saves speed).
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_map = {}
        
        for key, name in BRANDS_MAP.items():
            # 'benzin' and 'dizel' are hardcoded values expected by the backend logic
            f_gasoline = executor.submit(fetch_single_price, key, "benzin", city, district)
            f_diesel = executor.submit(fetch_single_price, key, "dizel", city, district)
            
            future_map[f_gasoline] = (name, "Gasoline")
            future_map[f_diesel]  = (name, "Diesel")
           
        # Collect to results 
        for future in concurrent.futures.as_completed(future_map):
            brand_name, fuel_type_label = future_map[future]
            price = 0.0
            try:
                price = future.result()
            except:
                pass
            
            # DataFrame columns are for display, so English is fine here
            data_list.append({
                "Brand": brand_name,
                "Fuel Type": fuel_type_label,
                "Price": price
            })
            
    df = pd.DataFrame(data_list)
    return df

def create_chic_chart(city, district):
    """
    Creates an elegant comparison chart using Matplotlib.
    """
    # 1. Check to inputs
    # Validate inputs
    if not city or not district:
        city, district = "istanbul", "kadikoy" # Default
        
    # 2. Get data
    df = get_real_fuel_data(city, district)
    
    # If data is not exist or all them are 0 then give info
    if df.empty or df['Price'].sum() == 0:
        fig_empty, ax_empty = plt.subplots(figsize=(8, 4))
        ax_empty.text(0.5, 0.5, "No Data / API Error\n(Please ensure the API is working)", ha='center', va='center', fontsize=12)
        ax_empty.axis('off')
        return fig_empty

    # 3. Get ready to data for graph (Pivot)
    # Pivot for plotting
    df_pivot = df.pivot(index='Brand', columns='Fuel Type', values='Price')
    cols = [c for c in ["Gasoline", "Diesel"] if c in df_pivot.columns]
    df_pivot = df_pivot[cols]

    # 4. Create Style and Graphic
    # Plotting style
    plt.style.use('seaborn-v0_8-darkgrid') # A modern and clean theme

    fig, ax = plt.subplots(figsize=(11, 6))

    # Color pallet: Gasoline (Orange/Yellow), Diesel (Green/Dark)
    colors = ['#F39C12', '#2ECC71'] 
    
    # Draw Line Graphic
    df_pivot.plot(
        kind='bar', 
        ax=ax, 
        color=colors, 
        width=0.75, 
        edgecolor='white', 
        linewidth=1.2,
        rot=0 # X axis text don't be vertical
    )

    # 5. Header and Axises
    # Labels
    ax.set_title(f"⛽ {city.upper()} / {district.upper()} Fuel Prices", 
                 fontsize=16, fontweight='bold', pad=20, color='#34495E')
    ax.set_xlabel("Station Brand", fontsize=12, labelpad=10, color='#555')
    ax.set_ylabel("Liter Price (TL)", fontsize=12, labelpad=10, color='#555')
    
    # Set Background color is light grey
    fig.patch.set_facecolor('#FDFFE6') 
    ax.set_facecolor('white')

    # Y Axis limits (Since the prices are close to each other, we are raising the min value a little.)
    # So differents are see clearly
    # Zoom y-axis
    vals = df[df['Price'] > 0]['Price']
    if len(vals) > 0:
        y_min = vals.min() * 0.95
        y_max = vals.max() * 1.02
        ax.set_ylim(y_min, y_max)

    # 6. Add label in lines
    for container in ax.containers:
        # Write the labels just above the bar, not inside it
        ax.bar_label(container, fmt='%.2f', padding=3, fontweight='bold', color='#2C3E50')

    # Legend Setting
    ax.legend(title=None, frameon=True, facecolor='white', framealpha=0.9, loc='lower right', fontsize=11)

    plt.tight_layout()

    return fig

# --- GRADIO UI ---
with gr.Blocks(title="Fuel Price Analysis", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 📊 Live Fuel Price Comparison
        This tool compares brand prices using **live API data** for the specified Province and District.
        """
    )
    
    with gr.Row():
        # Input labels are English, but values passed to functions are kept raw
        city_input = gr.Textbox(label="City", placeholder="Exa: istanbul", value="istanbul")
        dist_input = gr.Textbox(label="District", placeholder="Exa: kadikoy", value="kadikoy")
    
    btn_analiz = gr.Button("🔍 Fetch & Plot", variant="primary")

    plot_output = gr.Plot(label="Chart")
    
    # Button Action
    btn_analiz.click(
        fn=create_chic_chart, 
        inputs=[city_input, dist_input], 
        outputs=plot_output
    )

    # Run otomaticly when page loaded
    demo.load(fn=create_chic_chart, inputs=[city_input, dist_input], outputs=plot_output)

if __name__ == "__main__":
    demo.launch()
