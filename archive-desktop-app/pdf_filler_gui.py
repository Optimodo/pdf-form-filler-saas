import sys
import os
import fitz  # PyMuPDF
import csv
import logging
from datetime import datetime
import shutil
import webbrowser
from urllib.parse import quote
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, 
                             QVBoxLayout, QWidget, QFileDialog, QProgressBar,
                             QMessageBox, QHBoxLayout)
from PySide6.QtCore import Qt, QThread, Signal, QPoint
from PySide6.QtGui import QPixmap, QIcon
import win32event
import win32api
import winerror
import win32gui
import win32con

# Version information
VERSION = "1.0.0"

def normalize_path(path):
    """Normalize path separators for display."""
    return path.replace('/', os.path.sep).replace('\\', os.path.sep)

def get_application_path():
    """Get the path of the executable or script."""
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle (exe)
        return os.path.dirname(sys.executable)
    else:
        # If the application is run from a Python interpreter
        return os.path.dirname(os.path.abspath(__file__))

def get_icon_path():
    """Get the path to the icon file, whether running as script or executable."""
    if getattr(sys, 'frozen', False):
        # If running as executable
        return os.path.join(sys._MEIPASS, 'icon.png')
    else:
        # If running as script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.png')

def clean_value(value):
    """Clean and convert value to appropriate string format."""
    if value is None:
        return ""
    # Convert to string and strip whitespace
    value = str(value).strip()
    # Handle decimal numbers (remove trailing .0 if present)
    if value.endswith('.0'):
        value = value[:-2]
    return value

class PDFProcessorThread(QThread):
    """Worker thread for processing PDFs without blocking the GUI."""
    progress = Signal(int)  # Signal for progress updates
    status = Signal(str)    # Signal for status messages
    finished = Signal(bool, str, str)  # Success flag, message, and log file path
    
    def __init__(self, template_path, csv_path, output_path=None):
        super().__init__()
        self.template_path = template_path
        self.csv_path = csv_path
        self.output_path = output_path
        self.log_file = None

    def process_pdf(self, row_data, output_filename):
        """Process a single PDF with the given row data."""
        doc = None
        try:
            # Open the PDF
            doc = fitz.open(self.template_path)
            plot_ref = clean_value(row_data.get('PlotNo', 'Unknown'))
            logging.info(f"Processing PDF for Plot {plot_ref}")
            logging.debug(f"Output file: {output_filename}")
            
            # Get all widgets from all pages and filter for fields in our CSV
            all_widgets = []
            widget_page_map = {}  # Keep track of which page each widget is on
            for page_num in range(len(doc)):
                page_widgets = list(doc[page_num].widgets())
                for widget in page_widgets:
                    all_widgets.append(widget)
                    widget_page_map[widget.field_name] = page_num
            
            target_widgets = [w for w in all_widgets if w.field_name in row_data.keys()]
            
            logging.debug(f"Found {len(target_widgets)} matching fields out of {len(all_widgets)} total fields across {len(doc)} pages")
            
            if not target_widgets:
                logging.warning("No matching fields were found in the PDF!")
                return False
            
            fields_processed = set()
            field_updates = []  # Store updates to apply them all at once
            
            # First pass: collect all field updates
            for widget in target_widgets:
                try:
                    field_name = widget.field_name
                    new_value = clean_value(row_data.get(field_name, ''))
                    logging.debug(f"Setting {field_name} = {new_value} on page {widget_page_map[field_name] + 1}")
                    field_updates.append((field_name, new_value, widget_page_map[field_name]))
                    fields_processed.add(field_name)
                except Exception as e:
                    logging.error(f"Error processing field {field_name}: {e}")
                    continue
            
            # Report on any fields we couldn't find
            missing_fields = set(row_data.keys()) - fields_processed - {'Filename'}
            if missing_fields:
                logging.warning(f"Could not find these fields: {missing_fields}")
            
            # Create a new PDF document
            new_doc = fitz.open()
            new_doc.insert_pdf(doc)  # Copy all pages from original
            
            # Second pass: apply all updates to the new document
            for field_name, new_value, page_num in field_updates:
                try:
                    # Get widgets for the specific page
                    page = new_doc[page_num]
                    page_widgets = list(page.widgets())
                    # Find the matching widget on this page
                    for widget in page_widgets:
                        if widget.field_name == field_name:
                            widget.field_value = new_value
                            widget.update()
                            break
                    else:
                        logging.warning(f"Could not find field {field_name} on page {page_num + 1}")
                except Exception as e:
                    logging.error(f"Error updating field {field_name} on page {page_num + 1}: {e}")
            
            # Save the new document
            if self.output_path:
                output_dir = self.output_path
            else:
                output_dir = os.path.join(os.path.dirname(self.template_path), "output")
            
            output_path = os.path.join(output_dir, output_filename)
            logging.info(f"Saving PDF: {output_filename}")
            try:
                os.makedirs(output_dir, exist_ok=True)  # Ensure output directory exists
                new_doc.save(
                    output_path,
                    garbage=0,
                    deflate=True,
                    clean=False,
                    pretty=False
                )
                logging.debug("File saved successfully")
                new_doc.close()
                return True
                
            except Exception as save_error:
                logging.error(f"Save failed: {save_error}")
                raise
            
        except Exception as e:
            logging.error(f"Error processing PDF: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return False
        
        finally:
            # Always close the documents
            if doc:
                try:
                    doc.close()
                except:
                    pass

    def run(self):
        try:
            # Create output and logs directories relative to the application path
            app_path = get_application_path()
            template_dir = os.path.dirname(self.template_path)
            output_dir = os.path.join(template_dir, "output") if not self.output_path else self.output_path
            logs_dir = os.path.join(app_path, "logs")
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(logs_dir, exist_ok=True)
            
            # Reset logging configuration
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
            
            # Setup logging with a unique timestamp for each run
            timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M')
            self.log_file = os.path.join(logs_dir, f'pdf_processing_{timestamp}.log')
            
            # Configure logging to create a new file each time
            logging.basicConfig(
                filename=self.log_file,
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%d-%m-%Y %H:%M:%S',
                filemode='w'  # Use 'w' mode to create a new file each time
            )
            
            # Log the start of processing
            logging.info(f"Starting PDF processing at {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
            logging.info(f"Template: {self.template_path}")
            logging.info(f"CSV: {self.csv_path}")
            logging.info(f"Output directory: {output_dir}")
            
            # Read CSV file
            with open(self.csv_path, 'r', encoding='utf-8-sig') as csvfile:
                rows = list(csv.DictReader(csvfile))
                
                # Clean up field names to remove any BOM characters
                if rows:
                    cleaned_fieldnames = [name.replace('\ufeff', '') for name in rows[0].keys()]
                    rows = [{cleaned_fieldnames[i]: row[orig_name] 
                            for i, orig_name in enumerate(row.keys())}
                           for row in rows]
                
                total_rows = len(rows)
                self.status.emit(f"Processing {total_rows} PDFs...")
                
                successful = 0
                for i, row in enumerate(rows, 1):
                    output_filename = row.pop('Filename')
                    if self.process_pdf(row, output_filename):
                        successful += 1
                        self.status.emit(f"Completed PDF {i} of {total_rows}")
                    else:
                        self.status.emit(f"Failed to process PDF {i}")
                    
                    # Update progress
                    progress = int((i / total_rows) * 100)
                    self.progress.emit(progress)
            
            self.finished.emit(True, f"Successfully processed {successful} of {total_rows} PDFs", normalize_path(self.log_file))
            
        except Exception as e:
            logging.error(f"Error processing PDFs: {e}")
            self.finished.emit(False, f"Error: {str(e)}", normalize_path(self.log_file))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"PDF Form Filler v{VERSION}")
        
        # Set application icon
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QApplication.setWindowIcon(app_icon)
        
        # Calculate window size based on button width and padding
        button_width = 300  # 50% wider than before
        window_padding = 40  # 20px on each side
        window_width = button_width + window_padding
        self.setGeometry(100, 100, window_width, 500)  # Made slightly taller to accommodate new button
        
        # Remove window decorations and make window fixed size
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Center the window
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.center() - self.frameGeometry().center())

        # Create central widget and main vertical layout
        central_widget = QWidget()
        central_widget.setStyleSheet("""
            QWidget {
                background: #2C2C2C;
                border: 1px solid #3C3C3C;
                border-radius: 8px;
            }
        """)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Create title bar
        title_bar = QWidget()
        title_bar.setStyleSheet("QWidget { border: none; background: transparent; }")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)  # Add spacing between buttons
        
        # Add title label
        title_label = QLabel(f"PDF Form Filler v{VERSION}")
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                border: none;
                background: transparent;
            }
        """)
        
        # Common style for title bar buttons
        title_button_style = """
            QPushButton {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                width: 30px;
                height: 30px;
            }
            QPushButton:hover {
                background: #3C3C3C;
                border-radius: 15px;
            }
        """
        
        # Add minimize button
        minimize_btn = QPushButton("—")
        minimize_btn.setFixedSize(30, 30)
        minimize_btn.clicked.connect(self.showMinimized)
        minimize_btn.setStyleSheet(title_button_style)
        
        # Add close button
        close_btn = QPushButton("×")  # Using × symbol for close
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(title_button_style + """
            QPushButton:hover {
                background: #E81123;
                border-radius: 15px;
            }
        """)
        
        # Add widgets to title bar
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(minimize_btn)
        title_layout.addWidget(close_btn)
        
        # Add title bar to main layout
        main_layout.addWidget(title_bar)

        # Top section - Logo
        logo_label = QLabel()
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("QLabel { background: transparent; }")
            main_layout.addWidget(logo_label)
        else:
            logging.warning(f"Could not find icon at: {icon_path}")

        # Create form section widget
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(8)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_widget.setStyleSheet("QWidget { border: none; background: transparent; }")

        # Create buttons with consistent size
        self.template_btn = QPushButton("📄 Select PDF Template")
        self.csv_btn = QPushButton("📊 Select CSV File")
        self.output_btn = QPushButton("📁 Output Location (Optional)")
        self.process_btn = QPushButton("Process PDFs")
        self.template_btn.setFixedWidth(button_width)
        self.csv_btn.setFixedWidth(button_width)
        self.output_btn.setFixedWidth(button_width)
        self.process_btn.setFixedWidth(button_width)
        self.process_btn.setEnabled(False)

        # Style the file selection buttons to be prominent
        file_select_style = """
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """
        self.template_btn.setStyleSheet(file_select_style)
        self.csv_btn.setStyleSheet(file_select_style)
        
        # Style the output button differently to show it's optional
        output_style = """
            QPushButton {
                background-color: #424242;
                color: white;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                border: 1px solid #2196F3;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2196F3;
            }
            QPushButton:pressed {
                background-color: #1976D2;
            }
        """
        self.output_btn.setStyleSheet(output_style)

        # Style the process button
        self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #1B5E20;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #808080;
            }
        """)

        # Create labels for selected files with center alignment and improved style
        self.template_label = QLabel("No template selected")
        self.csv_label = QLabel("No CSV file selected")
        self.output_label = QLabel("Default: 'output' folder next to template")
        self.template_label.setAlignment(Qt.AlignCenter)
        self.csv_label.setAlignment(Qt.AlignCenter)
        self.output_label.setAlignment(Qt.AlignCenter)
        label_style = """
            QLabel {
                color: #CCCCCC;
                font-style: italic;
                background: transparent;
            }
        """
        self.template_label.setStyleSheet(label_style)
        self.csv_label.setStyleSheet(label_style)
        self.output_label.setStyleSheet(label_style)

        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(button_width)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 4px;
                text-align: center;
                background: #333333;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)

        # Create status label with center alignment
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("QLabel { color: #CCCCCC; background: transparent; }")

        # Create horizontal layout for log buttons
        log_layout = QHBoxLayout()
        log_layout.setAlignment(Qt.AlignCenter)
        
        # Style for log buttons
        log_button_style = """
            QPushButton {
                background-color: #404040;
                color: white;
                padding: 8px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #606060;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #808080;
            }
        """
        
        # Create open log directory button
        self.open_logs_btn = QPushButton("Open Log Directory")
        self.open_logs_btn.clicked.connect(self.open_log_directory)
        self.open_logs_btn.setEnabled(False)
        self.open_logs_btn.setStyleSheet(log_button_style)
        
        # Create view last log button
        self.view_log_btn = QPushButton("View Last Log")
        self.view_log_btn.clicked.connect(self.view_last_log)
        self.view_log_btn.setEnabled(False)
        self.view_log_btn.setStyleSheet(log_button_style)

        # Create feedback and about links
        bottom_links_layout = QHBoxLayout()
        bottom_links_layout.setContentsMargins(0, 0, 0, 0)
        
        # Style for links
        link_style = """
            QLabel {
                color: #2196F3;
                font-size: 11px;
                background: transparent;
            }
            QLabel:hover {
                color: #1976D2;
                text-decoration: underline;
            }
        """
        
        # Create About link
        self.about_link = QLabel("About")
        self.about_link.setStyleSheet(link_style)
        self.about_link.setCursor(Qt.PointingHandCursor)
        self.about_link.mousePressEvent = self.show_about
        
        # Create Feedback link
        self.feedback_link = QLabel("🐞 Feedback")
        self.feedback_link.setStyleSheet(link_style)
        self.feedback_link.setCursor(Qt.PointingHandCursor)
        self.feedback_link.mousePressEvent = lambda e: self.open_feedback_email()
        
        # Add links to layout
        bottom_links_layout.addWidget(self.about_link)
        bottom_links_layout.addStretch()
        bottom_links_layout.addWidget(self.feedback_link)

        # Add close button
        self.close_btn = QPushButton("Close")
        self.close_btn.setFixedWidth(button_width)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)

        # Add all widgets to form layout
        form_layout.addWidget(self.template_btn, 0, Qt.AlignCenter)
        form_layout.addWidget(self.template_label)
        form_layout.addWidget(self.csv_btn, 0, Qt.AlignCenter)
        form_layout.addWidget(self.csv_label)
        form_layout.addWidget(self.output_btn, 0, Qt.AlignCenter)
        form_layout.addWidget(self.output_label)
        form_layout.addWidget(self.process_btn, 0, Qt.AlignCenter)
        form_layout.addWidget(self.progress_bar, 0, Qt.AlignCenter)
        form_layout.addWidget(self.status_label)
        form_layout.addLayout(log_layout)
        form_layout.addWidget(self.close_btn, 0, Qt.AlignCenter)
        form_layout.addLayout(bottom_links_layout)  # Add the links layout

        # Add form widget to main layout
        main_layout.addWidget(form_widget)

        # Connect signals
        self.template_btn.clicked.connect(self.select_template)
        self.csv_btn.clicked.connect(self.select_csv)
        self.output_btn.clicked.connect(self.select_output)
        self.process_btn.clicked.connect(self.process_pdfs)
        self.close_btn.clicked.connect(self.close)

        self.template_path = None
        self.csv_path = None
        self.output_path = None
        self.last_log_file = None

    def select_template(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF Template", "", "PDF Files (*.pdf)")
        if file_path:
            self.template_path = file_path
            self.template_label.setText(f"Selected: {os.path.basename(file_path)}")
            self.check_process_ready()
            
            # Enable open logs button if logs directory exists
            logs_dir = os.path.join(os.path.dirname(file_path), "logs")
            self.open_logs_btn.setEnabled(os.path.exists(logs_dir))

    def select_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.csv_path = file_path
            self.csv_label.setText(f"Selected: {os.path.basename(file_path)}")
            self.check_process_ready()

    def select_output(self):
        """Select custom output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if dir_path:
            self.output_path = dir_path
            self.output_label.setText(f"Selected: {os.path.basename(dir_path)}")
            self.output_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 10px;
                    border-radius: 4px;
                    font-weight: bold;
                    border: none;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)

    def check_process_ready(self):
        self.process_btn.setEnabled(
            bool(self.template_path and self.csv_path))

    def process_pdfs(self):
        self.progress_bar.setVisible(True)
        self.process_btn.setEnabled(False)
        self.template_btn.setEnabled(False)
        self.csv_btn.setEnabled(False)
        self.output_btn.setEnabled(False)

        # Create and start the processor thread
        self.processor = PDFProcessorThread(self.template_path, self.csv_path, self.output_path)
        self.processor.progress.connect(self.update_progress)
        self.processor.status.connect(self.update_status)
        self.processor.finished.connect(self.processing_finished)
        self.processor.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, message):
        self.status_label.setText(message)

    def processing_finished(self, success, message, log_file):
        self.process_btn.setEnabled(True)
        self.template_btn.setEnabled(True)
        self.csv_btn.setEnabled(True)
        self.output_btn.setEnabled(True)
        
        self.last_log_file = log_file
        self.view_log_btn.setEnabled(True)
        self.open_logs_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Success", 
                f"{message}\n\nLog file saved to:\n{normalize_path(log_file)}")
        else:
            QMessageBox.critical(self, "Error", 
                f"{message}\n\nCheck the log file for details:\n{normalize_path(log_file)}")
        
        self.status_label.setText(message)

    def open_log_directory(self):
        """Open the log directory."""
        logs_dir = os.path.join(get_application_path(), "logs")
        if os.path.exists(logs_dir):
            try:
                os.startfile(logs_dir)
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Could not open log directory: {str(e)}")
        else:
            QMessageBox.warning(self, "Warning", "Log directory not found.")

    def view_last_log(self):
        """View the last log file."""
        if self.last_log_file and os.path.exists(self.last_log_file):
            try:
                os.startfile(self.last_log_file)
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Could not open log file: {str(e)}")
        else:
            QMessageBox.warning(self, "Warning", "No log file available.")

    def open_feedback_email(self):
        """Open default email client with pre-filled feedback/bug report email."""
        email = "mike.mclean@malcolmbuildingservices.co.uk"
        subject = f"PDF Form Filler v{VERSION} Feedback/Bug Report"
        
        # Create mailto URL with encoded subject
        mailto_url = f"mailto:{email}?subject={quote(subject)}"
        
        try:
            webbrowser.open(mailto_url)
        except Exception as e:
            QMessageBox.warning(self, "Warning", 
                f"Could not open email client: {str(e)}\n\n"
                f"Please send your feedback to: {email}\n"
                f"Subject: {subject}")

    def show_about(self, event):
        """Show the About dialog."""
        about_text = (
            f"<h3 style='margin-bottom: 15px;'>PDF Form Filler v{VERSION}</h3>"
            "<p style='line-height: 1.6; margin-bottom: 5px;'>"
            "<b>Developer:</b> Mike McLean<br>"
            "<b>Company:</b> Malcolm Building Services<br>"
            f"<b>Email:</b> <a href='mailto:mike.mclean@malcolmbuildingservices.co.uk' "
            f"style='color: #2196F3; text-decoration: none;'>mike.mclean@malcolmbuildingservices.co.uk</a></p>"
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("About")
        msg.setText(about_text)
        
        # Set custom icon
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            msg.setIconPixmap(QPixmap(icon_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            msg.setIcon(QMessageBox.NoIcon)
        
        # Remove all existing buttons
        for button in msg.buttons():
            msg.removeButton(button)
        
        # Add centered OK button
        ok_button = msg.addButton("OK", QMessageBox.AcceptRole)
        
        # Style the dialog and button
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2C2C2C;
                min-width: 250px;
                max-width: 300px;
            }
            QMessageBox QLabel {
                color: #FFFFFF;
                padding: 10px;
                margin-bottom: 0px;
            }
            QMessageBox QLabel a {
                color: #2196F3;
                text-decoration: none;
            }
            QMessageBox QLabel a:hover {
                color: #1976D2;
                text-decoration: underline;
            }
            QMessageBox QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px 20px;
                border-radius: 4px;
                border: none;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #1976D2;
            }
            QMessageBox QWidget#qt_msgbox_buttonbox {
                background: transparent;
                margin-top: 0px;
                padding-top: 0px;
            }
        """)
        
        # Create a custom layout for the button
        button_box = msg.findChild(QWidget, "qt_msgbox_buttonbox")
        if button_box:
            # Create a new layout
            new_layout = QHBoxLayout()
            new_layout.setAlignment(Qt.AlignCenter)
            new_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
            new_layout.setSpacing(0)  # Remove spacing
            new_layout.addWidget(ok_button)
            
            # Clear the old layout and set the new one
            old_layout = button_box.layout()
            if old_layout:
                QWidget().setLayout(old_layout)  # Remove old layout
            button_box.setLayout(new_layout)
        
        # Use exec() instead of exec_()
        msg.exec()

    # Add mouse event handlers for window dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'drag_pos'):
            diff = event.globalPosition().toPoint() - self.drag_pos
            new_pos = self.pos() + QPoint(diff.x(), diff.y())
            self.move(new_pos)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if hasattr(self, 'drag_pos'):
            del self.drag_pos

def bring_to_front(window_title):
    """Find and activate the existing window."""
    try:
        # Find the window
        other_window = win32gui.FindWindow(None, window_title)
        if other_window:
            # If minimized, restore
            if win32gui.IsIconic(other_window):
                win32gui.ShowWindow(other_window, win32con.SW_RESTORE)
            # Bring to front
            win32gui.SetForegroundWindow(other_window)
            return True
    except:
        pass
    return False

def main():
    # Create a mutex for single instance
    mutex_name = "PDF_Form_Filler_Mutex_12345"
    mutex = win32event.CreateMutex(None, False, mutex_name)
    last_error = win32api.GetLastError()

    if last_error == winerror.ERROR_ALREADY_EXISTS:
        # Application already running
        if bring_to_front("PDF Form Filler"):
            # If we found and activated the window, exit
            sys.exit(0)
        else:
            # If we couldn't find the window (rare case), show an error
            QMessageBox.warning(None, "Warning", 
                "Another instance is already running but couldn't be found.\n"
                "Please close it manually if you can't see it.")
            sys.exit(1)

    # Continue with normal application startup
    app = QApplication(sys.argv)
    
    # Set application icon
    icon_path = get_icon_path()
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 