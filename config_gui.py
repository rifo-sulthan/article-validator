import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import threading
import config_generator

# Ensure correct working directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class ConfigGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Validation Config Generator")
        self.root.geometry("600x700")
        
        # Style
        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("TLabel", padding=6)

        # Header
        header_frame = ttk.Frame(root)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(header_frame, text="Generate Config from Description", font=("Segoe UI", 12, "bold")).pack()

        # Input Section
        input_frame = ttk.LabelFrame(root, text="Step 1: Describe your goal")
        input_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(input_frame, text="Example: 'Find articles about sustainable gardening tips'").pack(anchor="w", padx=5)
        
        self.prompt_entry = ttk.Entry(input_frame, width=50)
        self.prompt_entry.pack(fill="x", padx=10, pady=10)
        self.prompt_entry.bind("<Return>", lambda e: self.generate_config())

        # Action Buttons
        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        self.gen_btn = ttk.Button(btn_frame, text="Generate Configuration", command=self.generate_config)
        self.gen_btn.pack(side="left", padx=5)

        # Output Section
        output_frame = ttk.LabelFrame(root, text="Step 2: Review Generated Config")
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=20, font=("Consolas", 10))
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Save Section
        save_frame = ttk.Frame(root)
        save_frame.pack(fill="x", padx=10, pady=10)
        
        self.save_btn = ttk.Button(save_frame, text="Save to config.json", command=self.save_config, state="disabled")
        self.save_btn.pack(side="right", padx=5)
        
        self.status_lbl = ttk.Label(save_frame, text="Ready")
        self.status_lbl.pack(side="left", padx=5)

    def generate_config(self):
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            messagebox.showwarning("Input Required", "Please enter a description first.")
            return

        self.status_lbl.config(text="Generating... Please wait...", foreground="blue")
        self.gen_btn.config(state="disabled")
        self.output_text.delete(1.0, tk.END)
        
        # Run in thread to not freeze GUI
        threading.Thread(target=self._run_generation, args=(prompt,), daemon=True).start()

    def _run_generation(self, prompt):
        try:
            config = config_generator.generate_config_from_ai(prompt)
            
            # Update GUI from main thread
            self.root.after(0, self._display_result, config)
        except Exception as e:
            self.root.after(0, self._display_error, str(e))

    def _display_result(self, config):
        json_str = json.dumps(config, indent=4)
        self.output_text.insert(tk.END, json_str)
        
        # Merge basic parts if config is just partial updates (optional)
        # For now assume full replacement or manual edit
        
        self.status_lbl.config(text="Generation Complete", foreground="green")
        self.gen_btn.config(state="normal")
        self.save_btn.config(state="normal")

    def _display_error(self, error_msg):
        self.status_lbl.config(text="Error occurred", foreground="red")
        messagebox.showerror("Generation Error", error_msg)
        self.gen_btn.config(state="normal")

    def save_config(self):
        try:
            content = self.output_text.get(1.0, tk.END).strip()
            if not content: return

            new_config = json.loads(content)
            
            # Load existing config to preserve other fields (files, model path etc)
            config_path = "config.json"
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    full_config = json.load(f)
            else:
                full_config = {}

            # Update fields
            # We only want to update the semantic fields, not input/output paths ideally
            # unless the AI generated them.
            # config_generator outputs: candidate_labels, positive_labels, step1_prefilter
            
            # Update fields
            # Merge the new config into the existing one. 
            # This allows updating ANY field present in the GUI text box.
            full_config.update(new_config)

            with open(config_path, "w") as f:
                json.dump(full_config, f, indent=4)
            
            self.status_lbl.config(text="Saved to config.json!", foreground="green")
            messagebox.showinfo("Success", "Configuration updated successfully!")
            
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON. Please check the output text.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigGeneratorGUI(root)
    root.mainloop()
