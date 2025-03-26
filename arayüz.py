import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import os
import signal

class SimulationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulation Control Panel")
        
        # Süreçleri takip etmek için dictionary
        self.processes = {
            "world": None,
            "server": None,
            "get_data": None
        }
        
        # Butonlar için frame
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=10)
        
        # Start Butonları
        self.start_world_btn = tk.Button(self.button_frame, text="Start World", command=self.start_world)
        self.start_world_btn.pack(side=tk.LEFT, padx=5)
        
        self.start_server_btn = tk.Button(self.button_frame, text="Start Server", command=self.start_server)
        self.start_server_btn.pack(side=tk.LEFT, padx=5)
        
        self.get_data_btn = tk.Button(self.button_frame, text="Get Data", command=self.get_data)
        self.get_data_btn.pack(side=tk.LEFT, padx=5)
        
        # Stop Butonları
        self.stop_world_btn = tk.Button(self.button_frame, text="Stop World", command=self.stop_world)
        self.stop_world_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_server_btn = tk.Button(self.button_frame, text="Stop Server", command=self.stop_server)
        self.stop_server_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_get_data_btn = tk.Button(self.button_frame, text="Stop Get Data", command=self.stop_get_data)
        self.stop_get_data_btn.pack(side=tk.LEFT, padx=5)
        
        # Hepsini Kapat Butonu
        self.stop_all_btn = tk.Button(self.button_frame, text="Stop All", command=self.stop_all)
        self.stop_all_btn.pack(side=tk.LEFT, padx=5)
        
        # Log alanı
        self.log_text = scrolledtext.ScrolledText(root, width=80, height=20)
        self.log_text.pack(pady=10)
        
    def log(self, message):
        """Log mesajlarını arayüze ekle"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
    
    def run_command(self, command, process_key):
        """Komut çalıştır ve çıktıları log'a yaz"""
        try:
            # shell=True ile cmd gibi çalıştırıyoruz, böylece ROS komutları da desteklenir
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, preexec_fn=os.setsid if os.name != 'nt' else None)
            self.processes[process_key] = process
            self.log(f"{process_key.capitalize()} başlatıldı: {' '.join(command) if isinstance(command, list) else command}")
            
            # Çıktıları gerçek zamanlı olarak oku
            while process.poll() is None:
                line = process.stdout.readline()
                if line:
                    self.log(line.strip())
            # Kalan çıktıları al
            for line in process.stdout.readlines():
                if line:
                    self.log(line.strip())
                    
            self.processes[process_key] = None
            self.log(f"{process_key.capitalize()} tamamlandı.")
        except Exception as e:
            self.log(f"Hata ({process_key}): {str(e)}")
            self.processes[process_key] = None
    
    def start_world(self):
        """Gazebo simülasyonunu başlat"""
        if self.processes["world"] is None:
            # Örnek: ROS ile Gazebo başlatma (senin komutuna göre değiştir)
            command = "python3 gazebo_simulation.py"  # Gerçek komutunu buraya yaz
            thread = threading.Thread(target=self.run_command, args=(command, "world"))
            thread.start()
        else:
            self.log("World zaten çalışıyor!")
    
    def start_server(self):
        """Server'ı başlat"""
        if self.processes["server"] is None:
            command = "python3 server6.py"  # Gerçek dosya adını buraya yaz
            thread = threading.Thread(target=self.run_command, args=(command, "server"))
            thread.start()
        else:
            self.log("Server zaten çalışıyor!")
    
    def get_data(self):
        """Server'dan veri al"""
        if self.processes["get_data"] is None:
            command = "python3 get.py"  # Gerçek dosya adını buraya yaz
            thread = threading.Thread(target=self.run_command, args=(command, "get_data"))
            thread.start()
        else:
            self.log("Get Data zaten çalışıyor!")
    
    def stop_process(self, process_key):
        """Belirtilen süreci durdur"""
        process = self.processes.get(process_key)
        if process is not None:
            try:
                if os.name == 'nt':  # Windows
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
                else:  # Unix/Linux
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)  # Grup olarak sonlandır
                process.wait(timeout=3)
                self.log(f"{process_key.capitalize()} durduruldu.")
            except Exception as e:
                self.log(f"{process_key.capitalize()} durdurulurken hata: {str(e)}")
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)  # Zorla kapat
                self.log(f"{process_key.capitalize()} zorla kapatıldı.")
            finally:
                self.processes[process_key] = None
        else:
            self.log(f"{process_key.capitalize()} zaten kapalı veya çalışmıyor.")
    
    def stop_world(self):
        """Gazebo simülasyonunu durdur"""
        self.stop_process("world")
        # ROS için ek temizlik (opsiyonel)
        if self.processes["world"] is None:
            subprocess.run("rosnode kill -a", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run("killall -9 gzserver gzclient", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def stop_server(self):
        """Server'ı durdur"""
        self.stop_process("server")
    
    def stop_get_data(self):
        """Get Data işlemini durdur"""
        self.stop_process("get_data")
    
    def stop_all(self):
        """Hepsini durdur"""
        self.log("Tüm süreçler durduruluyor...")
        for key in self.processes.keys():
            self.stop_process(key)
        # ROS ve Gazebo için genel temizlik
        subprocess.run("rosnode kill -a", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run("killall -9 gzserver gzclient", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationGUI(root)
    root.mainloop()