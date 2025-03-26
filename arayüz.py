import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading

class SimulationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulation Control Panel")
        
        # Butonlar için frame
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=10)
        
        # Start World Butonu
        self.start_world_btn = tk.Button(self.button_frame, text="Start World", command=self.start_world)
        self.start_world_btn.pack(side=tk.LEFT, padx=5)
        
        # Start Server Butonu
        self.start_server_btn = tk.Button(self.button_frame, text="Start Server", command=self.start_server)
        self.start_server_btn.pack(side=tk.LEFT, padx=5)
        
        # Get Data Butonu
        self.get_data_btn = tk.Button(self.button_frame, text="Get Data", command=self.get_data)
        self.get_data_btn.pack(side=tk.LEFT, padx=5)
        
        # Log çıktıları için sekme
        self.log_text = scrolledtext.ScrolledText(root, width=80, height=20)
        self.log_text.pack(pady=10)
        
    def log(self, message):
        """Log mesajlarını arayüze yaz"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # Otomatik aşağı kaydır
    
    def run_command(self, command):
        """Belirtilen komutu çalıştır ve çıktıları log'a yaz"""
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while True:
            output = process.stdout.readline()
            error = process.stderr.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                self.log(output.strip())
            if error:
                self.log(f"ERROR: {error.strip()}")
    
    def start_world(self):
        """Gazebo simülasyonunu başlat"""
        self.log("Starting Gazebo simulation...")
        # Arka planda çalıştırmak için thread kullanıyoruz
        thread = threading.Thread(target=self.run_command, args=(["python3", "launch_world.py"],))
        thread.start()
    
    def start_server(self):
        """Server'ı başlat"""
        self.log("Starting server...")
        thread = threading.Thread(target=self.run_command, args=(["python3", "server.py"],))
        thread.start()
    
    def get_data(self):
        """Server'dan veri al"""
        self.log("Fetching data from server...")
        thread = threading.Thread(target=self.run_command, args=(["python3", "get_data.py"],))
        thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulationGUI(root)
    root.mainloop()