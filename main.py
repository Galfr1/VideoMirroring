import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

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
        self.root.title("Video Mirror")
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
        
        # Video frame only
        self.video_frame = ttk.Label(self.root, background="black")
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
                
                # On Windows, try to get a better name
                try:
                    # Read one frame to ensure camera is working
                    ret, _ = cap.read()
                    if ret:
                        # Try to get resolution for identification
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        name = f"Video Input {i} ({width}x{height})"
                except:
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
                                   f"{camera_names[0]} detected.\n\nStart mirroring?"):
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
        
        self.running = True
        self.update_frame()
    
    def update_frame(self):
        if not self.running:
            return
        
        ret, frame = self.cap.read()
        if ret:
            # Mirror the frame horizontally
            mirrored = cv2.flip(frame, 1)
            
            # Convert from BGR to RGB
            rgb = cv2.cvtColor(mirrored, cv2.COLOR_BGR2RGB)
            
            # Resize to fit window while maintaining aspect ratio
            h, w = rgb.shape[:2]
            frame_width = self.video_frame.winfo_width()
            frame_height = self.video_frame.winfo_height()
            
            if frame_width > 1 and frame_height > 1:
                scale = min(frame_width/w, frame_height/h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                rgb = cv2.resize(rgb, (new_w, new_h))
            
            # Convert to PhotoImage
            img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_frame.imgtk = imgtk
            self.video_frame.config(image=imgtk)
        
        # Schedule next update
        self.root.after(10, self.update_frame)
    
    def on_closing(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoMirrorApp(root)
    root.mainloop()