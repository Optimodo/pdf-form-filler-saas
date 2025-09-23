"""
PDF Processing Service - Web adaptation of the proven desktop PDF processing logic.

CRITICAL: This preserves the exact workflow from the desktop app to maintain
compatibility with different PDF viewers and editors. The order of operations
has been carefully refined and must not be changed.
"""
import os
import fitz  # PyMuPDF
import csv
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path


def clean_value(value: Any) -> str:
    """
    Clean and convert value to appropriate string format.
    
    CRITICAL: This function is identical to the desktop version.
    Preserves exact data formatting that ensures PDF compatibility.
    """
    if value is None:
        return ""
    # Convert to string and strip whitespace
    value = str(value).strip()
    # Handle decimal numbers (remove trailing .0 if present)
    if value.endswith('.0'):
        value = value[:-2]
    return value


class PDFProcessor:
    """
    PDF Form Filler processor that maintains the exact workflow
    from the desktop application for maximum compatibility.
    """
    
    def __init__(self, template_path: str, output_dir: Optional[str] = None):
        """
        Initialize PDF processor.
        
        Args:
            template_path: Path to the PDF template file
            output_dir: Optional custom output directory
        """
        self.template_path = template_path
        self.output_dir = output_dir
        
        # Validate template exists
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found: {template_path}")
    
    def process_single_pdf(self, row_data: Dict[str, Any], output_filename: str) -> bool:
        """
        Process a single PDF with the given row data.
        
        CRITICAL: This method preserves the EXACT workflow from the desktop app.
        The order of operations is crucial for PDF compatibility.
        
        Args:
            row_data: Dictionary of field names to values
            output_filename: Name for the output file
            
        Returns:
            bool: True if successful, False otherwise
        """
        doc = None
        new_doc = None
        
        try:
            # Step 1: Open the PDF (identical to desktop)
            doc = fitz.open(self.template_path)
            plot_ref = clean_value(row_data.get('PlotNo', 'Unknown'))
            logging.info(f"Processing PDF for Plot {plot_ref}")
            logging.debug(f"Output file: {output_filename}")
            
            # Step 2: Get all widgets from all pages and filter for fields in our CSV
            # CRITICAL: This two-step process (collect all, then filter) is important
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
            
            # Step 3: First pass - collect all field updates
            # CRITICAL: Two-pass approach prevents conflicts during field updates
            fields_processed = set()
            field_updates = []  # Store updates to apply them all at once
            
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
            
            # Step 4: Create a new PDF document
            # CRITICAL: Always work on a copy, never modify the original
            new_doc = fitz.open()
            new_doc.insert_pdf(doc)  # Copy all pages from original
            
            # Step 5: Second pass - apply all updates to the new document
            # CRITICAL: This approach ensures field updates don't interfere with each other
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
            
            # Step 6: Save the new document with EXACT parameters
            # CRITICAL: These save parameters were refined for maximum compatibility
            if self.output_dir:
                output_dir = self.output_dir
            else:
                output_dir = os.path.join(os.path.dirname(self.template_path), "output")
            
            output_path = os.path.join(output_dir, output_filename)
            logging.info(f"Saving PDF: {output_filename}")
            
            try:
                os.makedirs(output_dir, exist_ok=True)  # Ensure output directory exists
                
                # CRITICAL: These exact save parameters are essential for compatibility
                new_doc.save(
                    output_path,
                    garbage=0,      # Don't garbage collect to preserve structure
                    deflate=True,   # Compress for smaller files
                    clean=False,    # Don't clean to preserve structure
                    pretty=False    # Don't prettify to preserve structure
                )
                logging.debug("File saved successfully")
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
            # CRITICAL: Always close documents to prevent memory leaks
            if new_doc:
                try:
                    new_doc.close()
                except:
                    pass
            if doc:
                try:
                    doc.close()
                except:
                    pass
    
    def process_csv_batch(self, csv_path: str) -> Tuple[int, int, List[str]]:
        """
        Process a batch of PDFs from CSV data.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            Tuple of (successful_count, total_count, error_messages)
        """
        try:
            # Read CSV file with UTF-8-sig encoding to handle BOM
            with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
                rows = list(csv.DictReader(csvfile))
                
                # Clean up field names to remove any BOM characters
                # CRITICAL: This BOM handling was added to fix encoding issues
                if rows:
                    cleaned_fieldnames = [name.replace('\ufeff', '') for name in rows[0].keys()]
                    rows = [{cleaned_fieldnames[i]: row[orig_name] 
                            for i, orig_name in enumerate(row.keys())}
                           for row in rows]
                
                total_rows = len(rows)
                successful = 0
                errors = []
                
                for i, row in enumerate(rows, 1):
                    try:
                        # Extract filename and remove from data
                        output_filename = row.pop('Filename')
                        
                        if self.process_single_pdf(row, output_filename):
                            successful += 1
                            logging.info(f"Completed PDF {i} of {total_rows}: {output_filename}")
                        else:
                            error_msg = f"Failed to process PDF {i}: {output_filename}"
                            errors.append(error_msg)
                            logging.error(error_msg)
                            
                    except Exception as e:
                        error_msg = f"Error processing row {i}: {str(e)}"
                        errors.append(error_msg)
                        logging.error(error_msg)
                
                return successful, total_rows, errors
                
        except Exception as e:
            error_msg = f"Error reading CSV file: {str(e)}"
            logging.error(error_msg)
            return 0, 0, [error_msg]


def process_pdf_batch(template_path: str, csv_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to process a batch of PDFs.
    
    Args:
        template_path: Path to PDF template
        csv_path: Path to CSV data file
        output_dir: Optional output directory
        
    Returns:
        Dictionary with processing results
    """
    try:
        processor = PDFProcessor(template_path, output_dir)
        successful, total, errors = processor.process_csv_batch(csv_path)
        
        return {
            "success": True,
            "successful_count": successful,
            "total_count": total,
            "errors": errors,
            "message": f"Successfully processed {successful} of {total} PDFs"
        }
        
    except Exception as e:
        return {
            "success": False,
            "successful_count": 0,
            "total_count": 0,
            "errors": [str(e)],
            "message": f"Failed to process PDFs: {str(e)}"
        }

