import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def get_startupinfo():
    """Prevent command windows from appearing on Windows."""
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return startupinfo
    return None


class MP4ToMP3App:

    def __init__(self, root):
        self.root = root
        self.root.title("MP4 to MP3 Converter")
        self.root.geometry("520x350")
        self.root.resizable(False, False)

        self.input_file = ""
        self.output_folder = ""

        tk.Label(
            root,
            text="MP4 → MP3",
            font=("Segoe UI", 22, "bold")
        ).pack(pady=(20, 5))

        tk.Label(
            root,
            text="Simple local audio converter",
            font=("Segoe UI", 10)
        ).pack()

        tk.Button(
            root,
            text="Choose MP4 File",
            width=25,
            command=self.choose_file
        ).pack(pady=(20, 5))

        self.file_label = tk.Label(
            root,
            text="No file selected",
            wraplength=450
        )
        self.file_label.pack()

        tk.Button(
            root,
            text="Choose Output Folder",
            width=25,
            command=self.choose_output
        ).pack(pady=(15, 5))

        self.output_label = tk.Label(
            root,
            text="Same folder as video",
            wraplength=450
        )
        self.output_label.pack()

        bitrate_frame = tk.Frame(root)
        bitrate_frame.pack(pady=15)

        tk.Label(
            bitrate_frame,
            text="MP3 Quality:"
        ).pack(side="left")

        self.bitrate = ttk.Combobox(
            bitrate_frame,
            values=["128k", "192k", "256k", "320k"],
            width=8,
            state="readonly"
        )

        self.bitrate.set("320k")
        self.bitrate.pack(side="left", padx=10)

        self.convert_button = tk.Button(
            root,
            text="Convert",
            width=25,
            height=2,
            command=self.convert
        )
        self.convert_button.pack(pady=5)

        self.status = tk.Label(
            root,
            text=""
        )
        self.status.pack(pady=5)

    def choose_file(self):

        file_path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[
                ("Video Files", "*.mp4 *.mkv *.mov *.avi *.webm"),
                ("All Files", "*.*")
            ]
        )

        if file_path:
            self.input_file = file_path

            self.file_label.config(
                text=os.path.basename(file_path)
            )

    def choose_output(self):

        folder = filedialog.askdirectory()

        if folder:
            self.output_folder = folder

            self.output_label.config(
                text=folder
            )

    def has_audio_stream(self, file_path):

        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            file_path
        ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=get_startupinfo()
            )

            data = json.loads(result.stdout)

            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    return True

            return False

        except FileNotFoundError:
            messagebox.showerror(
                "FFprobe Not Found",
                "FFprobe was not found.\n\n"
                "FFmpeg may not be installed correctly."
            )

            return False

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Could not inspect the video:\n\n{e}"
            )

            return False

    def convert(self):

        if not self.input_file:
            messagebox.showerror(
                "No File",
                "Choose a video first."
            )
            return

        self.status.config(
            text="Checking audio stream..."
        )

        self.root.update()

        # CHECK FOR AUDIO FIRST
        if not self.has_audio_stream(self.input_file):

            self.status.config(
                text="No audio track found."
            )

            messagebox.showerror(
                "No Audio Found",
                "This video does not contain an audio track.\n\n"
                "There is nothing to convert to MP3.\n\n"
                "If this video was downloaded from a website, "
                "you may have downloaded the video-only stream."
            )

            return

        if self.output_folder:
            folder = self.output_folder
        else:
            folder = os.path.dirname(self.input_file)

        filename = os.path.splitext(
            os.path.basename(self.input_file)
        )[0]

        output_file = os.path.join(
            folder,
            filename + ".mp3"
        )

        bitrate = self.bitrate.get()

        command = [
            "ffmpeg",
            "-y",

            "-i",
            self.input_file,

            "-map",
            "0:a:0",

            "-vn",

            "-codec:a",
            "libmp3lame",

            "-b:a",
            bitrate,

            output_file
        ]

        self.status.config(
            text="Converting..."
        )

        self.root.update()

        try:

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=get_startupinfo()
            )

            if result.returncode == 0:

                self.status.config(
                    text="Conversion complete."
                )

                messagebox.showinfo(
                    "Finished",
                    f"MP3 created successfully:\n\n{output_file}"
                )

            else:

                self.status.config(
                    text="Conversion failed."
                )

                messagebox.showerror(
                    "Conversion Failed",
                    result.stderr[-2000:]
                )

        except FileNotFoundError:

            messagebox.showerror(
                "FFmpeg Not Found",
                "FFmpeg could not be found.\n\n"
                "Make sure FFmpeg is installed and available in PATH."
            )


if __name__ == "__main__":

    root = tk.Tk()

    app = MP4ToMP3App(root)

    root.mainloop()