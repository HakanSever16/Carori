const API_URL = "http://127.0.0.1:5000";


async function aramaYap() {
    const input = document.getElementById("modelInput");
    const query = input.value.trim();
    const loading = document.getElementById("loading");
    const listDiv = document.getElementById("sonuc-listesi");
    const detayDiv = document.getElementById("detay-alani");
    const btn = document.getElementById("searchBtn");

    if (!query) return alert("Lütfen bir model yazın!");


    listDiv.innerHTML = "";
    detayDiv.style.display = "none";
    loading.style.display = "block";
    btn.disabled = true;

    try {
        
        const response = await fetch(`${API_URL}/arac`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ models: query })
        });

        const data = await response.json();

        loading.style.display = "none";
        btn.disabled = false;

        if (data.error) {
            listDiv.innerHTML = `<p style="color:red">Hata: ${data.error}</p>`;
            return;
        }

        if (data.length === 0) {
            listDiv.innerHTML = "<p>Sonuç bulunamadı.</p>";
            return;
        }

        
        data.forEach(arac => {
            const div = document.createElement("div");
            div.className = "result-item";
            
            div.onclick = () => detayGetir(arac.url, arac.title);
            
            div.innerHTML = `
                <strong>${arac.title}</strong><br>
                <small>${arac.model_searched}</small>
            `;
            listDiv.appendChild(div);
        });

    } catch (error) {
        console.error(error);
        loading.innerHTML = "Bir hata oluştu. Konsolu kontrol edin.";
        btn.disabled = false;
    }
}


async function detayGetir(url, title) {
    const detayDiv = document.getElementById("detay-alani");
    const baslik = document.getElementById("detay-baslik");
    const icerik = document.getElementById("detay-icerik");
    
    
    detayDiv.style.display = "block";
    baslik.innerText = title;
    icerik.innerHTML = "<em>Detaylı veriler çekiliyor...</em>";
    
    
    detayDiv.scrollIntoView({ behavior: "smooth" });

    try {
        
        const encodedUrl = encodeURIComponent(url);
        const response = await fetch(`${API_URL}/arac/detay?url=${encodedUrl}`);
        
        const data = await response.json();

        if (data.error) {
            icerik.innerHTML = `<p style="color:red">${data.error}</p>`;
            return;
        }

        
        const yakit = data.fuel_consumption_l_per_100km;
        
        
        icerik.innerHTML = `
            ${data.image_url ? `<img src="${data.image_url}" class="car-img"><br><br>` : ''}
            
            <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                <tr style="background:#eee;"><th>Veri Tipi</th><th>Değer (l/100km)</th></tr>
                <tr><td>Şehir İçi</td><td>${yakit['Şehir İçi'] || '-'}</td></tr>
                <tr><td>Şehir Dışı</td><td>${yakit['Şehir Dışı'] || '-'}</td></tr>
                <tr><td><strong>Ortalama</strong></td><td><strong>${yakit['Ortalama'] || '-'}</strong></td></tr>
            </table>
            
            <p><small><a href="${data.url}" target="_blank">Orijinal Kaynağa Git</a></small></p>
        `;

    } catch (error) {
        icerik.innerHTML = "Detay çekilirken hata oluştu.";
        console.error(error);
    }
}