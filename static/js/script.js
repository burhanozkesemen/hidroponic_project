document.addEventListener('DOMContentLoaded', () => {

    const sensorElements = {
        ph: document.getElementById('ph-val'),
        ec: document.getElementById('ec-val'),
        water_temp: document.getElementById('temp-val'),
        air_temp: document.getElementById('air-temp-val'),
        co2: document.getElementById('co2-val'),
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
            if (!response.ok) throw new Error(`Sensor fetch failed: ${response.status}`);

            const data = await response.json();
            console.log('📊 Sensor data fetched:', data);

            // DOM Güncelleme
            if (sensorElements.ph && data.ph !== undefined) {
                sensorElements.ph.textContent = parseFloat(data.ph).toFixed(2);
            }
            if (sensorElements.ec && data.ec !== undefined) {
                sensorElements.ec.textContent = parseFloat(data.ec).toFixed(2);
            }
            if (sensorElements.water_temp && data.water_temp !== undefined) {
                sensorElements.water_temp.textContent = parseFloat(data.water_temp).toFixed(1);
            }
            if (sensorElements.air_temp && data.air_temp !== undefined) {
                sensorElements.air_temp.textContent = parseFloat(data.air_temp).toFixed(1);
            }
            if (sensorElements.co2 && data.co2 !== undefined) {
                sensorElements.co2.textContent = parseFloat(data.co2).toFixed(0);
            }
            if (sensorElements.humidity && data.humidity !== undefined) {
                sensorElements.humidity.textContent = parseFloat(data.humidity).toFixed(0);
            }
            if (sensorElements.water && data.water_level !== undefined) {
                sensorElements.water.textContent = parseFloat(data.water_level).toFixed(0);
            }

            // Pompa durumu
            const pumpText = data.pump_status === 'active' ? 'ACTIVE 🟢' : 'INACTIVE ⚪';
            sensorElements.pump.textContent = pumpText;
            sensorElements.pump.style.color = data.pump_status === 'active' ? '#10b981' : '#ef4444';

            // Bağlantı durumu güncellemeleri
            statusIndicators.server.classList.add('active'); // Eğer veri geliyorsa server aktiftir

        } catch (error) {
            console.error('❌ Sensor fetch failed:', error);
            statusIndicators.server.classList.remove('active');
        }
    }

    // Kamera feed'lerini yenile (cache busting ile)
    function refreshCameraFeeds() {
        const now = Date.now();
        const img1 = document.getElementById('camera-feed-img');
        const img2 = document.getElementById('camera-feed-img-2');
        
        if (img1) {
            img1.src = `/api/video_feed?_=${now}`;
        }
        if (img2) {
            img2.src = `/api/video_feed_2?_=${now}`;
        }
    }

    // Simple Camera Stream - Single frame polling (non-blocking)
    function streamCamera(endpoint, cameraId, imgElement, loadingElement) {
        let isFirstFrame = true;
        
        async function pollFrame() {
            try {
                // Use polling endpoint for single frames (less CPU intensive)
                const frameEndpoint = `/api/frame/${cameraId}?_=${Date.now()}`;
                const response = await fetch(frameEndpoint);
                
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const blob = await response.blob();
                if (blob.size > 100) { // Valid JPEG
                    const url = URL.createObjectURL(blob);
                    if (imgElement) {
                        imgElement.src = url;
                        if (isFirstFrame && loadingElement) {
                            loadingElement.style.display = 'none';
                            isFirstFrame = false;
                            console.log(`✅ Camera ${cameraId} loaded`);
                        }
                    }
                }
                
                // Poll next frame after delay - throttle to prevent Firefox warning
                setTimeout(pollFrame, 500); // 2 FPS is enough for greenhouse monitoring
                
            } catch (error) {
                console.error(`Camera ${cameraId} error:`, error);
                if (isFirstFrame && loadingElement) {
                    loadingElement.innerHTML = '<p style="color: #94a3b8;">Retrying...</p>';
                }
                setTimeout(pollFrame, 2000);
            }
        }
        
        pollFrame();
    }

    // 2. Görüntü Yükleme ve Analiz (Multiple Files - Kameralardan)
    uploadInput.addEventListener('change', async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        // Yükleniyor görseli veya efekti eklenebilir
        cameraImg.style.opacity = '0.5';

        try {
            let mergedCounts = {};
            let firstImage = null;

            // Her dosya için predict yap
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch('/api/predict', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error('Prediction failed for file ' + (i + 1));

                const result = await response.json();

                // İlk görüntüyü kaydet
                if (i === 0) firstImage = result.image;

                // Sayıları birleştir
                for (const [key, value] of Object.entries(result.counts)) {
                    mergedCounts[key] = (mergedCounts[key] || 0) + value;
                }
            }

            // Görüntüyü güncelle (ilk görüntü)
            if (firstImage) {
                cameraImg.src = firstImage;
                cameraImg.style.opacity = '1';
            }

            // Merge edilmiş istatistikleri güncelle
            updateStats(mergedCounts);

        } catch (error) {
            console.error('Prediction Error:', error);
            alert('Analiz başarısız oldu: ' + error.message);
            cameraImg.style.opacity = '1';
        }
    });

    function updateStats(counts) {
        detectionList.innerHTML = ''; // Listeyi temizle
        let total = 0;

        if (!counts || Object.keys(counts).length === 0) {
            detectionList.innerHTML = '<p style="color: #94a3b8; font-size: 0.9rem; text-align: center;">No detections found.</p>';
            plantCount.textContent = '0';
            return;
        }

        for (const [key, value] of Object.entries(counts)) {
            const li = document.createElement('div');
            li.className = 'detection-item';
            li.innerHTML = `
                <span class="metric-label">${key.toUpperCase()}</span>
                <span class="metric-val" style="float: right; color: var(--primary);">${value}</span>
            `;
            detectionList.appendChild(li);
            total += value;
        }

        plantCount.textContent = total;
    }

    // 3. Başlatma
    setInterval(fetchSensors, 2000); // Her 2 saniyede bir sensör verisini güncelle
    fetchSensors(); // İlk sensör yükleme
    
    // Kamera stream'lerini başlat (polling mode)
    streamCamera('/api/video_feed', 0, document.getElementById('camera-feed-img'), document.getElementById('camera-1-loading'));
    streamCamera('/api/video_feed_2', 2, document.getElementById('camera-feed-img-2'), document.getElementById('camera-2-loading'));
});
