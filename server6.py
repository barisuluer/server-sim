import asyncio
import threading
import logging
import os
import subprocess
import signal
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
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
    server_base_port: int = 50051
    telemetry_interval: float = 2.0
    mavsdk_server_path: str = "/home/baris/.local/lib/python3.10/site-packages/mavsdk/bin/mavsdk_server"
    connection_timeout: float = 10.0
    server_startup_delay: float = 5.0

# Flask uygulaması
app = Flask(__name__)

# Telemetri verilerini saklamak için global sözlük
telemetry_data: Dict[str, Dict] = {}

# Flask API endpoint'i
@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    return jsonify(telemetry_data)

class TelemetryServer:
    def _init_(self, config: ServerConfig):
        self.config = config
        self.drones: List[System] = []
        self.server_processes: List[subprocess.Popen] = []
        self._running = False
        self._cleanup_done = False

    async def start_mavsdk_servers(self) -> bool:
        """Her drone için ayrı bir mavsdk_server başlat"""
        try:
            for i in range(self.config.num_drones):
                udp_port = self.config.base_port + i
                server_port = self.config.server_base_port + i
                cmd = f"{self.config.mavsdk_server_path} -p {server_port} udpin://127.0.0.1:{udp_port}"
                process = subprocess.Popen(
                    cmd.split(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.server_processes.append(process)
                await asyncio.sleep(0.5)  # Her server için kısa bir bekleme
            
            # Server'ların başlaması için bekle
            await asyncio.sleep(self.config.server_startup_delay)
            return True
        except Exception as e:
            logger.error(f"mavsdk_server'lar başlatılırken hata: {str(e)}")
            return False

    async def connect_drone(self, drone: System, drone_id: int) -> bool:
        """Drone'a bağlan"""
        port = self.config.base_port + drone_id
        server_port = self.config.server_base_port + drone_id
        try:
            await drone.connect(system_address=f"udp://127.0.0.1:{port}")
            
            # Bağlantı durumunu kontrol et
            timeout = self.config.connection_timeout
            async for state in drone.core.connection_state():
                if state.is_connected:
                    logger.info(f"Drone {drone_id} başarıyla bağlandı")
                    return True
                await asyncio.sleep(0.1)
                timeout -= 0.1
                if timeout <= 0:
                    logger.error(f"Drone {drone_id} bağlantı zaman aşımına uğradı")
                    return False
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

        # mavsdk_server'ları başlat
        if not await self.start_mavsdk_servers():
            logger.error("mavsdk_server'lar başlatılamadı!")
            self._running = False
            return

        # Drone'ları bağla
        for i in range(self.config.num_drones):
            drone_id = f"drone_{i}"
            drone = System(mavsdk_server_address="localhost", port=self.config.server_base_port + i)
            if await self.connect_drone(drone, i):
                self.drones.append(drone)
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
        if self._cleanup_done:
            return
            
        self._running = False
        self._cleanup_done = True
        
        # Drone bağlantılarını kapat
        for drone in self.drones:
            try:
                await drone.close()
            except Exception as e:
                logger.error(f"Drone bağlantısı kapatılırken hata: {str(e)}")
        
        # mavsdk_server'ları sonlandır
        for proc in self.server_processes:
            try:
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=5)  # 5 saniye bekle
            except subprocess.TimeoutExpired:
                proc.kill()  # Zaman aşımı olursa zorla sonlandır
            except Exception as e:
                logger.error(f"mavsdk_server sonlandırılırken hata: {str(e)}")

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
        os._exit(0)

if __name__ == "__main__":
    main()