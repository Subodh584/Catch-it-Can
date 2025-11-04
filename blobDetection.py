import cv2
import numpy as np
import requests
import time
from tkinter import Tk, Toplevel, Label, LabelFrame, Scale, Button, DoubleVar, HORIZONTAL
from PIL import Image, ImageTk

class AutonomousBlobTracker:
    def __init__(self, esp32_ip="192.168.4.1", root=None):
        # ESP32 connection
        self.esp32_ip = esp32_ip
        self.esp32_url = f"http://{esp32_ip}/control"
        
        # Default HSV color range (Blue)
        self.lower_hsv = np.array([34, 64, 143])
        self.upper_hsv = np.array([66, 146, 255])

        # Blob size limits (in pixels)
        self.min_blob_area = 500
        self.max_blob_area = 50000
        
        # Tracking state
        self.last_position = None
        self.frames_lost = 0
        self.max_frames_lost = 10
        
        # Control parameters
        self.dead_zone = 30  # Pixels from center where no movement needed
        self.base_speed = 100  # Base motor speed (increased for faster response)
        self.max_speed = 255  # Maximum motor speed
        self.min_motor_speed = 180  # Minimum motor speed
        
        # Movement timing
        self.last_command_time = 0
        self.command_interval = 0.05  # Send commands every 50ms for faster response
        
        # Tkinter root window (hidden)
        self.root = root
        
        # HSV Finder window reference
        self.hsv_finder_window = None
        
        # ESP32 connection test
        self.test_connection()
        
    def test_connection(self):
        """Test connection to ESP32"""
        try:
            response = requests.get(f"http://{self.esp32_ip}/", timeout=2)
            if response.status_code == 200:
                print("✓ Connected to ESP32 successfully!")
                return True
        except:
            print("✗ Warning: Could not connect to ESP32")
            print(f"  Make sure ESP32 is powered on and you're connected to WiFi: ESP32_Motor_Control")
            print(f"  ESP32 IP should be: {self.esp32_ip}")
        return False
    
    def send_motor_command(self, speed):
        """
        Send movement command to ESP32
        speed > 0: Move FORWARD (object is below center)
        speed < 0: Move BACKWARD (object is above center)
        speed = 0: STOP
        """
        try:
            # Both motors get same speed for linear movement
            # Send commands in parallel for faster response
            params_a = {'motor': 'A', 'speed': speed}
            params_b = {'motor': 'B', 'speed': speed}
            
            requests.get(self.esp32_url, params=params_a, timeout=0.3)
            requests.get(self.esp32_url, params=params_b, timeout=0.3)
            return True
        except:
            return False
    
    def open_hsv_finder(self):
        """Open the HSV Range Finder window"""
        # Check if window exists and is still valid
        if self.hsv_finder_window is not None:
            try:
                if self.hsv_finder_window.winfo_exists():
                    self.hsv_finder_window.lift()
                    self.hsv_finder_window.focus()
                    return
                else:
                    # Window was destroyed, reset reference
                    self.hsv_finder_window = None
            except:
                # Window is invalid, reset reference
                self.hsv_finder_window = None
        
        print("Opening HSV Range Finder...")
        
        # Create HSV Finder window
        self.hsv_finder_window = Toplevel(self.root)
        self.hsv_finder_window.geometry('910x600')
        self.hsv_finder_window.title('HSV Range Finder')
        self.hsv_finder_window.resizable(0, 0)
        
        # Initialize slider variables with current HSV values
        l_h, l_s, l_v = DoubleVar(), DoubleVar(), DoubleVar()
        u_h, u_s, u_v = DoubleVar(), DoubleVar(), DoubleVar()
        
        l_h.set(self.lower_hsv[0])
        l_s.set(self.lower_hsv[1])
        l_v.set(self.lower_hsv[2])
        u_h.set(self.upper_hsv[0])
        u_s.set(self.upper_hsv[1])
        u_v.set(self.upper_hsv[2])
        
        # --- Camera Frames ---
        mainCameraFrame = LabelFrame(self.hsv_finder_window, text='Main Camera')
        mainCameraFrame.place(x=0, y=0)
        vidLabel1 = Label(mainCameraFrame)
        vidLabel1.configure(width=300, height=400)
        vidLabel1.pack()
        
        contourCameraFrame = LabelFrame(self.hsv_finder_window, text='Result Camera')
        contourCameraFrame.place(x=305, y=0)
        vidLabel2 = Label(contourCameraFrame)
        vidLabel2.configure(width=300, height=400)
        vidLabel2.pack()
        
        outCameraFrame = LabelFrame(self.hsv_finder_window, text='Binary Mask')
        outCameraFrame.place(x=600, y=0)
        vidLabel3 = Label(outCameraFrame)
        vidLabel3.configure(width=300, height=400)
        vidLabel3.pack()
        
        # --- Slider Section ---
        sliderFrame = LabelFrame(self.hsv_finder_window, text='HSV Range Adjustment')
        sliderFrame.place(x=0, y=425)
        
        # Lower HSV sliders
        Label(sliderFrame, text='Lower Hue:').grid(row=0, column=0)
        lhSlider = Scale(sliderFrame, orient=HORIZONTAL, from_=0, to=179, variable=l_h)
        lhSlider.grid(row=0, column=1)
        
        Label(sliderFrame, text='Lower Saturation:').grid(row=0, column=2)
        lsSlider = Scale(sliderFrame, orient=HORIZONTAL, from_=0, to=255, variable=l_s)
        lsSlider.grid(row=0, column=3)
        
        Label(sliderFrame, text='Lower Value:').grid(row=0, column=4)
        lvSlider = Scale(sliderFrame, orient=HORIZONTAL, from_=0, to=255, variable=l_v)
        lvSlider.grid(row=0, column=5)
        
        # Upper HSV sliders
        Label(sliderFrame, text='Upper Hue:').grid(row=1, column=0)
        uhSlider = Scale(sliderFrame, orient=HORIZONTAL, from_=0, to=179, variable=u_h)
        uhSlider.grid(row=1, column=1)
        
        Label(sliderFrame, text='Upper Saturation:').grid(row=1, column=2)
        usSlider = Scale(sliderFrame, orient=HORIZONTAL, from_=0, to=255, variable=u_s)
        usSlider.grid(row=1, column=3)
        
        Label(sliderFrame, text='Upper Value:').grid(row=1, column=4)
        uvSlider = Scale(sliderFrame, orient=HORIZONTAL, from_=0, to=255, variable=u_v)
        uvSlider.grid(row=1, column=5)
        
        # --- Result Display Frame ---
        resultFrame = LabelFrame(self.hsv_finder_window, text='Current HSV Values')
        resultFrame.place(x=680, y=425)
        
        Label(resultFrame, text='Lower HSV').grid(row=0, column=0, columnspan=3)
        lhShow = Label(resultFrame, text=str(int(l_h.get())), width=5)
        lhShow.grid(row=1, column=0)
        lsShow = Label(resultFrame, text=str(int(l_s.get())), width=5)
        lsShow.grid(row=1, column=1)
        lvShow = Label(resultFrame, text=str(int(l_v.get())), width=5)
        lvShow.grid(row=1, column=2)
        
        Label(resultFrame, text='Upper HSV').grid(row=2, column=0, columnspan=3)
        uhShow = Label(resultFrame, text=str(int(u_h.get())), width=5)
        uhShow.grid(row=3, column=0)
        usShow = Label(resultFrame, text=str(int(u_s.get())), width=5)
        usShow.grid(row=3, column=1)
        uvShow = Label(resultFrame, text=str(int(u_v.get())), width=5)
        uvShow.grid(row=3, column=2)
        
        # Open camera for preview (try index 0, if busy try index 1)
        cap_preview = cv2.VideoCapture(0)
        if not cap_preview.isOpened():
            print("Camera 0 busy, trying camera 1...")
            cap_preview = cv2.VideoCapture(1)
        
        if not cap_preview.isOpened():
            print("❌ Error: Could not open camera for HSV preview")
            self.hsv_finder_window.destroy()
            self.hsv_finder_window = None
            return
        
        print("✓ HSV Finder camera opened successfully")
        
        # Apply button
        def apply_hsv():
            self.lower_hsv = np.array([int(l_h.get()), int(l_s.get()), int(l_v.get())])
            self.upper_hsv = np.array([int(u_h.get()), int(u_s.get()), int(u_v.get())])
            print(f"✓ Applied new HSV values:")
            print(f"  Lower: {self.lower_hsv}")
            print(f"  Upper: {self.upper_hsv}")
            try:
                cap_preview.release()
            except:
                pass
            try:
                self.hsv_finder_window.destroy()
            except:
                pass
            self.hsv_finder_window = None
            print("HSV Finder closed")
        
        applyBtn = Button(resultFrame, text='Apply & Close', command=apply_hsv, 
                         bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'))
        applyBtn.grid(row=4, column=0, columnspan=3, pady=10)
        
        # Update function for video feed
        def update_hsv_preview():
            try:
                if self.hsv_finder_window is None or not self.hsv_finder_window.winfo_exists():
                    return
                
                ret, frame = cap_preview.read()
                if not ret:
                    self.hsv_finder_window.after(10, update_hsv_preview)
                    return
            except:
                return
            
            # Update display labels
            lhShow.configure(text=str(int(l_h.get())))
            lsShow.configure(text=str(int(l_s.get())))
            lvShow.configure(text=str(int(l_v.get())))
            uhShow.configure(text=str(int(u_h.get())))
            usShow.configure(text=str(int(u_s.get())))
            uvShow.configure(text=str(int(u_v.get())))
            
            # Get current slider values
            lower_bound = np.array([l_h.get(), l_s.get(), l_v.get()])
            upper_bound = np.array([u_h.get(), u_s.get(), u_v.get()])
            
            # Convert frame to HSV and apply mask
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, lower_bound, upper_bound)
            filtered_frame = cv2.bitwise_and(frame, frame, mask=mask)
            
            # Convert frames for display
            img1 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img1 = Image.fromarray(img1)
            img1 = ImageTk.PhotoImage(image=img1)
            
            img2 = cv2.cvtColor(filtered_frame, cv2.COLOR_BGR2RGB)
            img2 = Image.fromarray(img2)
            img2 = ImageTk.PhotoImage(image=img2)
            
            img3 = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
            img3 = Image.fromarray(img3)
            img3 = ImageTk.PhotoImage(image=img3)
            
            # Update labels
            vidLabel1.config(image=img1)
            vidLabel1.image = img1
            vidLabel2.config(image=img2)
            vidLabel2.image = img2
            vidLabel3.config(image=img3)
            vidLabel3.image = img3
            
            self.hsv_finder_window.after(10, update_hsv_preview)
        
        # Cleanup function
        def on_closing():
            try:
                cap_preview.release()
            except:
                pass
            try:
                self.hsv_finder_window.destroy()
            except:
                pass
            self.hsv_finder_window = None
            print("HSV Finder closed")
        
        self.hsv_finder_window.protocol("WM_DELETE_WINDOW", on_closing)
        update_hsv_preview()
    
    def detect_blob(self, frame):
        """Detect the colored blob in the frame"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_hsv, self.upper_hsv)
        
        # Remove noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        return mask
    
    def get_average_position(self, mask):
        """Calculate average position of all white pixels"""
        y_coords, x_coords = np.where(mask == 255)
        
        if len(x_coords) == 0 or len(y_coords) == 0:
            return None, 0
        
        area = len(x_coords)
        
        if area < self.min_blob_area or area > self.max_blob_area:
            return None, 0
        
        avg_x = int(np.mean(x_coords))
        avg_y = int(np.mean(y_coords))
        
        return (avg_x, avg_y), area
    
    def calculate_motor_speed(self, center, frame_shape):
        """
        Calculate motor speed based on vertical position
        Returns: (speed, command_text)
        
        IMPORTANT: Y-axis movement control
        - Object ABOVE center (low Y value) → Move BACKWARD (negative speed)
        - Object BELOW center (high Y value) → Move FORWARD (positive speed)
        - Object in dead zone → STOP
        """
        height, width = frame_shape[:2]
        frame_center_y = height // 2
        
        if center is None:
            return 0, "STOP - Lost tracking"
        
        cx, cy = center
        
        # Calculate vertical error (positive = object is below center)
        error_y = cy - frame_center_y
        
        # Check if in dead zone
        if abs(error_y) < self.dead_zone:
            return 0, "CENTERED - In dead zone"
        
        # Calculate proportional speed based on error
        # Larger error = faster speed (more aggressive speed curve)
        speed_factor = min(abs(error_y) / (height * 0.4), 1.0)  # Reach max speed at 40% of frame height
        speed = int(self.base_speed + (self.max_speed - self.base_speed) * speed_factor)
        
        # Get minimum speed from trackbar (or default to 180)
        min_speed = getattr(self, 'min_motor_speed', 180)
        speed = max(min_speed, min(speed, self.max_speed))  # Clamp between min and max
        
        if error_y > 0:
            # Object is BELOW center → Move FORWARD
            return speed, f"FORWARD {speed} - Object below (Err: +{error_y}px)"
        else:
            # Object is ABOVE center → Move BACKWARD
            return -speed, f"BACKWARD {speed} - Object above (Err: {error_y}px)"
    
    def draw_overlay(self, frame, center, area, command, motor_speed):
        """Draw tracking information on frame"""
        height, width = frame.shape[:2]
        frame_center_y = height // 2
        
        # Draw horizontal center line
        cv2.line(frame, (0, frame_center_y), (width, frame_center_y), (255, 255, 255), 2)
        
        # Draw dead zone (horizontal band)
        cv2.rectangle(frame, 
                     (0, frame_center_y - self.dead_zone), 
                     (width, frame_center_y + self.dead_zone), 
                     (200, 200, 200), 1)
        
        if center:
            # Draw RED circle at average position
            cv2.circle(frame, center, 10, (0, 0, 255), -1)
            cv2.circle(frame, center, 15, (0, 0, 255), 2)
            
            # Draw line from blob to center line
            cv2.line(frame, center, (center[0], frame_center_y), (0, 255, 255), 2)
            
            # Display info
            cv2.putText(frame, f"Pixels: {area}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, f"Position: {center}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, f"Motor Speed: {motor_speed}", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Display current HSV values (top right corner)
        cv2.putText(frame, f"HSV Lower: [{self.lower_hsv[0]}, {self.lower_hsv[1]}, {self.lower_hsv[2]}]", 
                   (width - 400, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"HSV Upper: [{self.upper_hsv[0]}, {self.upper_hsv[1]}, {self.upper_hsv[2]}]", 
                   (width - 400, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Display command
        cv2.putText(frame, command, (10, height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Display help text for HSV adjustment
        cv2.putText(frame, "Press 'a' to adjust HSV", (10, height - 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        # Draw direction indicator
        if "FORWARD" in command:
            cv2.arrowedLine(frame, (width - 50, height - 50), (width - 50, height - 100), 
                          (0, 255, 0), 3, tipLength=0.3)
        elif "BACKWARD" in command:
            cv2.arrowedLine(frame, (width - 50, height - 100), (width - 50, height - 50), 
                          (0, 0, 255), 3, tipLength=0.3)
        
        return frame
    


def main():
    print("=" * 60)
    print("AUTONOMOUS BLOB TRACKER WITH ESP32 CONTROL")
    print("=" * 60)
    print("\n📋 SETUP INSTRUCTIONS:")
    print("1. Power on your ESP32")
    print("2. Connect to WiFi network: 'ESP32_Motor_Control'")
    print("3. Password: '12345678'")
    print("4. ESP32 IP Address: 192.168.4.1")
    print("\n🎮 CONTROLS:")
    print("  - 'a' - Open HSV adjustment window")
    print("  - 'q' - Quit program")
    print("  - 's' - Display current settings")
    print("  - SPACE - Emergency stop")
    print("\n🤖 TRACKING MODE:")
    print("  - Object ABOVE center → Motors move BACKWARD")
    print("  - Object BELOW center → Motors move FORWARD")
    print("  - Object in dead zone → Motors STOP")
    print("=" * 60)
    
    esp32_ip = input("\nEnter ESP32 IP address (default: 192.168.4.1): ").strip()
    if not esp32_ip:
        esp32_ip = "192.168.4.1"
    
    # Initialize hidden Tkinter root window
    root = Tk()
    root.withdraw()  # Hide the root window
    
    # Initialize tracker with root window
    tracker = AutonomousBlobTracker(esp32_ip, root)
    
    # Open camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Could not open camera")
        return
    
    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("\n✓ Camera opened successfully")
    print("✓ System ready - Starting autonomous tracking...\n")
    print("💡 Press 'a' to open HSV calibration window")
    
    # Create window
    cv2.namedWindow('Autonomous Blob Tracker')
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break
            
            # Detect blob and get mask
            mask = tracker.detect_blob(frame)
            
            # Get average position of all white pixels
            center, area = tracker.get_average_position(mask)
            
            # Calculate motor speed and command
            motor_speed, command = tracker.calculate_motor_speed(center, frame.shape)
            
            # Send command to ESP32 (with rate limiting)
            current_time = time.time()
            if current_time - tracker.last_command_time >= tracker.command_interval:
                if tracker.send_motor_command(motor_speed):
                    tracker.last_command_time = current_time
            
            # Draw overlay with Adjust button
            frame = tracker.draw_overlay(frame, center, area, command, motor_speed)
            
            # Show frames
            cv2.imshow('Autonomous Blob Tracker', frame)
            
            # Update Tkinter event loop only if HSV finder is open
            if tracker.hsv_finder_window is not None:
                try:
                    root.update()
                except:
                    pass
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nStopping motors and exiting...")
                tracker.send_motor_command(0)
                break
            elif key == ord(' '):  # Emergency stop
                print("\n⚠️ EMERGENCY STOP!")
                tracker.send_motor_command(0)
            elif key == ord('a'):  # Alternative: press 'a' to open adjustment window
                tracker.open_hsv_finder()
            elif key == ord('s'):
                print(f"\n💾 Current Settings:")
                print(f"Lower HSV: {tracker.lower_hsv}")
                print(f"Upper HSV: {tracker.upper_hsv}")
                print(f"Min Area: {tracker.min_blob_area}")
                print(f"Max Area: {tracker.max_blob_area}")
                print(f"Dead Zone: {tracker.dead_zone}")
                print(f"Base Speed: {tracker.base_speed}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Keyboard interrupt - Stopping motors...")
        tracker.send_motor_command(0)
    
    finally:
        # Clean shutdown
        tracker.send_motor_command(0)
        cap.release()
        cv2.destroyAllWindows()
        if root:
            try:
                root.destroy()
            except:
                pass
        print("✓ System shutdown complete")

if __name__ == "__main__":
    main()
