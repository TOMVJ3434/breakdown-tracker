import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import os
import time
from tkinter import messagebox

try:
    from pymodbus.client import ModbusTcpClient
    PLC_AVAILABLE = True
except ImportError:
    PLC_AVAILABLE = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# PLC Setup
PLC_IP = "192.168.1.10"
PLC_CONNECTED = False
plc = None

if PLC_AVAILABLE:
    try:
        plc = ModbusTcpClient(PLC_IP, port=502)
        if plc.connect():
            PLC_CONNECTED = True
    except:
        pass

PLC_REGS = {'CHECK': 100, 'OK': 101, 'NG': 102, 'SAVE_MASTER': 103, 'PART_NUM': 104}

# Variables
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

frame = None
capture_frame = None
roi_list = []        # [(x,y,w,h), (x,y,w,h), ...]
master_list = []     # [master_img1, master_img2, ...]
threshold_list = []  # [0.7, 0.8, 0.9, ...] - Individual threshold for each ROI
part_number = ""
default_threshold = 0.7
inspection_busy = False
total_count = 0
ok_count = 0
ng_count = 0
selected_roi_index = -1  # For selecting which ROI to set threshold

save_path = r"C:\Users\WORK STATION\Desktop\VISION SYSTEM\vision_parts"
os.makedirs(save_path, exist_ok=True)

last_plc_read = 0

# Functions
def update():
    global frame, last_plc_read
    ret, frame = cap.read()
    if ret:
        display = frame.copy()
        # Draw ROI rectangles with numbers
        for i, roi in enumerate(roi_list):
            x,y,w,h = roi
            color = (0,255,0) if i != selected_roi_index else (255,0,255)  # Magenta for selected
            cv2.rectangle(display, (x,y), (x+w,y+h), color, 2)
            # Draw ROI number
            cv2.putText(display, f"ROI-{i+1}", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            # Draw threshold value
            thresh = threshold_list[i] if i < len(threshold_list) else default_threshold
            cv2.putText(display, f"T:{thresh:.2f}", (x, y+h+20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        img = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(img)
        label.configure(image=imgtk)
        label.image = imgtk

    now = time.time()
    if PLC_CONNECTED and now - last_plc_read > 0.05:
        plc_check()
        last_plc_read = now

    app.after(10, update)

def plc_check():
    global inspection_busy, part_number
    if not PLC_CONNECTED or inspection_busy:
        return
    try:
        data = plc.read_holding_registers(PLC_REGS['CHECK'], 1)
        if data and data.registers[0] == 1:
            check_part()
            plc.write_register(PLC_REGS['CHECK'], 0)

        data = plc.read_holding_registers(PLC_REGS['PART_NUM'], 1)
        if data:
            new_part = f"PART{data.registers[0]}"
            if new_part != part_number:
                part_number = new_part
                part_entry.delete(0, "end")
                part_entry.insert(0, part_number)
                current_part.configure(text=f"PART : {part_number}")
                load_part()

        data = plc.read_holding_registers(PLC_REGS['SAVE_MASTER'], 1)
        if data and data.registers[0] == 1:
            save_master()
            plc.write_register(PLC_REGS['SAVE_MASTER'], 0)
    except:
        pass

def capture():
    global capture_frame
    if frame is not None:
        capture_frame = frame.copy()
        status_label.configure(text="🟢 Image captured!")

def add_roi():
    global roi_list, master_list, threshold_list
    if capture_frame is None:
        messagebox.showwarning("Warning", "Capture first!")
        return
    roi = cv2.selectROI("Select ROI", capture_frame, False)
    x,y,w,h = roi
    if w > 0 and h > 0:
        roi_list.append((x,y,w,h))
        gray = cv2.cvtColor(capture_frame, cv2.COLOR_BGR2GRAY)
        master_list.append(gray[y:y+h, x:x+w])
        threshold_list.append(default_threshold)  # Default threshold for new ROI
        update_roi_listbox()  # Update listbox
        status_label.configure(text=f"🟢 ROI-{len(roi_list)} added | Threshold: {default_threshold}")
    cv2.destroyAllWindows()

def delete_roi():
    global roi_list, master_list, threshold_list, selected_roi_index
    if roi_list and selected_roi_index >= 0:
        # Delete selected ROI
        roi_list.pop(selected_roi_index)
        master_list.pop(selected_roi_index)
        threshold_list.pop(selected_roi_index)
        selected_roi_index = -1
        update_roi_listbox()
        status_label.configure(text=f"🟢 ROI deleted | Remaining: {len(roi_list)}")
    elif roi_list:
        # Delete last ROI if none selected
        roi_list.pop()
        master_list.pop()
        threshold_list.pop()
        update_roi_listbox()
        status_label.configure(text=f"🟢 ROI-{len(roi_list)+1} deleted | Remaining: {len(roi_list)}")

def select_roi_from_list(index):
    global selected_roi_index
    selected_roi_index = index
    # Update threshold entry to show selected ROI's threshold
    if 0 <= index < len(threshold_list):
        thresh_entry.delete(0, "end")
        thresh_entry.insert(0, str(threshold_list[index]))
    status_label.configure(text=f"🟢 Selected ROI-{index+1} | Threshold: {threshold_list[index]:.2f}")

def set_roi_threshold():
    global selected_roi_index
    if selected_roi_index < 0 or selected_roi_index >= len(threshold_list):
        messagebox.showwarning("Warning", "Select a ROI first!")
        return
    try:
        new_threshold = float(thresh_entry.get())
        threshold_list[selected_roi_index] = new_threshold
        status_label.configure(text=f"🟢 ROI-{selected_roi_index+1} Threshold: {new_threshold}")
    except:
        status_label.configure(text="🔴 Invalid threshold!")

def set_all_threshold():
    global default_threshold
    try:
        new_threshold = float(thresh_entry.get())
        default_threshold = new_threshold
        # Update all ROIs to this threshold
        for i in range(len(threshold_list)):
            threshold_list[i] = new_threshold
        status_label.configure(text=f"🟢 All ROIs Threshold: {new_threshold}")
    except:
        status_label.configure(text="🔴 Invalid threshold!")

def update_roi_listbox():
    # Clear and repopulate listbox
    roi_listbox.delete(0, "end")
    for i in range(len(roi_list)):
        thresh = threshold_list[i] if i < len(threshold_list) else default_threshold
        roi_listbox.insert("end", f"ROI-{i+1}: T={thresh:.2f}")

def set_part():
    global part_number
    part_number = part_entry.get().strip()
    if part_number:
        current_part.configure(text=f"PART : {part_number}")
        status_label.configure(text=f"🟢 Part: {part_number}")

def set_threshold():
    # This now sets default threshold
    global default_threshold
    try:
        default_threshold = float(thresh_entry.get())
        status_label.configure(text=f"🟢 Default Threshold: {default_threshold}")
    except:
        status_label.configure(text="🔴 Invalid threshold!")

def save_master():
    if not part_number or not master_list:
        messagebox.showwarning("Warning", "Set part & ROI first!")
        return
    # Save master images
    for i, m in enumerate(master_list):
        cv2.imwrite(f"{save_path}/{part_number}_roi{i}.jpg", m)
    # Save ROI data
    with open(f"{save_path}/{part_number}_roi_data.txt", "w") as f:
        for r in roi_list:
            f.write(f"{r[0]},{r[1]},{r[2]},{r[3]}\n")
    # Save individual thresholds
    with open(f"{save_path}/{part_number}_thresholds.txt", "w") as f:
        for t in threshold_list:
            f.write(f"{t}\n")
    status_label.configure(text=f"🟢 Master saved: {part_number} | ROIs: {len(roi_list)}")

def load_part():
    global roi_list, master_list, threshold_list, part_number
    if not part_number:
        return
    roi_list.clear()
    master_list.clear()
    threshold_list.clear()
    try:
        # Load ROI data
        with open(f"{save_path}/{part_number}_roi_data.txt") as f:
            for line in f:
                x,y,w,h = map(int, line.strip().split(","))
                roi_list.append((x,y,w,h))
        # Load master images
        for i in range(len(roi_list)):
            m = cv2.imread(f"{save_path}/{part_number}_roi{i}.jpg", 0)
            if m is not None:
                master_list.append(m)
        # Load individual thresholds
        try:
            with open(f"{save_path}/{part_number}_thresholds.txt") as f:
                for line in f:
                    threshold_list.append(float(line.strip()))
        except FileNotFoundError:
            # If no individual thresholds, use default for all
            threshold_list = [default_threshold] * len(roi_list)

        update_roi_listbox()
        status_label.configure(text=f"🟢 Loaded: {part_number} | ROIs: {len(roi_list)}")
    except FileNotFoundError:
        status_label.configure(text=f"⚠️ New part: {part_number}")

def check_part():
    global inspection_busy, total_count, ok_count, ng_count
    if inspection_busy:
        return
    inspection_busy = True

    if frame is None or not master_list:
        result_label.configure(text="ERROR", text_color="red")
        inspection_busy = False
        return

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    total_count += 1
    total_label.configure(text=f"TOTAL : {total_count}")

    # Check each ROI with its individual threshold
    for i, (roi, master) in enumerate(zip(roi_list, master_list)):
        x,y,w,h = roi
        crop = cv2.resize(gray[y:y+h, x:x+w], (master.shape[1], master.shape[0]))
        res = cv2.matchTemplate(crop, master, cv2.TM_CCOEFF_NORMED)
        _, val, _, _ = cv2.minMaxLoc(res)

        # Use individual threshold for this ROI
        roi_threshold = threshold_list[i] if i < len(threshold_list) else default_threshold

        if val < roi_threshold:
            # NG - Show which ROI failed
            result_label.configure(text=f"NG-{i+1}", text_color="#e74c3c")
            ng_count += 1
            ng_label.configure(text=f"NG : {ng_count}")
            if PLC_CONNECTED:
                try:
                    plc.write_register(PLC_REGS['OK'], 0)
                    plc.write_register(PLC_REGS['NG'], 1)
                except:
                    pass
            app.after(1000, reset_result)
            return

    # All ROIs passed
    result_label.configure(text="OK", text_color="#27ae60")
    ok_count += 1
    ok_label.configure(text=f"OK : {ok_count}")
    if PLC_CONNECTED:
        try:
            plc.write_register(PLC_REGS['OK'], 1)
            plc.write_register(PLC_REGS['NG'], 0)
        except:
            pass
    app.after(1000, reset_result)

def reset_result():
    global inspection_busy
    result_label.configure(text="WAIT", text_color="cyan")
    inspection_busy = False

def show_current():
    if part_number:
        roi_info = "\n".join([f"ROI-{i+1}: T={threshold_list[i]:.2f}" for i in range(len(roi_list))])
        messagebox.showinfo("Current", f"Part: {part_number}\nROIs: {len(roi_list)}\n{roi_info}")

def clear_all_roi():
    global roi_list, master_list, threshold_list, selected_roi_index
    roi_list.clear()
    master_list.clear()
    threshold_list.clear()
    selected_roi_index = -1
    update_roi_listbox()
    status_label.configure(text="🟢 All ROIs cleared")

# ==================== UI ====================
app = ctk.CTk()
app.geometry("1600x900")  # Wider for ROI list
app.title("🔍 Rovix Vision System ")
app.configure(fg_color="#2c3e50")

# MAIN CONTAINER
main_container = ctk.CTkFrame(app, fg_color="#2c3e50")
main_container.pack(fill="both", expand=True, padx=5, pady=5)

# LEFT: Control Panel
left_panel = ctk.CTkFrame(main_container, fg_color="black", width=400, border_width=2, border_color="#34495e")
left_panel.pack(side="left", fill="y", padx=(5,0), pady=5)
left_panel.pack_propagate(False)

# CENTER: Camera
center_frame = ctk.CTkFrame(main_container, fg_color="black")
center_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

# WAIT indicator
wait_frame = ctk.CTkFrame(center_frame, fg_color="#1a1a1a", border_width=3, border_color="#34495e", height=100)
wait_frame.pack(fill="x", pady=(0, 5))
wait_frame.pack_propagate(False)

result_label = ctk.CTkLabel(wait_frame, text="WAIT", font=("Arial", 50, "bold"), text_color="cyan")
result_label.place(relx=0.5, rely=0.5, anchor="center")

# Camera frame
camera_frame = ctk.CTkFrame(center_frame, fg_color="black", border_width=3)
camera_frame.pack(fill="both", expand=True)

label = ctk.CTkLabel(camera_frame, text="", font=("Arial", 28, "bold"), text_color="white")
label.pack(fill="both", expand=True)

# Counter
counter_frame = ctk.CTkFrame(camera_frame, fg_color="#2c3e50", border_width=2)
counter_frame.place(relx=0.5, rely=0.95, anchor="center")

total_label = ctk.CTkLabel(counter_frame, text="TOTAL : 0", font=("Arial", 16, "bold"))
total_label.pack(side="left", padx=20, pady=5)

ok_label = ctk.CTkLabel(counter_frame, text="OK : 0", font=("Arial", 16, "bold"), text_color="#27ae60")
ok_label.pack(side="left", padx=20, pady=5)

ng_label = ctk.CTkLabel(counter_frame, text="NG : 0", font=("Arial", 16, "bold"), text_color="#e74c3c")
ng_label.pack(side="left", padx=20, pady=5)

# RIGHT: Result & ROI List
right_panel = ctk.CTkFrame(main_container, fg_color="black", width=400, border_width=2, border_color="#34495e")
right_panel.pack(side="right", fill="y", padx=(0,5), pady=5)
right_panel.pack_propagate(False)

# ==================== RIGHT PANEL ====================

# Title
ctk.CTkLabel(right_panel, text="✅ RESULT & CHECK", font=("Arial", 18, "bold"), text_color="white").pack(pady=(10,5))

# RESULT FRAME
result_frame = ctk.CTkFrame(right_panel, fg_color="#34495e", border_width=1)
result_frame.pack(pady=5, padx=10, fill="x")

ctk.CTkLabel(result_frame, text="📊 RESULT STATUS", font=("Arial", 12, "bold")).pack(pady=(5,0))

btn_row = ctk.CTkFrame(result_frame, fg_color="#34495e")
btn_row.pack(pady=5)
ctk.CTkButton(btn_row, text="OK", width=100, height=40, fg_color="#27ae60", 
              font=("Arial", 16, "bold"), command=lambda: result_label.configure(text="OK", text_color="#27ae60")).pack(side="left", padx=5)
ctk.CTkButton(btn_row, text="NG", width=100, height=40, fg_color="#c0392b", 
              font=("Arial", 16, "bold"), command=lambda: result_label.configure(text="NG", text_color="#e74c3c")).pack(side="left", padx=5)

# CHECK BUTTON
check_frame = ctk.CTkFrame(right_panel, fg_color="#34495e", border_width=1)
check_frame.pack(pady=5, padx=10, fill="x")

ctk.CTkLabel(check_frame, text="🔍 INSPECTION", font=("Arial", 12, "bold")).pack(pady=(5,0))

ctk.CTkButton(check_frame, text="🔍 CHECK", width=280, height=60, fg_color="#f39c12", 
              text_color="black", font=("Arial", 20, "bold"), command=check_part).pack(pady=10)

# ROI LIST BOX
roi_list_frame = ctk.CTkFrame(right_panel, fg_color="#34495e", border_width=1)
roi_list_frame.pack(pady=5, padx=10, fill="both", expand=True)

ctk.CTkLabel(roi_list_frame, text="📋 ROI LIST (Select to edit)", font=("Arial", 12, "bold")).pack(pady=(5,0))

# ROI Listbox with scrollbar
roi_listbox_frame = ctk.CTkFrame(roi_list_frame, fg_color="#2c3e50")
roi_listbox_frame.pack(pady=5, padx=5, fill="both", expand=True)

from tkinter import Listbox, Scrollbar, SINGLE

# Use tkinter Listbox for better selection
listbox_container = ctk.CTkFrame(roi_listbox_frame, fg_color="#2c3e50")
listbox_container.pack(fill="both", expand=True)

roi_listbox = Listbox(listbox_container, bg="#2c3e50", fg="white", font=("Arial", 12),
                      selectmode=SINGLE, height=8)
roi_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)

scrollbar = Scrollbar(listbox_container, orient="vertical", command=roi_listbox.yview)
scrollbar.pack(side="right", fill="y")
roi_listbox.config(yscrollcommand=scrollbar.set)

def on_roi_select(event):
    selection = roi_listbox.curselection()
    if selection:
        select_roi_from_list(selection[0])

roi_listbox.bind('<<ListboxSelect>>', on_roi_select)

# ROI Control buttons
roi_btn_frame = ctk.CTkFrame(roi_list_frame, fg_color="#34495e")
roi_btn_frame.pack(pady=5, fill="x")

ctk.CTkButton(roi_btn_frame, text="🗑️ Delete", width=90, height=30, fg_color="#e74c3c",
              command=delete_roi).pack(side="left", padx=2)
ctk.CTkButton(roi_btn_frame, text="🗑️ Clear All", width=90, height=30, fg_color="#c0392b",
              command=clear_all_roi).pack(side="left", padx=2)

# ==================== LEFT PANEL CONTROLS ====================

# Title
ctk.CTkLabel(left_panel, text="🔧 CONTROLS", font=("Arial", 18, "bold"), text_color="white").pack(pady=(5,5))

# PART NUMBER
part_frame = ctk.CTkFrame(left_panel, fg_color="#34495e", border_width=1)
part_frame.pack(pady=5, padx=5, fill="x")

ctk.CTkLabel(part_frame, text="🔢 PART NUMBER", font=("Arial", 12, "bold")).pack(pady=(5,0))
part_entry = ctk.CTkEntry(part_frame, placeholder_text="Enter part", width=200, height=35)
part_entry.pack(pady=5)
ctk.CTkButton(part_frame, text="SET PART", width=200, height=35, fg_color="#7ed321", 
              font=("Arial", 12, "bold"), command=set_part).pack(pady=5)

current_part = ctk.CTkLabel(part_frame, text="PART : NONE", font=("Arial", 14, "bold"), text_color="#f39c12")
current_part.pack(pady=5)

# THRESHOLD - Now for individual ROI
thresh_frame = ctk.CTkFrame(left_panel, fg_color="#34495e", border_width=1)
thresh_frame.pack(pady=5, padx=5, fill="x")

ctk.CTkLabel(thresh_frame, text="🎯 THRESHOLD CONTROL", font=("Arial", 12, "bold")).pack(pady=(5,0))

# Show selected ROI info
selected_roi_label = ctk.CTkLabel(thresh_frame, text="No ROI selected", font=("Arial", 11), text_color="#f39c12")
selected_roi_label.pack(pady=2)

thresh_entry = ctk.CTkEntry(thresh_frame, width=200, height=35)
thresh_entry.insert(0, "0.7")
thresh_entry.pack(pady=5)

btn_frame_thresh = ctk.CTkFrame(thresh_frame, fg_color="#34495e")
btn_frame_thresh.pack(pady=5)

ctk.CTkButton(btn_frame_thresh, text="Set for ROI", width=95, height=30, fg_color="#3498db",
              command=set_roi_threshold).pack(side="left", padx=2)
ctk.CTkButton(btn_frame_thresh, text="Set All", width=95, height=30, fg_color="#9b59b6",
              command=set_all_threshold).pack(side="left", padx=2)

# IMAGE OPERATIONS
img_frame = ctk.CTkFrame(left_panel, fg_color="#34495e", border_width=1)
img_frame.pack(pady=5, padx=5, fill="x")

ctk.CTkLabel(img_frame, text="📸 IMAGE OPERATIONS", font=("Arial", 12, "bold")).pack(pady=(5,0))

btn_row1 = ctk.CTkFrame(img_frame, fg_color="#34495e")
btn_row1.pack(pady=5)
ctk.CTkButton(btn_row1, text="CAPTURE", width=95, height=40, fg_color="#17a2b8", 
              command=capture).pack(side="left", padx=2)
ctk.CTkButton(btn_row1, text="ADD ROI", width=95, height=40, fg_color="#95a5a6", 
              text_color="black", command=add_roi).pack(side="left", padx=2)

# MASTER OPERATIONS
master_frame = ctk.CTkFrame(left_panel, fg_color="#34495e", border_width=1)
master_frame.pack(pady=5, padx=5, fill="x")

ctk.CTkLabel(master_frame, text="💾 MASTER OPERATIONS", font=("Arial", 12, "bold")).pack(pady=(5,0))

btn_row2 = ctk.CTkFrame(master_frame, fg_color="#34495e")
btn_row2.pack(pady=5)
ctk.CTkButton(btn_row2, text="SAVE", width=95, height=40, fg_color="#8e44ad", 
              command=save_master).pack(side="left", padx=2)
ctk.CTkButton(btn_row2, text="LOAD", width=95, height=40, fg_color="#3498db", 
              command=load_part).pack(side="left", padx=2)

ctk.CTkButton(master_frame, text="CURRENT PART INFO", width=200, height=40, fg_color="#e67e22", 
              font=("Arial", 12, "bold"), command=show_current).pack(pady=5)

# Status Bar
plc_status = "Connected" if PLC_CONNECTED else "Disconnected"
status_label = ctk.CTkLabel(app, text=f"🟢 Ready | PLC: {plc_status} | Path: {save_path}", 
                              font=("Arial", 11), text_color="#2ecc71", fg_color="#2c3e50")
status_label.pack(fill="x", padx=10, pady=(0,5))

update()
app.mainloop()