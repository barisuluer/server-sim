import asyncio
import threading
import logging
import os
from dataclasses import dataclass
from typing import Dict, List
from flask import Flask, jsonify
from mavsdk import System

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telemetry_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ServerConfig:
    host: str = '0.0.0.0'
    port: int = 5000
    num_drones: int = 5
    base_port: int = 14540
    telemetry_interval: float = 2.0

# Flask uygulaması
app = Flask(__name__)

# Telemetri verilerini saklamak için global sözlük
telemetry_data: Dict[str, Dict] = {}

# Flask API endpoint'i
@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    return jsonify(telemetry_data)

class TelemetryServer:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.drones: List[System] = []
        self._running = False

    async def connect_drone(self, drone: System, drone_id: int) -> bool:
        """Drone'a bağlan"""
        port = self.config.base_port + drone_id
        try:
            logger.info(f"Drone {drone_id} bağlanıyor: udp://:{port}")
            await drone.connect(system_address=f"udp://:{port}")
            
            # Bağlantı durumunu kontrol et
            async for state in drone.core.connection_state():
                if state.is_connected:
                    logger.info(f"Drone {drone_id} başarıyla bağlandı!")
                    return True
                await asyncio.sleep(1)
            
            logger.error(f"Drone {drone_id} bağlantısı başarısız")
            return False
        except Exception as e:
            logger.error(f"Drone {drone_id} bağlantı hatası: {str(e)}")
            return False

    async def collect_telemetry(self, drone: System, drone_id: str):
        """Drone'dan telemetri verilerini topla"""
        while self._running:
            try:
                # Pozisyon verilerini al
                async for position in drone.telemetry.position():
                    telemetry_data[drone_id]["position"] = {
                        "lat": position.latitude_deg,
                        "lon": position.longitude_deg,
                        "alt": position.absolute_altitude_m
                    }
                    break

                # Hız verilerini al
                async for velocity in drone.telemetry.velocity_ned():
                    telemetry_data[drone_id]["velocity"] = {
                        "north": velocity.north_m_s,
                        "east": velocity.east_m_s,
                        "down": velocity.down_m_s
                    }
                    break

                # Batarya verilerini al
                async for battery in drone.telemetry.battery():
                    telemetry_data[drone_id]["battery"] = round(battery.remaining_percent, 1)
                    break

                await asyncio.sleep(self.config.telemetry_interval)
            except Exception as e:
                logger.error(f"{drone_id} telemetri hatası: {str(e)}")
                await asyncio.sleep(self.config.telemetry_interval)

    async def start_telemetry(self):
        """Telemetri toplama işlemini başlat"""
        logger.info("Telemetri toplama başlatılıyor...")
        self._running = True

        # Drone'ları bağla
        for i in range(self.config.num_drones):
            drone_id = f"drone_{i}"
            drone = System()  # Yeni drone oluştur
            if await self.connect_drone(drone, i):  # Drone'u bağla
                self.drones.append(drone)  # Bağlantı başarılıysa listeye ekle
                telemetry_data[drone_id] = {"position": {}, "velocity": {}, "battery": 0}
            else:
                logger.error(f"Drone {i} başlatılamadı, diğer drone'lar devam ediyor...")

        if not self.drones:
            logger.error("Hiçbir drone başlatılamadı!")
            self._running = False
            return

        # Telemetri toplama görevlerini başlat
        tasks = [
            self.collect_telemetry(drone, f"drone_{i}")
            for i, drone in enumerate(self.drones)
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        """Telemetri toplama işlemini durdur"""
        self._running = False
        for drone in self.drones:
            try:
                # Drone bağlantısını kapat
                await drone.close()
                logger.info("Drone bağlantısı kapatıldı")
            except Exception as e:
                logger.error(f"Drone bağlantısı kapatılırken hata: {str(e)}")
                # Hata durumunda bile devam et
                continue

def run_flask(config: ServerConfig):
    """Flask sunucusunu başlat"""
    logger.info(f"Flask sunucusu başlatılıyor: {config.host}:{config.port}")
    app.run(host=config.host, port=config.port, debug=False, use_reloader=False)

def main():
    """Ana çalıştırma fonksiyonu"""
    config = ServerConfig()
    
    # Flask'ı ayrı bir thread'de başlat
    flask_thread = threading.Thread(
        target=run_flask,
        args=(config,),
        daemon=True
    )
    flask_thread.start()
    logger.info("Flask thread başlatıldı")

    # Telemetri sunucusunu başlat
    server = TelemetryServer(config)
    
    def run_telemetry():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server.start_telemetry())
        except KeyboardInterrupt:
            logger.info("Telemetri sunucusu kapatılıyor...")
            loop.run_until_complete(server.stop())
        finally:
            loop.close()

    telemetry_thread = threading.Thread(target=run_telemetry, daemon=True)
    telemetry_thread.start()
    logger.info("Telemetri thread başlatıldı")

    try:
        # Ana thread'in kapanmasını engelle
        while True:
            threading.Event().wait()
    except KeyboardInterrupt:
        logger.info("Program kapatılıyor...")
        # Programı düzgün bir şekilde sonlandır
        os._exit(0)

if __name__ == "__main__":
    main()