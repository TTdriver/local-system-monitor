from pathlib import Path
#!/usr/bin/python3
"""Local desktop resource monitor. Local sensors and one optional GitHub update check; no privileged commands."""
import csv
import io
import queue
import subprocess
import threading
import tkinter as tk
from collections import deque
from datetime import datetime

import psutil

from tk_update_link import UpdateLink

APP_VERSION = '0.1.1'
UPDATE_VERSION_URL = 'https://api.github.com/repos/TTdriver/local-system-monitor/contents/VERSION'
DOWNLOAD_URL = 'https://github.com/TTdriver/local-system-monitor#installation'

BG = '#14171e'
CARD = '#202630'
TEXT = '#edf2fa'
MUTED = '#a1adbf'
CPU = '#61b6ff'
GPU = '#76d8ae'


def read_gpus():
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total,power.draw',
             '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=3, check=True,
        )
        rows = []
        for row in csv.reader(io.StringIO(result.stdout)):
            if len(row) != 6:
                continue
            values = []
            for value in row[1:]:
                try:
                    values.append(float(value.strip()))
                except ValueError:
                    values.append(None)
            rows.append(dict(zip(['name', 'usage', 'temperature', 'used', 'total', 'power'],
                                 [row[0].strip(), *values])))
        return rows
    except (OSError, subprocess.SubprocessError):
        return []


def cpu_temperature():
    try:
        sensors = psutil.sensors_temperatures()
        for name in ('coretemp', 'k10temp', 'zenpower', 'cpu_thermal'):
            readings = sensors.get(name, [])
            if readings:
                return max(r.current for r in readings)
    except (AttributeError, OSError):
        pass
    return None


def value(number, suffix='', digits=0):
    return 'Unavailable' if number is None else f'{number:.{digits}f}{suffix}'


class Panel:
    def __init__(self, parent, title, color):
        self.color = color
        self.history = deque(maxlen=60)
        self.frame = tk.Frame(parent, bg=CARD, padx=20, pady=15)
        self.frame.pack(fill='both', expand=True, pady=(0, 12))
        self.title = tk.Label(self.frame, text=title, bg=CARD, fg=MUTED,
                              font=('Sans', 11, 'bold'), anchor='w')
        self.title.pack(fill='x')
        self.usage = tk.Label(self.frame, text='—', bg=CARD, fg=color,
                              font=('Sans', 32, 'bold'), anchor='w')
        self.usage.pack(fill='x', pady=(5, 0))
        self.details = tk.Label(self.frame, text='Reading sensors…', bg=CARD, fg=TEXT,
                                font=('Sans', 10), anchor='w', justify='left')
        self.details.pack(fill='x', pady=(3, 8))
        self.graph = tk.Canvas(self.frame, bg=CARD, height=55, highlightthickness=0)
        self.graph.pack(fill='x')
        self.graph.bind('<Configure>', lambda _: self.draw())

    def update(self, usage, details):
        self.usage.config(text=value(usage, '%'))
        self.details.config(text=details)
        self.history.append(usage)
        self.draw()

    def draw(self):
        c = self.graph
        c.delete('all')
        w, h = c.winfo_width(), c.winfo_height()
        for y in (1, h / 2, h - 1):
            c.create_line(0, y, w, y, fill='#323b49')
        previous = None
        for i, usage in enumerate(self.history):
            if usage is None:
                previous = None
                continue
            point = ((60 - len(self.history) + i) * w / 59, h - 2 - max(0, min(100, usage)) * (h - 4) / 100)
            if previous:
                c.create_line(*previous, *point, fill=self.color, width=2)
            previous = point


class Monitor:
    def __init__(self):
        self.root = tk.Tk(className='LocalSystemMonitor')
        self.root.title('System Monitor')
        self.app_icon = tk.PhotoImage(file=str(Path(__file__).resolve().parent / 'app-icon.png'))
        self.root.iconphoto(True, self.app_icon)
        self.root.geometry('520x650')
        self.root.minsize(460, 600)
        self.root.configure(bg=BG)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.stop = threading.Event()
        self.samples = queue.Queue(maxsize=2)
        self.update_notice = UpdateLink(self.root, APP_VERSION, UPDATE_VERSION_URL, DOWNLOAD_URL, 'LocalSystemMonitor', BG, MUTED)
        outer = tk.Frame(self.root, bg=BG, padx=22, pady=18)
        outer.pack(fill='both', expand=True)
        heading = tk.Frame(outer, bg=BG)
        heading.pack(fill='x', pady=(0, 16))
        tk.Label(heading, text='SYSTEM MONITOR', bg=BG, fg=TEXT,
                 font=('Sans', 15, 'bold')).pack(side='left')
        self.on_top = tk.BooleanVar(value=False)
        tk.Checkbutton(heading, text='Keep on top', variable=self.on_top, bg=BG, fg=MUTED,
                       selectcolor=CARD, activebackground=BG, activeforeground=TEXT,
                       command=lambda: self.root.attributes('-topmost', self.on_top.get())).pack(side='right')
        self.cpu = Panel(outer, 'CPU', CPU)
        self.gpu = Panel(outer, 'GPU', GPU)
        self.ram = tk.Label(outer, text='Memory: reading…', bg=BG, fg=TEXT, anchor='w', font=('Sans', 11))
        self.ram.pack(fill='x', pady=(1, 8))
        self.status = tk.Label(outer, text='Local sensors · updates every second · 60-sample history',
                               bg=BG, fg=MUTED, anchor='w', font=('Sans', 9))
        self.status.pack(fill='x')
        threading.Thread(target=self.collect, daemon=True).start()
        self.root.after(100, self.refresh)

    def collect(self):
        psutil.cpu_percent(percpu=True)
        while not self.stop.wait(1):
            cores = psutil.cpu_percent(percpu=True)
            memory = psutil.virtual_memory()
            try:
                frequency = psutil.cpu_freq()
            except (OSError, NotImplementedError):
                frequency = None
            sample = (cores, memory, frequency, cpu_temperature(), read_gpus(), datetime.now())
            try:
                self.samples.put_nowait(sample)
            except queue.Full:
                self.samples.get_nowait()
                self.samples.put_nowait(sample)

    def refresh(self):
        latest = None
        try:
            while True:
                latest = self.samples.get_nowait()
        except queue.Empty:
            pass
        if latest:
            cores, memory, frequency, temperature, gpus, timestamp = latest
            usage = sum(cores) / len(cores) if cores else None
            frequency_text = value(frequency.current / 1000 if frequency else None, ' GHz', 2)
            self.cpu.update(usage, f'{len(cores)} logical cores  ·  {frequency_text}\n'
                            f'Temperature: {value(temperature, " °C")}  ·  Busiest core: {value(max(cores) if cores else None, "%")}')
            if gpus:
                gpu = gpus[0]
                self.gpu.title.config(text=gpu['name'].upper())
                used = value(gpu['used'] / 1024 if gpu['used'] is not None else None, '', 1)
                total = value(gpu['total'] / 1024 if gpu['total'] is not None else None, ' GB', 1)
                self.gpu.update(gpu['usage'], f'Temperature: {value(gpu["temperature"], " °C")}  ·  Power: {value(gpu["power"], " W")}\n'
                                f'GPU memory: {used} / {total}')
            else:
                self.gpu.update(None, 'NVIDIA GPU readings unavailable\nCheck that the NVIDIA driver is running.')
            self.ram.config(text=f'RAM  {memory.used / 1024**3:.1f} / {memory.total / 1024**3:.1f} GB  ·  {memory.percent:.0f}%')
            self.status.config(text=f'Updated {timestamp:%H:%M:%S}  ·  Local sensors  ·  60-sample history')
        self.root.after(200, self.refresh)

    def close(self):
        self.stop.set()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    Monitor().run()
