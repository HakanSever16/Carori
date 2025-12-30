# CARORİ: Intelligent Fuel Cost Calculation System

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.0-green)
![Gradio](https://img.shields.io/badge/Gradio-UI-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

**CARORİ** (Cost Analysis based on Route, vehicle model, and Real-time Information) is a web-based decision support system designed to estimate travel costs with high accuracy. Unlike traditional navigation apps that only provide distance and time, CARORİ integrates **vehicle-specific factory data** and **real-time fuel station prices** along the route.

## 📖 Abstract

Increasing energy costs and variable fuel prices have made travel planning critical. This project processes the route, vehicle model, and current station data selected by the user to perform cost optimization. The system utilizes a **Hybrid Scraping Architecture** to ensure speed and accuracy.

## 🚀 Key Features

* **Hybrid Web Scraping:** Combines `Selenium` for dynamic vehicle data and `Requests` + `Beautiful Soup` for ultra-fast, real-time fuel price fetching.
* **Smart Routing:** Uses **OpenRouteService** and **Folium** to calculate precise distances and visualize routes interactively via **Leaflet.js**.
* **Vehicle Specific:** Pulls factory fuel consumption data (City/Highway) for the specific car model selected.
* **Instant Price Analysis:** Scrapes real-time prices from stations specifically located along the generated route.
* **Cost Calculation:** `(Route Distance) × (Vehicle Consumption Coeff) × (Regional Fuel Price)`.

## 🛠️ Tech Stack & Architecture

This project is built using **Python** with a modular architecture:

* **Backend API:** Flask
* **User Interface:** Gradio
* **Data Mining:** Selenium (Dynamic), Requests & BS4 (Static/Fast)
* **GIS & Mapping:** OpenRouteService, Folium, Leaflet.js
* **Data Analysis:** Pandas, NumPy
* **Visualization:** Matplotlib

## 📦 Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/yourusername/CARORI-Fuel-Cost-Calculator.git](https://github.com/yourusername/CARORI-Fuel-Cost-Calculator.git)
    cd CARORI-Fuel-Cost-Calculator
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup WebDriver**
    * Ensure you have Google Chrome installed.
    * The system uses Selenium; ensure `chromedriver` is compatible with your browser version.

## 🏃‍♂️ Usage

1.  **Start the API Server** (Handles fuel price scraping)
    ```bash
    python api.py
    ```
    *Runs on port 3939*

2.  **Start the Interface** (In a new terminal)
    ```bash
    python app.py
    ```
    *Runs on port 7860*

3.  **Access the App**
    * Open your browser and go to `http://localhost:7860`

## 📊 Methodology

The system employs a **Hybrid Scraping** approach to solve performance bottlenecks:
1.  **Requests/BS4:** Used for fetching static fuel price tables instantly (ms latency).
2.  **Selenium:** Used only when necessary for complex, dynamic vehicle databases.
3.  **Caching:** The Flask API implements `lru_cache` to prevent redundant network requests for station prices.

## 👥 Authors

* **Hakan SEVER**
* **Özgür ALTUNKAYNAK**
* **Muhammed İkbal YILDIZ**
* **MHD Mahdi KOCHHA**
* **Ali HAMDEMİRCİ**

*Department of Computer Technology and Information Systems, Trakya University, Edirne, Turkey.*

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

