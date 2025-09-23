import fitz  # PyMuPDF
import os
import re
from typing import List, Dict, Any, Tuple
import shutil

# Version information
VERSION = "1.0.0"

# Define text alignment constants
TEXT_ALIGN_LEFT = 0
TEXT_ALIGN_CENTER = 1
TEXT_ALIGN_RIGHT = 2

def parse_field_selection(selection: str, max_field: int) -> List[int]:
    """Parse a field selection string like '1-5,7,9-11' into a list of field indices."""
    selected = set()
    # Split by comma and process each part
    for part in selection.strip().split(','):
        if '-' in part:
            # Handle ranges like '1-5'
            start, end = map(int, part.split('-'))
            selected.update(range(start, end + 1))
        else:
            # Handle single numbers
            selected.add(int(part))
    
    # Validate all numbers are in range
    if min(selected) < 1 or max(selected) > max_field:
        raise ValueError(f"Field selection must be between 1 and {max_field}")
    
    return sorted(list(selected))

def get_field_attributes(widget: fitz.Widget) -> Dict[str, Any]:
    """Get editable attributes of a form field."""
    # Get the field's font size from text_fontsize property
    try:
        font_size = widget.text_fontsize
    except AttributeError:
        font_size = 0  # Default if not available
    
    # Get field flags
    flags = widget.field_flags if hasattr(widget, 'field_flags') else 0
    
    return {
        'field_type': widget.field_type,
        'field_name': widget.field_name,
        'field_value': widget.field_value,
        'field_flags': flags,
        'font_size': font_size,
        'text_align': getattr(widget, 'text_align', 0),  # 0=left, 1=center, 2=right
        'is_multiline': bool(flags & 2**12),
        'do_not_scroll': bool(flags & 2**13),
        'do_not_spell_check': bool(flags & 2**22),
        'do_not_type': bool(flags & 2**1),
    }

def set_field_attributes(doc: fitz.Document, page_num: int, widget: fitz.Widget, attributes: Dict[str, Any]) -> None:
    """Apply attributes to a form field."""
    try:
        # Get the page and its widgets
        page = doc[page_num]
        widgets = page.widgets()
        
        # Find our widget in the page's widgets
        target_widget = None
        for w in widgets:
            if w.field_name == widget.field_name:
                target_widget = w
                break
        
        if not target_widget:
            print(f"Warning: Could not find widget {widget.field_name} on page {page_num + 1}")
            return
        
        # Store original flags
        flags = target_widget.field_flags if hasattr(target_widget, 'field_flags') else 0
        
        # Update text alignment if specified
        if 'text_align' in attributes and hasattr(target_widget, 'text_align'):
            target_widget.text_align = attributes['text_align']
        
        # Update font size if specified
        if 'font_size' in attributes:
            try:
                target_widget.text_fontsize = attributes['font_size']
            except AttributeError:
                print(f"Warning: Could not set font size for field {target_widget.field_name}")
        
        # Handle boolean flags
        flag_mappings = {
            'is_multiline': 2**12,
            'do_not_scroll': 2**13,
            'do_not_spell_check': 2**22,
            'do_not_type': 2**1
        }
        
        for attr, flag in flag_mappings.items():
            if attr in attributes:
                if attributes[attr]:
                    flags |= flag  # Set flag
                else:
                    flags &= ~flag  # Clear flag
        
        target_widget.field_flags = flags
        target_widget.update()
        
    except Exception as e:
        print(f"Warning: Failed to update widget {widget.field_name} on page {page_num + 1}: {str(e)}")

def display_fields(fields: List[Dict[str, Any]]) -> None:
    """Display numbered list of form fields with their attributes."""
    print("\nForm Fields:")
    print("-" * 80)
    for idx, field in enumerate(fields, 1):
        print(f"\n{idx}. Name: {field['field_name']}")
        print(f"   Type: {field['field_type']}")
        print(f"   Current Attributes:")
        print(f"   - Font Size: {field['font_size']}")
        print(f"   - Text Align: {['Left', 'Center', 'Right'][field['text_align']]}")
        print(f"   - Multiline: {field['is_multiline']}")
        print(f"   - Do Not Scroll: {field['do_not_scroll']}")
        print(f"   - Do Not Spell Check: {field['do_not_spell_check']}")
        print(f"   - Do Not Type: {field['do_not_type']}")

def get_attribute_changes() -> Dict[str, Any]:
    """Get attribute changes from user input."""
    changes = {}
    
    print("\nSelect attributes to modify (press Enter to skip):")
    
    # Font size
    size = input("Font size (e.g. 10): ").strip()
    if size:
        try:
            changes['font_size'] = float(size)
        except ValueError:
            print("Warning: Invalid font size, skipping...")
    
    # Text alignment
    print("\nText alignment options:")
    print("0 = Left")
    print("1 = Center")
    print("2 = Right")
    align = input("Select text alignment (0/1/2): ").strip()
    if align:
        try:
            align_val = int(align)
            if 0 <= align_val <= 2:
                changes['text_align'] = align_val
            else:
                print("Warning: Alignment must be 0, 1, or 2, skipping...")
        except ValueError:
            print("Warning: Invalid alignment value, skipping...")
    
    # Boolean flags - all questions standardized to "Enable X?"
    flags = [
        ('is_multiline', "multiline text"),
        ('do_not_scroll', "text scrolling"),
        ('do_not_spell_check', "spell checking"),
        ('do_not_type', "text input")
    ]
    
    print("\nFor each feature, type:")
    print("y = Enable")
    print("n = Disable")
    print("Enter = Skip (no change)")
    print("")
    
    for flag_name, description in flags:
        response = input(f"Enable {description}? (y/n/Enter to skip): ").strip().lower()
        if response in ('y', 'n'):
            # Invert the value for 'do_not_' flags to make the logic consistent
            if flag_name.startswith('do_not_'):
                changes[flag_name] = (response == 'n')
            else:
                changes[flag_name] = (response == 'y')
    
    return changes

def set_text_alignment(widget: fitz.Widget, align_value: int) -> None:
    """Set text alignment using field flags."""
    try:
        # Get current flags
        current_flags = widget.field_flags if hasattr(widget, 'field_flags') else 0
        
        # Clear existing alignment bits (bits 24-25)
        alignment_mask = ~(3 << 24)  # 3 = binary 11, to clear both bits
        flags = current_flags & alignment_mask
        
        # Set new alignment
        # Left = 0, Center = 1, Right = 2
        # These need to be shifted to bits 24-25
        flags |= (align_value << 24)
        
        # Update the flags
        widget.field_flags = flags
        widget.update()
        
    except Exception as e:
        print(f"Warning: Could not set text alignment: {str(e)}")

def get_field_flags(widget: fitz.Widget) -> int:
    """Get the field flags while preserving important existing flags."""
    try:
        # Get current flags
        current_flags = widget.field_flags if hasattr(widget, 'field_flags') else 0
        
        # Create a mask of ONLY the bits we want to manage
        # PDF field flags we want to manage (zero-based bit positions):
        # Bit 12: Multiline
        # Bit 13: Do not scroll
        # Bit 22: Do not spell check
        # Bit 0: Read only
        # Note: Bits 24-25 are for text alignment, handled separately
        managed_bits = (1 << 12) | (1 << 13) | (1 << 22) | (1 << 0)
        password_bit = (1 << 13)  # Make sure to preserve this
        alignment_bits = (3 << 24)  # Preserve alignment bits
        
        # Keep ALL flags EXCEPT our managed ones, but always preserve password and alignment bits
        preserved_flags = (current_flags & ~managed_bits) | (current_flags & password_bit) | (current_flags & alignment_bits)
        
        return preserved_flags
    except Exception as e:
        print(f"Warning: Could not get field flags: {str(e)}")
        return 0

def apply_field_flags(widget: fitz.Widget, preserved_flags: int, changes: Dict[str, bool]) -> None:
    """Apply field flag changes while preserving other flags."""
    try:
        # Start with the preserved flags (which includes password and alignment bits)
        final_flags = preserved_flags
        
        # Define the flags we manage (excluding password and alignment)
        flag_mappings = {
            'is_multiline': 1 << 12,
            'do_not_scroll': 1 << 13,
            'do_not_spell_check': 1 << 22,
            'do_not_type': 1 << 0
        }
        
        # Apply only the flags that are in our changes
        for attr, flag in flag_mappings.items():
            if attr in changes:
                if changes[attr]:
                    final_flags |= flag
                # If false, the flag remains cleared from preserved_flags
        
        # Make sure we preserve the password bit from the original flags
        password_bit = (1 << 13)
        original_password = widget.field_flags & password_bit
        final_flags = (final_flags & ~password_bit) | original_password
        
        # Set the final flags
        widget.field_flags = final_flags
        widget.update()
        
    except Exception as e:
        print(f"Warning: Could not apply field flags: {str(e)}")

def save_modified_pdf(doc: fitz.Document, output_path: str, field_changes: Dict[str, Any], selected_fields: List[int], field_widgets: Dict[int, Tuple[int, fitz.Widget]]) -> bool:
    """Save the modified PDF using various methods until one succeeds."""
    try:
        # Create a new document
        new_doc = fitz.open()
        
        # Copy each page and its widgets
        for page_num in range(len(doc)):
            # Copy the page
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            # Get widgets for this page
            new_page = new_doc[page_num]
            new_widgets = new_page.widgets()
            
            # Find widgets that need to be modified on this page
            for field_num in selected_fields:
                orig_page_num, orig_widget = field_widgets[field_num]
                if orig_page_num == page_num:
                    # Find matching widget in new page
                    for new_widget in new_widgets:
                        if new_widget.field_name == orig_widget.field_name:
                            # Get preserved flags
                            preserved_flags = get_field_flags(new_widget)
                            
                            # Handle text alignment first if specified
                            if 'text_align' in field_changes:
                                try:
                                    # Set Q value directly using xref
                                    xref = new_widget.xref
                                    new_doc.xref_set_key(xref, "Q", str(field_changes['text_align']))
                                    new_widget.update()
                                except Exception as e:
                                    print(f"Warning: Could not set text alignment for field {new_widget.field_name}: {e}")
                            
                            # Update font size if specified
                            if 'font_size' in field_changes:
                                try:
                                    new_widget.text_fontsize = field_changes['font_size']
                                except AttributeError:
                                    print(f"Warning: Could not set font size for field {new_widget.field_name}")
                            
                            # Handle flag changes
                            flag_changes = {k: v for k, v in field_changes.items() 
                                         if k in ('is_multiline', 'do_not_scroll', 
                                                'do_not_spell_check', 'do_not_type')}
                            if flag_changes:
                                apply_field_flags(new_widget, preserved_flags, flag_changes)
                            
                            break
        
        # Save the new document with minimal options to preserve structure
        new_doc.save(
            output_path,
            garbage=0,  # Don't garbage collect to preserve structure
            deflate=True,
            clean=False,  # Don't clean to preserve structure
            pretty=False,
            linear=True
        )
        
        new_doc.close()
        return True
        
    except Exception as e:
        print(f"Error saving PDF: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    # Display version information
    print(f"PDF Field Editor v{VERSION}")
    print("-" * 80)
    
    # Get template path
    template_path = input("Enter PDF template path: ").strip()
    if not os.path.exists(template_path):
        print("Error: Template file not found!")
        return
    
    # Create backup of original file
    backup_path = template_path + ".backup"
    try:
        shutil.copy2(template_path, backup_path)
        print(f"Created backup at: {backup_path}")
    except Exception as e:
        print(f"Warning: Could not create backup: {str(e)}")
    
    try:
        # Open the PDF
        doc = fitz.open(template_path)
        
        # Collect all form fields
        all_fields = []
        field_widgets = {}  # Map field index to (page_num, widget) tuple
        field_idx = 1
        
        for page_num in range(len(doc)):
            for widget in doc[page_num].widgets():
                attrs = get_field_attributes(widget)
                all_fields.append(attrs)
                field_widgets[field_idx] = (page_num, widget)
                field_idx += 1
        
        if not all_fields:
            print("No form fields found in the template!")
            return
        
        # Display all fields
        display_fields(all_fields)
        
        # Get field selection
        while True:
            try:
                selection = input("\nEnter field numbers to modify (e.g. 1-5,7,9-11) or 'all': ").strip()
                if selection.lower() == 'all':
                    selected_fields = list(range(1, len(all_fields) + 1))
                else:
                    selected_fields = parse_field_selection(selection, len(all_fields))
                break
            except ValueError as e:
                print(f"Error: {e}")
        
        # Get attribute changes
        changes = get_attribute_changes()
        
        if not changes:
            print("No changes specified!")
            return
        
        # Save as new template
        output_path = os.path.splitext(template_path)[0] + "_modified.pdf"
        
        if save_modified_pdf(doc, output_path, changes, selected_fields, field_widgets):
            print(f"\nChanges saved to: {output_path}")
            # Verify the saved file
            try:
                with fitz.open(output_path) as test_doc:
                    if len(test_doc) > 0:
                        print("Verified: The saved PDF is valid.")
                    else:
                        print("Warning: The saved PDF might be corrupted (0 pages).")
            except:
                print("Warning: Could not verify the saved PDF. It might be corrupted.")
        else:
            print("Error: Failed to save the modified PDF.")
            if os.path.exists(backup_path):
                print(f"You can restore from the backup file: {backup_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(traceback.format_exc())
        if os.path.exists(backup_path):
            print(f"You can restore from the backup file: {backup_path}")
    
    finally:
        if 'doc' in locals():
            doc.close()

if __name__ == "__main__":
    main() 