import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import os
import signal
import sys

class SimulationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulation Control Panel")
        
        self.processes = {
            "world": None,
            "server": None,
            "get_data": None
        }
        
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=10)
        
        self.start_world_btn = tk.Button(self.button_frame, text="Start World", command=self.start_world)
        self.start_world_btn.pack(side=tk.LEFT, padx=5)
        
        self.start_server_btn = tk.Button(self.button_frame, text="Start Server", command=self.start_server)
        self.start_server_btn.pack(side=tk.LEFT, padx=5)
        
        self.get_data_btn = tk.Button(self.button_frame, text="Get Data", command=self.get_data)
        self.get_data_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_world_btn = tk.Button(self.button_frame, text="Stop World", command=self.stop_world)
        self.stop_world_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_server_btn = tk.Button(self.button_frame, text="Stop Server", command=self.stop_server)
        self.stop_server_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_get_data_btn = tk.Button(self.button_frame, text="Stop Get Data", command=self.stop_get_data)
        self.stop_get_data_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_all_btn = tk.Button(self.button_frame, text="Stop All", command=self.stop_all)
        self.stop_all_btn.pack(side=tk.LEFT, padx=5)
        
        self.log_frame = tk.Frame(root)
        self.log_frame.pack(pady=10)
        
        self.sim_server_log_label = tk.Label(self.log_frame, text="Simulation & Server Log")
        self.sim_server_log_label.pack()
        self.sim_server_log = scrolledtext.ScrolledText(self.log_frame, width=80, height=10)
        self.sim_server_log.pack(pady=5)
        
        self.get_data_log_label = tk.Label(self.log_frame, text="Get Data Log")
        self.get_data_log_label.pack()
        self.get_data_log = scrolledtext.ScrolledText(self.log_frame, width=80, height=10)
        self.get_data_log.pack(pady=5)
        
    def log(self, message, log_type="sim_server"):
        if log_type == "get_data":
            self.get_data_log.insert(tk.END, message + "\n")
            self.get_data_log.see(tk.END)
        else:
            self.sim_server_log.insert(tk.END, message + "\n")
            self.sim_server_log.see(tk.END)
    
    def run_command(self, command, process_key):
        """Komut çalıştır ve çıktıları uygun log'a yaz"""
        try:
            # Tamponlamayı devre dışı bırakmak için PYTHONUNBUFFERED ve -u ekliyoruz
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            process = subprocess.Popen(
                command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1, 
                env=env,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            self.processes[process_key] = process
            self.log(f"{process_key.capitalize()} başlatıldı: {command}", process_key if process_key == "get_data" else "sim_server")
            
            # Gerçek zamanlı çıktı okuma
            while process.poll() is None:
                line = process.stdout.readline()
                if line:
                    self.log(line.strip(), process_key if process_key == "get_data" else "sim_server")
            for line in process.stdout.readlines():
                if line:
                    self.log(line.strip(), process_key if process_key == "get_data" else "sim_server")
                    
            self.processes[process_key] = None
            self.log(f"{process_key.capitalize()} tamamlandı.", process_key if process_key == "get_data" else "sim_server")
        except Exception as e:
            self.log(f"Hata ({process_key}): {str(e)}", process_key if process_key == "get_data" else "sim_server")
            self.processes[process_key] = None
    
    def start_world(self):
        if self.processes["world"] is None:
            command = "python3 gazebo_simulation.py"
            thread = threading.Thread(target=self.run_command, args=(command, "world"))
            thread.start()
        else:
            self.log("World zaten çalışıyor!", "sim_server")
    
    def start_server(self):
        if self.processes["server"] is None:
            command = "python3 server6.py"
            thread = threading.Thread(target=self.run_command, args=(command, "server"))
            thread.start()
        else:
            self.log("Server zaten çalışıyor!", "sim_server")
    
    def get_data(self):
        if self.processes["get_data"] is None:
            # -u ile tamponlamayı devre dışı bırakıyoruz
            command = "python3 -u get.py"
            thread = threading.Thread(target=self.run_command, args=(command, "get_data"))
            thread.start()
        else:
            self.log("Get Data zaten çalışıyor!", "get_data")
    
    def stop_process(self, process_key):
        process = self.processes.get(process_key)
        if process is not None:
            try:
                if os.name == 'nt':
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
                else:
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
        self.stop_process("world")
        if self.processes["world"] is None:
            subprocess.run("rosnode kill -a", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run("killall -9 gzserver gzclient", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def stop_server(self):
        self.stop_process("server")
    
    def stop_get_data(self):
        self.stop_process("get_data")
    
    def stop_all(self):
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