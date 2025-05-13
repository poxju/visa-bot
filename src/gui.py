import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sv_ttk
import configparser
import subprocess
import psutil
import os
import sys

class VisaBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Visa Bot")
        self.root.geometry("380x750")  # Adjusted height to accommodate new input field
        self.root.resizable(False, False)
        if hasattr(sys, '_MEIPASS'):
            self.icon_path = os.path.join(sys._MEIPASS, 'src/icons/program_photo.png')
        else:
            self.icon_path = os.path.join(os.path.dirname(__file__), 'icons/program_photo.png')
        self.root.iconphoto(False, tk.PhotoImage(file=self.icon_path)) 
        self.create_widgets()
        sv_ttk.set_theme("dark")
        self.process = None
        self.is_running = False  # Add a flag to check if the process is running

    def create_widgets(self):
        self.label = ttk.Label(self.root, text="US VISA RESCHEDULER", font=("roboto", 16, "bold"))
        self.label.pack(pady=10)
        
        self.create_form()
        
        if hasattr(sys, '_MEIPASS'):
            start_icon_path = os.path.join(sys._MEIPASS, 'src/icons/start_icon.png')
            stop_icon_path = os.path.join(sys._MEIPASS, 'src/icons/stop_icon.png')
            restart_icon_path = os.path.join(sys._MEIPASS, 'src/icons/restart_icon.png')
        else:
            start_icon_path = os.path.join(os.path.dirname(__file__), 'icons/start_icon.png')
            stop_icon_path = os.path.join(os.path.dirname(__file__), 'icons/stop_icon.png')
            restart_icon_path = os.path.join(os.path.dirname(__file__), 'icons/restart_icon.png')

        self.start_icon = tk.PhotoImage(file=start_icon_path).subsample(2, 2)
        self.stop_icon = tk.PhotoImage(file=stop_icon_path).subsample(2, 2)
        self.restart_icon = tk.PhotoImage(file=restart_icon_path).subsample(2, 2)
        
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(pady=10)
        
        self.start_button = ttk.Button(self.button_frame, image=self.start_icon, command=self.check_entries_and_run_main)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(self.button_frame, image=self.stop_icon, command=self.stop_main, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        self.restart_button = ttk.Button(self.button_frame, image=self.restart_icon, command=self.restart_main, state=tk.DISABLED)
        self.restart_button.grid(row=0, column=2, padx=5)
        
        self.create_log_area()

    def create_form(self):
        form_frame = ttk.LabelFrame(self.root, text="Personal Information")
        form_frame.pack(pady=5, padx=10, fill="both", expand=False)
        
        self.prefill_var = tk.BooleanVar()
        self.prefill_checkbox = ttk.Checkbutton(form_frame, text="Fill with default info", variable=self.prefill_var, command=self.prefill_form)
        self.prefill_checkbox.grid(row=0, column=1, sticky=tk.E, pady=5, padx=5)
                
        ttk.Label(form_frame, text="Email").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.email_entry = ttk.Entry(form_frame)
        self.email_entry.grid(row=1, column=1, pady=5, padx=5, sticky=tk.EW)
        
        ttk.Label(form_frame, text="Password").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.password_entry = ttk.Entry(form_frame, show="*")
        self.password_entry.grid(row=2, column=1, pady=5, padx=5, sticky=tk.EW)
        
        ttk.Label(form_frame, text="Schedule ID").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        self.schedule_id_entry = ttk.Entry(form_frame)
        self.schedule_id_entry.grid(row=3, column=1, pady=5, padx=5, sticky=tk.EW)
        
        ttk.Label(form_frame, text="Country Code").grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        self.country_code_var = tk.StringVar()
        self.country_code_dropdown = ttk.Combobox(form_frame, textvariable=self.country_code_var, width=15)
        self.country_code_dropdown['values'] = ('en-tr', 'en-us', 'en-ca')
        self.country_code_dropdown.grid(row=4, column=1, pady=5, padx=5, sticky=tk.EW)
        
        ttk.Label(form_frame, text="Schedule Date \n(YYYY-MM-DD)").grid(row=5, column=0, sticky=tk.W, pady=5, padx=5)
        self.schedule_date_entry = ttk.Entry(form_frame)
        self.schedule_date_entry.grid(row=5, column=1, pady=5, padx=5, sticky=tk.EW)
        
        ttk.Label(form_frame, text="Facility ID").grid(row=6, column=0, sticky=tk.W, pady=5, padx=5)
        self.facility_id_entry = ttk.Entry(form_frame)
        self.facility_id_entry.grid(row=6, column=1, pady=5, padx=5, sticky=tk.EW)

        form_frame.columnconfigure(1, weight=1)

        # Create Bot Settings frame
        bot_settings_frame = ttk.LabelFrame(self.root, text="Bot Settings")
        bot_settings_frame.pack(pady=5, padx=10, fill="both", expand=False)

        self.watch_bot_var = tk.BooleanVar()
        self.watch_bot_checkbox = ttk.Checkbutton(bot_settings_frame, text="Watch Bot", variable=self.watch_bot_var, state=tk.DISABLED)
        self.watch_bot_checkbox.grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.watch_bot_var.trace_add("write", self.on_watch_bot_toggle)

        self.notifications_var = tk.BooleanVar()
        self.notifications_checkbox = ttk.Checkbutton(bot_settings_frame, text="Enable Notifications", variable=self.notifications_var)
        self.notifications_checkbox.grid(row=0, column=1, sticky=tk.E, pady=5, padx=5)

        ttk.Label(bot_settings_frame, text="Waiting Time \n(minutes)").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.waiting_time_var = tk.StringVar(value="8")  # Default to 8 minutes
        self.waiting_time_dropdown = ttk.Combobox(bot_settings_frame, textvariable=self.waiting_time_var, width=15)
        self.waiting_time_dropdown['values'] = [str(i) for i in range(1, 21)]  # 1 to 20 minutes
        self.waiting_time_dropdown.grid(row=1, column=1, pady=5, padx=5, sticky=tk.EW)

        ttk.Label(bot_settings_frame, text="Alert Email").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.alert_email_entry = ttk.Entry(bot_settings_frame)
        self.alert_email_entry.grid(row=2, column=1, pady=5, padx=5, sticky=tk.EW)

        self.prefill_alert_email_var = tk.BooleanVar()
        self.prefill_alert_email_checkbox = ttk.Checkbutton(bot_settings_frame, text="Default", variable=self.prefill_alert_email_var, command=self.prefill_alert_email)
        self.prefill_alert_email_checkbox.grid(row=2, column=2, sticky=tk.W, pady=5, padx=5)

        bot_settings_frame.columnconfigure(1, weight=1)

    def create_log_area(self):
        log_frame = ttk.LabelFrame(self.root, text="Logs")
        log_frame.pack(pady=5, padx=10, fill="both", expand=True)
        
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)  # Enable word wrapping
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_config("start", foreground="green")
        self.log_text.tag_config("stop", foreground="red")
        self.log_text.tag_config("main", foreground="yellow")  # New tag for main.py logs

    def log_message(self, message, tag=None):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def prefill_form(self):
        if self.prefill_var.get():
            config = configparser.ConfigParser()
            if hasattr(sys, '_MEIPASS'):
                config_path = os.path.join(sys._MEIPASS, 'src/defaultconfig.ini')
            else:
                config_path = os.path.join(os.path.dirname(__file__), 'defaultconfig.ini')
            config.read(config_path)
            self.clear_form()
            self.email_entry.insert(0, config['USVISA']['USERNAME'])
            self.password_entry.insert(0, config['USVISA']['PASSWORD'])
            self.schedule_id_entry.insert(0, config['USVISA']['SCHEDULE_ID'])
            self.country_code_var.set(config['USVISA']['COUNTRY_CODE'])
            self.schedule_date_entry.insert(0, config['USVISA']['MY_SCHEDULE_DATE'])
            self.facility_id_entry.insert(0, config['USVISA']['FACILITY_ID'])
            self.notifications_var.set(config['BOT_SETTINGS'].getboolean('notifications', fallback=False))
            self.waiting_time_var.set(str(config['BOT_SETTINGS'].getint('wait_time', fallback=8) // 60))  # Convert seconds to minutes
            self.watch_bot_var.set(config['BOT_SETTINGS'].getboolean('watch_bot', fallback=False))
        else:
            self.clear_form()

    def prefill_alert_email(self):
        if self.prefill_alert_email_var.get():
            config = configparser.ConfigParser()
            if hasattr(sys, '_MEIPASS'):
                config_path = os.path.join(sys._MEIPASS, 'src/defaultconfig.ini')
            else:
                config_path = os.path.join(os.path.dirname(__file__), 'defaultconfig.ini')
            config.read(config_path)
            self.alert_email_entry.delete(0, tk.END)
            alert_email = config['USVISA'].get('username', '')
            self.alert_email_entry.insert(0, alert_email)
        else:
            self.alert_email_entry.delete(0, tk.END)

    def clear_form(self):
        self.email_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.schedule_id_entry.delete(0, tk.END)
        self.schedule_date_entry.delete(0, tk.END)
        self.facility_id_entry.delete(0, tk.END)
        self.country_code_var.set('')  # Reset dropdown to empty/default
        self.alert_email_entry.delete(0, tk.END)

    def run_main(self):
        if self.is_running:
            self.log_message("Visa Bot is already running.", "main")
            return
        try:
            if not self.prefill_var.get():
                self.save_config()
            else:
                self.log_message("Using pre-filled values...", "start")
                self.save_config()
            self.log_message("Starting main.py...", "start")
            watch_bot = self.watch_bot_var.get()
            waiting_time = int(self.waiting_time_var.get()) * 60  # Convert minutes to seconds
            if hasattr(sys, '_MEIPASS'):
                main_path = os.path.join(sys._MEIPASS, "src/main.py")
            else:
                main_path = os.path.join(os.path.dirname(__file__), "main.py")
            self.process = subprocess.Popen(["python", main_path, str(watch_bot).lower(), str(waiting_time)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.is_running = True  # Set the flag to True when the process starts
            self.stop_button.config(state=tk.NORMAL)
            self.restart_button.config(state=tk.NORMAL)
            self.stop_button.state(["!disabled"])
            self.restart_button.state(["!disabled"])
            self.watch_bot_checkbox.config(state=tk.NORMAL)  # Enable the checkbox now that driver is running
            self.waiting_time_dropdown.config(state=tk.DISABLED)  # Disable the waiting time dropdown

            def read_output(pipe):
                for line in iter(pipe.readline, ''):
                    self.log_message(line.strip(), "main")
                pipe.close()

            from threading import Thread
            Thread(target=read_output, args=(self.process.stdout,)).start()
            Thread(target=read_output, args=(self.process.stderr,)).start()
        except Exception as e:
            self.log_message(f"Error: {e}", "stop")
            messagebox.showerror("Error", f"An error occurred: {e}")

    def save_config(self):
        config = configparser.ConfigParser()
        config['USVISA'] = {
            'USERNAME': self.email_entry.get(),
            'PASSWORD': self.password_entry.get(),
            'SCHEDULE_ID': self.schedule_id_entry.get(),
            'COUNTRY_CODE': self.country_code_var.get(),
            'MY_SCHEDULE_DATE': self.schedule_date_entry.get(),
            'FACILITY_ID': self.facility_id_entry.get()
        }
        config['BOT_SETTINGS'] = {
            'NOTIFICATIONS': str(self.notifications_var.get()),
            'WAIT_TIME': str(int(self.waiting_time_var.get()) * 60),  # Convert minutes to seconds
            'WATCH_BOT': str(self.watch_bot_var.get()),
            'ALERT_EMAIL': self.alert_email_entry.get()
        }
        config['CHROMEDRIVER'] = {
            'LOCAL_USE': "True",
            'HUB_ADDRESS': "http://localhost:9515/wd/hub"
        }
        if hasattr(sys, '_MEIPASS'):
            config_path = os.path.join(sys._MEIPASS, 'src/config.ini')
        else:
            config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        with open(config_path, 'w') as configfile:
            config.write(configfile)

    def stop_main(self):
        if self.process:
            parent = psutil.Process(self.process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            self.log_message("Stopped main.py", "stop")
            self.is_running = False  # Reset the flag when the process stops
            self.stop_button.config(state=tk.DISABLED)
            self.restart_button.config(state=tk.DISABLED)
            self.stop_button.state(["disabled"])
            self.restart_button.state(["disabled"])
            self.watch_bot_checkbox.config(state=tk.DISABLED)  # Disable the checkbox now that driver is stopped
            self.waiting_time_dropdown.config(state=tk.NORMAL)  # Enable the waiting time dropdown
            messagebox.showinfo("Process Stopped", "The process has been stopped successfully.")

    def restart_main(self):
        if messagebox.askyesno("Restart", "Are you sure you want to restart the process?"):
            self.stop_main()
            self.run_main()
            messagebox.showinfo("Process Restarted", "The process has been restarted successfully.")

    def check_entries(self):
        if not self.email_entry.get() or not self.password_entry.get() or not self.schedule_id_entry.get() or not self.country_code_var.get() or not self.schedule_date_entry.get() or not self.facility_id_entry.get() or not self.alert_email_entry.get():
            messagebox.showwarning("Warning", "All fields must be filled out.")
            return False
        return True

    def check_entries_and_run_main(self):
        if self.check_entries():
            self.run_main()

    def on_watch_bot_toggle(self, *args):
        config = configparser.ConfigParser()
        if hasattr(sys, '_MEIPASS'):
            config_path = os.path.join(sys._MEIPASS, 'src/config.ini')
        else:
            config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        config.read(config_path)
        config['BOT_SETTINGS']['WATCH_BOT'] = str(self.watch_bot_var.get())
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        self.log_message(f"Set WATCH_BOT to {self.watch_bot_var.get()}.", "main")
            
if __name__ == "__main__":
    root = tk.Tk()
    app = VisaBotGUI(root)
    root.mainloop()

