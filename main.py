import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import sys
import re
import time
from PIL import Image, ImageTk

# --- Theme Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class VideoRow(ctk.CTkFrame):
    def __init__(self, master, file_path, index, thumb_path, resolution, delete_callback):
        super().__init__(master, height=110, corner_radius=15, fg_color="#1e1e1e", border_width=1, border_color="#333")
        self.pack_propagate(False)
        self.file_path = file_path

        self.thumb_frame = ctk.CTkFrame(self, width=120, height=80, corner_radius=10, fg_color="#000")
        self.thumb_frame.pack(side="left", padx=15, pady=15)
        self.thumb_frame.pack_propagate(False)

        try:
            img = Image.open(thumb_path).resize((120, 80))
            self.photo = ImageTk.PhotoImage(img)
            ctk.CTkLabel(self.thumb_frame, image=self.photo, text="").pack()
        except:
            ctk.CTkLabel(self.thumb_frame, text="NO PREVIEW", font=("Arial", 10)).pack(expand=True)

        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", padx=10, fill="both", expand=True)

        name = os.path.basename(file_path)
        display_name = (name[:25] + '...') if len(name) > 25 else name
        ctk.CTkLabel(info_frame, text=display_name, font=("Segoe UI", 15, "bold"), anchor="w").pack(pady=(20, 0))
        ctk.CTkLabel(info_frame, text=f"Source: {resolution}", font=("Segoe UI", 11), text_color="#aaa", anchor="w").pack()

        self.p_bar = ctk.CTkProgressBar(self, width=280, height=12, progress_color="#3498db", fg_color="#333")
        self.p_bar.set(0)
        self.p_bar.pack(side="left", padx=20)

        self.status_label = ctk.CTkLabel(self, text="READY", width=100, font=("Segoe UI", 12, "bold"), text_color="#3498db")
        self.status_label.pack(side="left", padx=5)

        self.btn_del = ctk.CTkButton(self, text="✕", width=35, height=35, corner_radius=10,
                                     fg_color="#2a2a2a", hover_color="#e74c3c",
                                     command=lambda: delete_callback(self))
        self.btn_del.pack(side="right", padx=20)

class AdvancedVideoEncoder(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AdvancedVideoEncoder Pro by sudipto-dev-app")
        self.geometry("1350x980")

        self.ffmpeg_path = get_resource_path(os.path.join("bin", "ffmpeg.exe"))
        self.ffprobe_path = get_resource_path(os.path.join("bin", "ffprobe.exe"))

        self.queue = []
        self.output_dir = ""
        self.is_cancelling = False
        self.current_process = None

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#111")
        self.sidebar.pack(side="left", fill="y")

        branding_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        branding_frame.pack(pady=25, padx=20, fill="x")
        ctk.CTkLabel(branding_frame, text="AdvancedEncoder", font=("Segoe UI", 24, "bold"), text_color="#3498db").pack(anchor="w")
        ctk.CTkLabel(branding_frame, text="by sudipto-dev-app", font=("Segoe UI", 12), text_color="#666").pack(anchor="w")

        self.setup_controls()

        # --- Main Area ---
        self.main_area = ctk.CTkFrame(self, fg_color="#121212", corner_radius=0)
        self.main_area.pack(side="right", fill="both", expand=True)

        self.header = ctk.CTkFrame(self.main_area, fg_color="#1a1a1a", height=80, corner_radius=0)
        self.header.pack(fill="x")
        ctk.CTkLabel(self.header, text="Media Queue", font=("Segoe UI", 20, "bold")).pack(side="left", padx=30)

        self.btn_add = ctk.CTkButton(self.header, text="+ ADD VIDEOS", command=self.add_to_queue,
                                     fg_color="#3498db", hover_color="#2980b9", width=140, height=35, font=("Segoe UI", 12, "bold"))
        self.btn_add.pack(side="right", padx=30)

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.bottom_bar = ctk.CTkFrame(self.main_area, height=140, fg_color="#1a1a1a", corner_radius=20)
        self.bottom_bar.pack(fill="x", padx=20, pady=(0, 20))

        self.btn_dest = ctk.CTkButton(self.bottom_bar, text="📁 Set Export Folder", command=self.select_dest,
                                      fg_color="#333", hover_color="#444", height=45)
        self.btn_dest.place(relx=0.05, rely=0.3)

        self.dest_label = ctk.CTkLabel(self.bottom_bar, text="No folder selected", text_color="#888")
        self.dest_label.place(relx=0.05, rely=0.65)

        self.btn_start = ctk.CTkButton(self.bottom_bar, text="START BATCH", command=self.start_process,
                                       fg_color="#27ae60", hover_color="#219150", width=180, height=50, font=("Segoe UI", 14, "bold"))
        self.btn_start.place(relx=0.8, rely=0.3)

        self.btn_cancel = ctk.CTkButton(self.bottom_bar, text="STOP", command=self.cancel_process,
                                        fg_color="#c0392b", state="disabled", width=80, height=50)
        self.btn_cancel.place(relx=0.72, rely=0.3)

        self.overall_pbar = ctk.CTkProgressBar(self.main_area, height=6, progress_color="#3498db", fg_color="#222")
        self.overall_pbar.set(0)
        self.overall_pbar.pack(fill="x", side="bottom")

    def setup_controls(self):
        # Bitrate
        ctk.CTkLabel(self.sidebar, text="Video Bitrate (Mbps)", font=("Segoe UI", 12, "bold")).pack(pady=(10, 5))
        self.mbps_val = 5.0
        v_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        v_frame.pack(pady=5)
        ctk.CTkButton(v_frame, text="-", width=35, fg_color="#222", command=self.dec_mbps).grid(row=0, column=0, padx=5)
        self.v_entry = ctk.CTkEntry(v_frame, width=70, justify="center")
        self.v_entry.insert(0, "5.0")
        self.v_entry.grid(row=0, column=1)
        ctk.CTkButton(v_frame, text="+", width=35, fg_color="#222", command=self.inc_mbps).grid(row=0, column=2, padx=5)

        # Dropdowns
        self.create_dropdown("Output Resolution", ["Original", "3840x2160 (4K)", "1920x1080 (1080p)", "1280x720 (720p)", "640x360 (360p)", "Audio (MP3)"], "res_var")
        self.create_dropdown("Frame Rate (FPS)", ["Original", "60 FPS", "50 FPS", "30 FPS", "24 FPS"], "fps_var")
        self.create_dropdown("Audio Bitrate", ["128k", "192k", "256k", "320k"], "a_bitrate_var")
        self.create_dropdown("Hardware Engine", ["libx264 (CPU)", "h264_nvenc (NVIDIA)", "h264_amf (AMD)"], "gpu_var")
        self.create_dropdown("Output Format", ["mp4", "mkv", "mov", "avi"], "out_format_var")

        self.theme_var = ctk.StringVar(value="Dark")
        ctk.CTkSwitch(self.sidebar, text="Modern Dark Mode", command=self.toggle_theme, variable=self.theme_var, onvalue="Dark", offvalue="Light", progress_color="#3498db").pack(pady=30)

    def create_dropdown(self, label, values, var_name):
        ctk.CTkLabel(self.sidebar, text=label, font=("Segoe UI", 12, "bold")).pack(pady=(10, 0))
        setattr(self, var_name, ctk.StringVar(value=values[0]))
        ctk.CTkOptionMenu(self.sidebar, values=values, variable=getattr(self, var_name), fg_color="#222", button_color="#333").pack(pady=5, padx=20, fill="x")

    def toggle_theme(self):
        ctk.set_appearance_mode(self.theme_var.get())

    def inc_mbps(self):
        self.mbps_val += 0.5
        self.v_entry.delete(0, "end"); self.v_entry.insert(0, str(round(self.mbps_val, 1)))

    def dec_mbps(self):
        if self.mbps_val > 0.5:
            self.mbps_val -= 0.5
            self.v_entry.delete(0, "end"); self.v_entry.insert(0, str(round(self.mbps_val, 1)))

    def add_to_queue(self):
        files = filedialog.askopenfilenames(filetypes=[("Videos", "*.mp4 *.mkv *.avi *.mov")])
        for f in files:
            cmd = [self.ffprobe_path, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration", "-of", "default=noprint_wrappers=1", f]
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
            w = re.search(r"width=(\d+)", res); h = re.search(r"height=(\d+)", res); d = re.search(r"duration=([\d.]+)", res)
            dur = float(d.group(1)) if d else 0
            res_str = f"{w.group(1)}x{h.group(1)}" if w else "Unknown"

            idx = len(self.queue) + 1
            thumb = f"t_{int(time.time())}_{idx}.jpg"
            subprocess.run([self.ffmpeg_path, "-i", f, "-ss", "00:00:01", "-vframes", "1", "-y", thumb], creationflags=subprocess.CREATE_NO_WINDOW)

            row = VideoRow(self.scroll_frame, f, idx, thumb, res_str, self.remove_from_queue)
            row.pack(fill="x", pady=10, padx=10)
            self.queue.append({"path": f, "ui": row, "duration": dur, "thumb": thumb})

    def remove_from_queue(self, row_obj):
        for item in self.queue:
            if item["ui"] == row_obj:
                if os.path.exists(item["thumb"]): os.remove(item["thumb"])
                self.queue.remove(item); break
        row_obj.destroy()

    def select_dest(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir = path
            self.dest_label.configure(text=f"Export: {os.path.basename(path)}")

    def cancel_process(self):
        if self.current_process:
            self.is_cancelling = True
            self.current_process.kill()

    def start_process(self):
        if not self.queue or not self.output_dir:
            messagebox.showwarning("Warning", "Add files and set export folder!"); return
        self.is_cancelling = False
        self.btn_start.configure(state="disabled"); self.btn_cancel.configure(state="normal")
        threading.Thread(target=self.run_batch, daemon=True).start()

    def run_batch(self):
        total = len(self.queue)
        for i, item in enumerate(self.queue):
            if self.is_cancelling: break
            file_path, row_ui, duration = item["path"], item["ui"], item["duration"]
            out_ext = self.out_format_var.get()
            output_file = os.path.join(self.output_dir, f"Encoded_{os.path.basename(file_path).split('.')[0]}.{out_ext}")

            encoder = self.gpu_var.get().split(" ")[0]
            cmd = [self.ffmpeg_path, "-i", file_path, "-progress", "pipe:1", "-nostats",
                   "-c:v", encoder, "-b:v", f"{self.v_entry.get()}M"]

            # FPS Logic
            fps_val = self.fps_var.get()
            if fps_val != "Original":
                cmd.extend(["-r", fps_val.split(" ")[0]])

            # Resolution/Audio Logic
            res_val = self.res_var.get()
            if res_val != "Original":
                if "Audio" in res_val:
                    output_file = os.path.splitext(output_file)[0] + ".mp3"
                    cmd = [self.ffmpeg_path, "-i", file_path, "-vn", "-b:a", self.a_bitrate_var.get(), "-y", output_file]
                else:
                    cmd.extend(["-s", res_val.split(" ")[0]])

            # NVENC Specific tuning
            if "nvenc" in encoder:
                cmd.extend(["-preset", "p4", "-rc", "vbr", "-cq", "24"])

            cmd.extend(["-c:a", "aac", "-b:a", self.a_bitrate_var.get(), "-y", output_file])

            self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW)

            for line in iter(self.current_process.stdout.readline, ""):
                time_match = re.search(r"out_time_ms=(\d+)", line)
                if time_match and duration > 0:
                    prog = min((float(time_match.group(1)) / 1000000) / duration, 1.0)
                    self.after(0, lambda p=prog, r=row_ui: self.update_row(r, p))

            self.current_process.wait()
            self.after(0, lambda r=row_ui: self.mark_done(r))
            self.after(0, lambda v=(i+1)/total: self.overall_pbar.set(v))

        self.after(0, self.cleanup)

    def update_row(self, row, val):
        row.p_bar.set(val)
        row.status_label.configure(text=f"{int(val*100)}%")

    def mark_done(self, row):
        row.p_bar.set(1.0); row.status_label.configure(text="DONE ✅", text_color="#27ae60")

    def cleanup(self):
        self.btn_start.configure(state="normal"); self.btn_cancel.configure(state="disabled")
        for item in self.queue:
            if os.path.exists(item["thumb"]):
                try: os.remove(item["thumb"])
                except: pass

if __name__ == "__main__":
    app = AdvancedVideoEncoder()
    app.mainloop()