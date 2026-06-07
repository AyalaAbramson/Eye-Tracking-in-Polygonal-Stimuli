"""
GUI launcher for Center Bias Experiment.

Provides a simple interface to:
- Enter participant demographics (ID, age, gender)
- Select experiment part (A or B)
- Choose block range (full session or split into thirds)
- Launch the experiment
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess


class ExperimentLauncher:
    """Simple GUI launcher for the center bias experiment."""

    def __init__(self, root):
        self.root = root
        self.root.title("Center Bias Experiment - Launcher")
        self.root.geometry("500x600")
        self.root.resizable(False, False)

        # Get project root (parent of src directory)
        self.project_root = Path(__file__).parent.parent

        # Create GUI
        self._create_widgets()

        # Bind Enter key to launch
        self.root.bind('<Return>', lambda e: self.launch_experiment())

    def _create_widgets(self):
        """Create all GUI widgets."""

        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Center Bias Experiment",
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Participant Number
        row = 1
        ttk.Label(main_frame, text="Participant Number:", font=('Arial', 10)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.participant_num_var = tk.StringVar()
        self.participant_num_entry = ttk.Entry(
            main_frame, textvariable=self.participant_num_var, width=30
        )
        self.participant_num_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        self.participant_num_entry.focus()

        # Participant ID (optional)
        row += 1
        ttk.Label(main_frame, text="Participant ID (optional):", font=('Arial', 10)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.participant_id_var = tk.StringVar()
        participant_id_entry = ttk.Entry(
            main_frame, textvariable=self.participant_id_var, width=30
        )
        participant_id_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(
            main_frame,
            text="(e.g., student ID, code name)",
            font=('Arial', 8),
            foreground='gray'
        ).grid(row=row+1, column=1, sticky=tk.W)

        # Age
        row += 2
        ttk.Label(main_frame, text="Age:", font=('Arial', 10)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.age_var = tk.StringVar()
        age_entry = ttk.Entry(main_frame, textvariable=self.age_var, width=30)
        age_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)

        # Gender
        row += 1
        ttk.Label(main_frame, text="Gender:", font=('Arial', 10)).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.gender_var = tk.StringVar(value="Prefer not to say")
        gender_frame = ttk.Frame(main_frame)
        gender_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)

        genders = ["Male", "Female", "Non-binary", "Prefer not to say", "Other"]
        for gender in genders:
            ttk.Radiobutton(
                gender_frame, text=gender, variable=self.gender_var, value=gender
            ).pack(anchor=tk.W)

        # Separator
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20
        )

        # Experiment Part
        row += 1
        ttk.Label(main_frame, text="Experiment Part:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.part_var = tk.StringVar(value="A")
        part_frame = ttk.Frame(main_frame)
        part_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Radiobutton(part_frame, text="Part A", variable=self.part_var, value="A").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(part_frame, text="Part B", variable=self.part_var, value="B").pack(side=tk.LEFT, padx=10)

        # Block Range
        row += 1
        ttk.Label(main_frame, text="Block Range:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.block_range_var = tk.StringVar(value="all")
        block_frame = ttk.Frame(main_frame)
        block_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)

        block_options = [
            ("All blocks (1-9)", "all"),
            ("Blocks 1-3", "1-3"),
            ("Blocks 4-6", "4-6"),
            ("Blocks 7-9", "7-9")
        ]
        for text, value in block_options:
            ttk.Radiobutton(
                block_frame, text=text, variable=self.block_range_var, value=value
            ).pack(anchor=tk.W)

        # Info label
        row += 1
        info_text = (
            "Split the session into thirds if participant needs\n"
            "a longer break or bathroom break in the middle."
        )
        info_label = ttk.Label(
            main_frame,
            text=info_text,
            font=('Arial', 8),
            foreground='gray',
            justify=tk.LEFT
        )
        info_label.grid(row=row, column=0, columnspan=2, pady=(0, 10))

        # Separator
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20
        )

        # Launch button
        row += 1
        self.launch_button = ttk.Button(
            main_frame,
            text="Launch Experiment",
            command=self.launch_experiment,
            style='Accent.TButton'
        )
        self.launch_button.grid(row=row, column=0, columnspan=2, pady=10)

        # Status label
        row += 1
        self.status_label = ttk.Label(
            main_frame,
            text="",
            font=('Arial', 9),
            foreground='green'
        )
        self.status_label.grid(row=row, column=0, columnspan=2)

        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)

    def validate_inputs(self):
        """Validate user inputs."""
        errors = []

        # Participant number is required
        participant_num = self.participant_num_var.get().strip()
        if not participant_num:
            errors.append("Participant number is required")
        elif not participant_num.isdigit():
            errors.append("Participant number must contain only digits")

        # Age validation (optional but if provided must be valid)
        age = self.age_var.get().strip()
        if age:
            try:
                age_int = int(age)
                if age_int < 1 or age_int > 120:
                    errors.append("Age must be between 1 and 120")
            except ValueError:
                errors.append("Age must be a number")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False

        return True

    def get_participant_id(self):
        """Generate participant ID (P## format)."""
        participant_num = self.participant_num_var.get().strip()
        return f"P{int(participant_num):02d}"

    def save_demographics(self, participant_id):
        """Save participant demographics to file."""
        # Get demographics
        demographics = {
            'participant_number': self.participant_num_var.get().strip(),
            'participant_id': participant_id,
            'subject_id': self.participant_id_var.get().strip() or "N/A",
            'age': self.age_var.get().strip() or "N/A",
            'gender': self.gender_var.get(),
            'timestamp': datetime.now().isoformat()
        }

        # Create demographics directory if it doesn't exist
        demo_dir = self.project_root / 'data' / 'demographics'
        demo_dir.mkdir(parents=True, exist_ok=True)

        # Save to file (append mode to accumulate all participants)
        demo_file = demo_dir / 'participant_demographics.jsonl'
        with open(demo_file, 'a') as f:
            f.write(json.dumps(demographics) + '\n')

        print(f"Demographics saved to {demo_file}")
        return demographics

    def launch_experiment(self):
        """Launch the experiment with selected parameters."""
        # Validate inputs
        if not self.validate_inputs():
            return

        # Get parameters
        participant_id = self.get_participant_id()
        part = self.part_var.get()
        block_range = self.block_range_var.get()

        # Save demographics
        try:
            demographics = self.save_demographics(participant_id)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save demographics: {e}")
            return

        # Build command
        python_exe = sys.executable
        script_path = self.project_root / 'src' / 'experiment2_runner.py'

        cmd = [
            python_exe,
            str(script_path),
            '--participant-id', participant_id,
            '--part', part
        ]

        # Add block range if not "all"
        if block_range != "all":
            cmd.extend(['--blocks', block_range])

        # Show confirmation
        block_text = f"blocks {block_range}" if block_range != "all" else "all blocks (1-9)"
        confirm_msg = (
            f"Launch experiment with:\n\n"
            f"Participant: {participant_id}\n"
            f"Part: {part}\n"
            f"Blocks: {block_text}\n\n"
            f"Subject ID: {demographics['subject_id']}\n"
            f"Age: {demographics['age']}\n"
            f"Gender: {demographics['gender']}\n\n"
            f"Continue?"
        )

        if not messagebox.askyesno("Confirm Launch", confirm_msg):
            return

        # Update status
        self.status_label.config(text="Launching experiment...", foreground='blue')
        self.root.update()

        # Disable launch button
        self.launch_button.config(state='disabled')

        try:
            # Launch experiment as subprocess
            print(f"\nLaunching: {' '.join(cmd)}\n")
            process = subprocess.Popen(cmd, cwd=str(self.project_root))

            # Update status
            self.status_label.config(
                text=f"Experiment running (PID: {process.pid})",
                foreground='green'
            )

            # Close GUI after short delay
            self.root.after(2000, self.root.destroy)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch experiment:\n{e}")
            self.status_label.config(text="Launch failed", foreground='red')
            self.launch_button.config(state='normal')


def main():
    """Main entry point for the launcher GUI."""
    root = tk.Tk()

    # Set style
    style = ttk.Style()
    style.theme_use('clam')

    # Create launcher
    launcher = ExperimentLauncher(root)

    # Run
    root.mainloop()


if __name__ == '__main__':
    main()
