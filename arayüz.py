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
        
        # Log alanları için frame
        self.log_frame = tk.Frame(root)
        self.log_frame.pack(pady=10)
        
        # Birinci Log Alanı: Server ve Simülasyon
        self.sim_server_log_label = tk.Label(self.log_frame, text="Simulation & Server Log")
        self.sim_server_log_label.pack()
        self.sim_server_log = scrolledtext.ScrolledText(self.log_frame, width=80, height=10)
        self.sim_server_log.pack(pady=5)
        
        # İkinci Log Alanı: Get Data
        self.get_data_log_label = tk.Label(self.log_frame, text="Get Data Log")
        self.get_data_log_label.pack()
        self.get_data_log = scrolledtext.ScrolledText(self.log_frame, width=80, height=10)
        self.get_data_log.pack(pady=5)
        
    def log(self, message, log_type="sim_server"):
        """Log mesajlarını uygun alana ekle"""
        if log_type == "get_data":
            self.get_data_log.insert(tk.END, message + "\n")
            self.get_data_log.see(tk.END)
        else:  # Varsayılan olarak sim_server
            self.sim_server_log.insert(tk.END, message + "\n")
            self.sim_server_log.see(tk.END)
    
    def run_command(self, command, process_key):
        """Komut çalıştır ve çıktıları uygun log'a yaz"""
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, preexec_fn=os.setsid if os.name != 'nt' else None)
            self.processes[process_key] = process
            self.log(f"{process_key.capitalize()} başlatıldı: {command}", process_key if process_key == "get_data" else "sim_server")
            
            # Çıktıları gerçek zamanlı olarak oku
            while process.poll() is None:
                line = process.stdout.readline()
                if line:
                    self.log(line.strip(), process_key if process_key == "get_data" else "sim_server")
            # Kalan çıktıları al
            for line in process.stdout.readlines():
                if line:
                    self.log(line.strip(), process_key if process_key == "get_data" else "sim_server")
                    
            self.processes[process_key] = None
            self.log(f"{process_key.capitalize()} tamamlandı.", process_key if process_key == "get_data" else "sim_server")
        except Exception as e:
            self.log(f"Hata ({process_key}): {str(e)}", process_key if process_key == "get_data" else "sim_server")
            self.processes[process_key] = None
    
    def start_world(self):
        """Gazebo simülasyonunu başlat"""
        if self.processes["world"] is None:
            command = "python3 gazebo_simulation.py"
            thread = threading.Thread(target=self.run_command, args=(command, "world"))
            thread.start()
        else:
            self.log("World zaten çalışıyor!", "sim_server")
    
    def start_server(self):
        """Server'ı başlat"""
        if self.processes["server"] is None:
            command = "python3 server6.py"
            thread = threading.Thread(target=self.run_command, args=(command, "server"))
            thread.start()
        else:
            self.log("Server zaten çalışıyor!", "sim_server")
    
    def get_data(self):
        """Server'dan veri al"""
        if self.processes["get_data"] is None:
            command = "python3 get.py"
            thread = threading.Thread(target=self.run_command, args=(command, "get_data"))
            thread.start()
        else:
            self.log("Get Data zaten çalışıyor!", "get_data")
    
    def stop_process(self, process_key):
        """Belirtilen süreci durdur"""
        process = self.processes.get(process_key)
        if process is not None:
            try:
                if os.name == 'nt':  # Windows
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
                else:  # Unix/Linux
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=3)
                self.log(f"{process_key.capitalize()} durduruldu.", process_key if process_key == "get_data" else "sim_server")
            except Exception as e:
                self.log(f"{process_key.capitalize()} durdurulurken hata: {str(e)}", process_key if process_key == "get_data" else "sim_server")
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                self.log(f"{process_key.capitalize()} zorla kapatıldı.", process_key if process_key == "get_data" else "sim_server")
            finally:
                self.processes[process_key] = None
        else:
            self.log(f"{process_key.capitalize()} zaten kapalı veya çalışmıyor.", process_key if process_key == "get_data" else "sim_server")
    
    def stop_world(self):
        """Gazebo simülasyonunu durdur"""
        self.stop_process("world")
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
        self.log("Tüm süreçler durduruluyor...", "sim_server")
        self.log("Tüm süreçler durduruluyor...", "get_data")
        for key in self.processes.keys():
            self.stop_process(key)
        subprocess.run("rosnode kill -a", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run("killall -9 gzserver gzclient", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationGUI(root)
    root.mainloop()