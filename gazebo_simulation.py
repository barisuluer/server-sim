import asyncio
import subprocess
import os
import logging
import signal
import psutil
from typing import List, Dict
from dataclasses import dataclass
from pathlib import Path

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simulation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SimulationConfig:
    num_drones: int = 5
    px4_path: str = "/home/baris/PX4-Autopilot/build/px4_sitl_default/bin/px4"
    gazebo_path: str = "/usr/bin/gazebo"
    world_path: str = "/home/baris/PX4-Autopilot/Tools/sitl_gazebo/worlds/empty.world"
    base_port: int = 14540
    positions: List[str] = None

    def __post_init__(self):
        if self.positions is None:
            self.positions = [f"{i},{i+1}" for i in range(self.num_drones)]

class SimulationManager:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.processes: List[subprocess.Popen] = []
        self._cleanup_done = False
        self._setup_signal_handlers()
        self._kill_existing_gazebo()

    def _kill_existing_gazebo(self):
        """Çalışan Gazebo süreçlerini sonlandır"""
        for proc in psutil.process_iter(['name']):
            try:
                if 'gazebo' in proc.info['name'].lower():
                    proc.kill()
                    logger.info(f"Var olan Gazebo süreci sonlandırıldı: {proc.pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def _setup_signal_handlers(self):
        """Sinyal işleyicilerini ayarla"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Sinyal işleyici"""
        logger.info(f"Sinyal alındı: {signum}")
        self.cleanup()
        exit(0)

    async def start_gazebo(self) -> bool:
        """Gazebo simülasyonunu başlat"""
        # Önce var olan Gazebo süreçlerini temizle
        self._kill_existing_gazebo()
        
        gazebo_cmd = f"{self.config.gazebo_path} --verbose {self.config.world_path}"
        logger.info(f"Gazebo başlatılıyor: {gazebo_cmd}")
        
        try:
            with open("gazebo_output.log", "w") as log_file:
                gazebo_process = subprocess.Popen(
                    gazebo_cmd,
                    shell=True,
                    stdout=log_file,
                    stderr=log_file,
                    text=True
                )
            self.processes.append(gazebo_process)
            await asyncio.sleep(5)
            return True
        except Exception as e:
            logger.error(f"Gazebo başlatılırken hata: {e}")
            return False

    async def start_drone(self, drone_id: int) -> bool:
        """Belirli bir drone'u başlat"""
        port = self.config.base_port + drone_id
        pose = self.config.positions[drone_id]
        system_id = drone_id + 1  # SYSID_THISMAV 1’den başlar (1, 2, 3, 4, 5)
        
        cmd = (
            f"PX4_SYS_AUTOSTART=4001 "
            f"PX4_GZ_MODEL_POSE='{pose}' "
            f"PX4_SIM_MODEL=gz_x500 "
            f"PX4_SITL_PORT={port} "
            f"SYSID_THISMAV={system_id} "  # Her drone için farklı SYSID_THISMAV
            f"{self.config.px4_path} -i {drone_id}"
        )
        
        logger.info(f"Drone {drone_id} başlatılıyor: {cmd}")
        
        try:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd="/home/baris/PX4-Autopilot",
                text=True
            )
            self.processes.append(process)
            
            # İlk drone için 10 saniye, diğerleri için 2 saniye bekle
            wait_time = 10 if drone_id == 0 else 2
            await asyncio.sleep(wait_time)
            return process.poll() is None
        except Exception as e:
            logger.error(f"Drone {drone_id} başlatılırken hata: {e}")
            return False

    async def monitor_processes(self):
        """Tüm süreçleri izle ve logla"""
        while True:
            for i, proc in enumerate(self.processes):
                if proc.poll() is None:  # Süreç hala çalışıyorsa
                    if i > 0:  # Gazebo hariç drone'lar için
                        out = proc.stdout.readline()
                        err = proc.stderr.readline()
                        if out:
                            logger.debug(f"Drone {i-1} stdout: {out.strip()}")
                        if err:
                            logger.debug(f"Drone {i-1} stderr: {err.strip()}")
            await asyncio.sleep(1)

    def cleanup(self):
        """Tüm süreçleri temizle"""
        if self._cleanup_done:
            return
            
        logger.info("Simülasyon kapatılıyor...")
        self._cleanup_done = True
        
        # Önce tüm Gazebo süreçlerini sonlandır
        self._kill_existing_gazebo()
        
        # Sonra diğer süreçleri temizle
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception as e:
                logger.error(f"Süreç kapatılırken hata: {e}")

    async def run(self):
        """Simülasyonu çalıştır"""
        try:
            if not await self.start_gazebo():
                return

            for i in range(self.config.num_drones):
                if not await self.start_drone(i):
                    logger.error(f"Drone {i} başlatılamadı")
                    return
                logger.info(f"Drone {i} başarıyla başlatıldı")

            await self.monitor_processes()
        except Exception as e:
            logger.error(f"Simülasyon çalışırken hata: {e}")
        finally:
            self.cleanup()

async def main():
    """Ana fonksiyon"""
    config = SimulationConfig()
    manager = SimulationManager(config)
    await manager.run()

if __name__ == "__main__":
    logger.info("Simülasyon başlatılıyor...")
    asyncio.run(main())