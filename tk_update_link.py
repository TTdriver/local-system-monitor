"""Muted bottom-right link; all widget operations run on the Tk GUI thread."""
import queue
import tkinter as tk
import webbrowser
from update_check import UpdateCheck

class UpdateLink:
    def __init__(self, root, installed, api_url, download_url, user_agent, bg, muted, check=None):
        self.root = root
        self.download_url = download_url
        self.footer = tk.Frame(root, bg=bg, height=22)
        self.footer.pack(side='bottom', fill='x', padx=20, pady=(0, 5))
        self.footer.pack_propagate(False)
        self.label = tk.Label(self.footer, text='', bg=bg, fg=muted, font=('Sans', 9), anchor='e')
        self.label.bind('<Button-1>', self.open_download)
        self.label.bind('<Return>', self.open_download)
        kwargs = {'check': check} if check else {}
        self.check = UpdateCheck(installed, api_url, user_agent, **kwargs)
        self.check.start()
        root.after(100, self.poll)

    def poll(self):
        try:
            version = self.check.results.get_nowait()
        except queue.Empty:
            self.root.after(100, self.poll)
            return
        if version:
            self.label.configure(text=f'Update available · v{version} ↗', cursor='hand2', takefocus=True)
            self.label.pack(side='right')
        # No recurring checks or polling after the one result is consumed.

    def open_download(self, event=None):
        webbrowser.open(self.download_url)
