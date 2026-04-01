document.addEventListener('DOMContentLoaded', () => {

    const sensorElements = {
        ph: document.getElementById('ph-val'),
        ec: document.getElementById('ec-val'),
        temp: document.getElementById('temp-val'),
        humidity: document.getElementById('hum-val'),
        pump: document.getElementById('pump-status'),
        water: document.getElementById('water-level')
    };

    const statusIndicators = {
        camera: document.getElementById('cam-status'),
        server: document.getElementById('server-status'),
        jetson: document.getElementById('jetson-status')
    };

    const cameraImg = document.getElementById('camera-feed-img');
    const uploadInput = document.getElementById('file-upload');
    const detectionList = document.getElementById('detection-list');
    const plantCount = document.getElementById('plant-count');

    // 1. Sensör Verilerini Periyodik Olarak Çekme
    async function fetchSensors() {
        try {
            const response = await fetch('/api/sensors');
            if (!response.ok) throw new Error('Sensor fetch failed');

            const data = await response.json();

            // DOM Güncelleme
            sensorElements.ph.textContent = data.ph.toFixed(2);
            sensorElements.ec.textContent = data.ec.toFixed(2);
            sensorElements.temp.textContent = data.temp.toFixed(1);
            sensorElements.humidity.textContent = data.humidity;
            sensorElements.water.textContent = data.water_level + '%';

            // Pompa durumu
            sensorElements.pump.textContent = data.pump_status === 'active' ? 'AKTİF 🟢' : 'BEKLEMEDE ⚪';

            // Bağlantı durumu güncellemeleri
            statusIndicators.server.classList.add('active'); // Eğer veri geliyorsa server aktiftir

        } catch (error) {
            console.error('Sensor Error:', error);
            statusIndicators.server.classList.remove('active');
        }
    }

    // 2. Görüntü Yükleme ve Analiz
    uploadInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Yükleniyor görseli veya efekti eklenebilir
        cameraImg.style.opacity = '0.5';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Prediction failed');

            const result = await response.json();

            // Görüntüyü güncelle
            cameraImg.src = result.image;
            cameraImg.style.opacity = '1';

            // İstatistikleri güncelle
            updateStats(result.counts);

        } catch (error) {
            console.error('Prediction Error:', error);
            alert('Analiz başarısız oldu.');
            cameraImg.style.opacity = '1';
        }
    });

    function updateStats(counts) {
        detectionList.innerHTML = ''; // Listeyi temizle
        let total = 0;

        for (const [key, value] of Object.entries(counts)) {
            const li = document.createElement('div');
            li.className = 'metric-row';
            li.innerHTML = `
                <span class="metric-label">${key.toUpperCase()}</span>
                <span class="metric-val text-primary">${value}</span>
            `;
            detectionList.appendChild(li);
            total += value;
        }

        plantCount.textContent = total;
    }

    // 3. Başlatma
    setInterval(fetchSensors, 2000); // Her 2 saniyede bir sensör verisini güncelle
    fetchSensors(); // İlk yükleme
});
