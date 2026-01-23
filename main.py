import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time

# Check for required libraries
missing_libraries = []

try:
    import cv2
except ImportError:
    missing_libraries.append("opencv-python")

try:
    from PIL import Image, ImageTk
except ImportError:
    missing_libraries.append("pillow")

if missing_libraries:
    root = tk.Tk()
    root.withdraw()
    
    error_msg = "Missing Required Libraries!\n\n"
    error_msg += "The following libraries are not installed:\n"
    for lib in missing_libraries:
        error_msg += f"  • {lib}\n"
    error_msg += "\nTo install them, open your terminal/command prompt and run:\n\n"
    error_msg += f"pip install {' '.join(missing_libraries)}\n\n"
    error_msg += "or\n\n"
    error_msg += f"python -m pip install {' '.join(missing_libraries)}"
    
    messagebox.showerror("Missing Dependencies", error_msg)
    root.destroy()
    sys.exit(1)


class CameraSelectionDialog:
    def __init__(self, parent, cameras, camera_names):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Video Input")
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Label
        label = ttk.Label(main_frame, text="Select a Video Input to mirror:", 
                         font=('Arial', 10, 'bold'))
        label.pack(pady=(0, 15))
        
        # Camera selection
        self.camera_var = tk.IntVar(value=0)
        radio_frame = ttk.Frame(main_frame)
        radio_frame.pack(pady=(0, 20))
        
        for idx, (cam_id, cam_name) in enumerate(zip(cameras, camera_names)):
            ttk.Radiobutton(radio_frame, text=cam_name, 
                           variable=self.camera_var, 
                           value=idx).pack(anchor=tk.W, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack()
        
        ok_btn = tk.Button(btn_frame, text="OK", command=self.ok, 
                          width=10, bg='#4CAF50', fg='white', 
                          font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2)
        ok_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=self.cancel,
                              width=10, bg='#f44336', fg='white',
                              font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Update and center dialog on screen
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
    def ok(self):
        self.result = self.camera_var.get()
        self.dialog.destroy()
    
    def cancel(self):
        self.result = None
        self.dialog.destroy()


class VideoMirrorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("4K Video Mirror")
        self.root.configure(background='black')
        
        # Maximize window
        self.root.state('zoomed')
        try:
            self.root.attributes('-zoomed', True)
        except:
            pass
        
        self.cap = None
        self.running = False
        self.available_cameras = []
        
        # Frame buffer for thread-safe communication
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # FPS tracking
        self.fps = 0
        self.frame_count = 0
        self.fps_start_time = time.time()
        
        # Video frame only - centered
        self.video_frame = ttk.Label(self.root, background="black", anchor="center")
        self.video_frame.pack(expand=True, fill=tk.BOTH)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Detect cameras and show selection dialog
        self.root.after(100, self.detect_and_select_camera)
    
    def detect_and_select_camera(self):
        # Check for available cameras and get their names
        camera_names = []
        for i in range(6):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.available_cameras.append(i)
                # Try to get camera name
                backend = cap.getBackendName()
                # Get a more descriptive name if possible
                name = f"Video Input {i}"
                
                camera_names.append(name)
                cap.release()
        
        if not self.available_cameras:
            messagebox.showerror("Error", "No cameras detected!")
            self.root.quit()
            return
        
        # Show selection dialog
        if len(self.available_cameras) == 1:
            # Only one camera, ask to start
            if messagebox.askyesno("Start Mirroring", 
                                   f"{camera_names[0]} detected.\n\nStart mirroring in 4K?"):
                self.start_mirror(0)
            else:
                self.root.quit()
        else:
            # Multiple cameras, show selection dialog
            dialog = CameraSelectionDialog(self.root, self.available_cameras, camera_names)
            self.root.wait_window(dialog.dialog)
            
            if dialog.result is not None:
                self.start_mirror(dialog.result)
            else:
                self.root.quit()
    
    def start_mirror(self, camera_index):
        camera_id = self.available_cameras[camera_index]
        self.cap = cv2.VideoCapture(camera_id)
        
        if not self.cap.isOpened():
            messagebox.showerror("Error", f"Could not open camera {camera_id}")
            self.root.quit()
            return
        
        # Set 4K resolution (3840x2160)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        
        # Optimize camera settings for performance
        self.cap.set(cv2.CAP_PROP_FPS, 60)  # Request 60 FPS
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize latency
        
        # Verify the resolution that was actually set
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        
        print(f"Camera resolution set to: {actual_width}x{actual_height} @ {actual_fps} FPS")
        
        # If 4K not supported, try other high resolutions
        if actual_width < 3840:
            print("4K not supported, camera is using its maximum resolution")
        
        self.running = True
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
        self.capture_thread.start()
        
        # Start display update
        self.update_display()
    
    def capture_frames(self):
        """Separate thread for capturing frames from camera"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Convert from BGR to RGB immediately
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Update shared frame buffer
                with self.frame_lock:
                    self.current_frame = rgb
    
    def update_display(self):
        """Update the display with the latest frame"""
        if not self.running:
            return
        
        # Get the latest frame
        with self.frame_lock:
            if self.current_frame is not None:
                rgb = self.current_frame.copy()
            else:
                self.root.after(5, self.update_display)
                return
        
        # Resize to fit window while maintaining aspect ratio
        h, w = rgb.shape[:2]
        frame_width = self.video_frame.winfo_width()
        frame_height = self.video_frame.winfo_height()
        
        if frame_width > 1 and frame_height > 1:
            scale = min(frame_width/w, frame_height/h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # Use INTER_NEAREST for faster scaling (or INTER_LINEAR for better quality)
            rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Convert to PhotoImage
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        
        self.video_frame.imgtk = imgtk
        self.video_frame.config(image=imgtk)
        
        # Schedule next update (5ms for ~200fps max)
        self.root.after(5, self.update_display)
    
    def on_closing(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoMirrorApp(root)
    root.mainloop()