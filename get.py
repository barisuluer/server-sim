import requests
import time
import json
import logging
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telemetry_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ClientConfig:
    server_url: str = "http://localhost:5000/telemetry"
    request_timeout: float = 5.0
    update_interval: float = 2.0
    max_retries: int = 3
    retry_delay: float = 1.0

class TelemetryClient:
    def __init__(self, config: ClientConfig):
        self.config = config
        self._running = False
        self._last_data: Optional[Dict] = None
        self._last_update: Optional[datetime] = None

    def fetch_telemetry(self) -> Optional[Dict]:
        """
        Sunucudan telemetri verilerini çeker.
        
        Returns:
            Optional[Dict]: Telemetri verileri veya hata durumunda None
        """
        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(
                    self.config.server_url,
                    timeout=self.config.request_timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._last_data = data
                    self._last_update = datetime.now()
                    logger.debug("Telemetri verileri başarıyla alındı")
                    return data
                else:
                    logger.error(f"Sunucudan veri alınamadı. Hata kodu: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"İstek zaman aşımına uğradı. Deneme {attempt + 1}/{self.config.max_retries}")
            except requests.exceptions.ConnectionError:
                logger.error("Sunucuya bağlanılamadı. Sunucunun çalıştığından emin olun.")
            except requests.exceptions.RequestException as e:
                logger.error(f"Beklenmeyen hata: {str(e)}")
            except json.JSONDecodeError:
                logger.error("Sunucudan gelen veri JSON formatında değil")
            
            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_delay)
        
        return None

    def print_telemetry(self, data: Dict):
        """
        Telemetri verilerini güzel bir formatta yazdırır.
        """
        print("\n" + "="*50)
        print(f"Telemetri Verileri - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)
        
        for drone_id, drone_data in data.items():
            print(f"\n{drone_id}:")
            print(f"  Pozisyon:")
            print(f"    Enlem: {drone_data['position'].get('lat', 'N/A')}°")
            print(f"    Boylam: {drone_data['position'].get('lon', 'N/A')}°")
            print(f"    Yükseklik: {drone_data['position'].get('alt', 'N/A')}m")
            
            print(f"  Hız:")
            print(f"    Kuzey: {drone_data['velocity'].get('north', 'N/A')} m/s")
            print(f"    Doğu: {drone_data['velocity'].get('east', 'N/A')} m/s")
            print(f"    Aşağı: {drone_data['velocity'].get('down', 'N/A')} m/s")
            
            print(f"  Batarya: %{drone_data.get('battery', 'N/A')}")
            print("-"*30)

    def run(self):
        """
        Telemetri verilerini sürekli olarak çeken ana döngü.
        """
        self._running = True
        logger.info("Telemetri istemcisi başlatılıyor...")
        
        try:
            while self._running:
                data = self.fetch_telemetry()
                if data:
                    self.print_telemetry(data)
                time.sleep(self.config.update_interval)
                
        except KeyboardInterrupt:
            logger.info("Telemetri istemcisi kapatılıyor...")
        finally:
            self._running = False

    def stop(self):
        """
        İstemciyi durdurur.
        """
        self._running = False

def main():
    """
    Ana çalıştırma fonksiyonu.
    """
    config = ClientConfig()
    client = TelemetryClient(config)
    
    try:
        client.run()
    except KeyboardInterrupt:
        logger.info("Program kapatılıyor...")
        client.stop()

if __name__ == "__main__":
    main()