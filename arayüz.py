import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading

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
        """Komut çalıştır ve cmd çıktılarını log'a yaz"""
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            self.processes[process_key] = process  # Süreci kaydet
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.log(line.strip())
            for line in iter(process.stderr.readline, ''):
                if line:
                    self.log(f"ERROR: {line.strip()}")
            process.wait()
            self.processes[process_key] = None  # Süreç bittiğinde temizle
        except Exception as e:
            self.log(f"Komut çalıştırılırken hata: {str(e)}")
            self.processes[process_key] = None
    
    def start_world(self):
        """Gazebo simülasyonunu başlat"""
        if self.processes["world"] is None:
            self.log("Starting Gazebo simulation...")
            thread = threading.Thread(target=self.run_command, args=(["python3", "launch_world.py"], "world"))
            thread.start()
        else:
            self.log("World zaten çalışıyor!")
    
    def start_server(self):
        """Server'ı başlat"""
        if self.processes["server"] is None:
            self.log("Starting server...")
            thread = threading.Thread(target=self.run_command, args=(["python3", "server.py"], "server"))
            thread.start()
        else:
            self.log("Server zaten çalışıyor!")
    
    def get_data(self):
        """Server'dan veri al"""
        if self.processes["get_data"] is None:
            self.log("Fetching data from server...")
            thread = threading.Thread(target=self.run_command, args=(["python3", "get_data.py"], "get_data"))
            thread.start()
        else:
            self.log("Get Data zaten çalışıyor!")
    
    def stop_process(self, process_key):
        """Belirtilen süreci durdur"""
        process = self.processes.get(process_key)
        if process is not None:
            process.terminate()  # Süreci sonlandır
            try:
                process.wait(timeout=2)  # 2 saniye bekle
            except subprocess.TimeoutExpired:
                process.kill()  # Eğer terminate işe yaramazsa zorla kapat
            self.processes[process_key] = None
            self.log(f"{process_key.capitalize()} durduruldu.")
        else:
            self.log(f"{process_key.capitalize()} zaten kapalı veya çalışmıyor.")
    
    def stop_world(self):
        """Gazebo simülasyonunu durdur"""
        self.stop_process("world")
    
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

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationGUI(root)
    root.mainloop()