#!/usr/bin/env python3
"""
Debug script to isolate the PDF form field issue.
This will help us understand what's happening with form fields during document copying.
"""
import fitz  # PyMuPDF
import os
import sys

def debug_pdf_fields(template_path):
    """Debug function to check form fields before and after copying."""
    print(f"=== Debugging PDF: {template_path} ===")
    
    # Step 1: Open original document
    print("\n1. Opening original document...")
    doc = fitz.open(template_path)
    print(f"   Document has {len(doc)} pages")
    
    # Step 2: Check original form fields
    print("\n2. Checking original form fields...")
    original_fields = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        widgets = list(page.widgets())
        print(f"   Page {page_num + 1}: {len(widgets)} widgets")
        
        for widget in widgets:
            field_info = {
                'name': widget.field_name,
                'type': widget.field_type,
                'value': widget.field_value,
                'page': page_num
            }
            original_fields.append(field_info)
            print(f"     - {widget.field_name}: '{widget.field_value}' (type: {widget.field_type})")
    
    print(f"\n   Total original fields: {len(original_fields)}")
    
    # Step 3: Create new document and copy
    print("\n3. Creating new document and copying...")
    new_doc = fitz.open()
    new_doc.insert_pdf(doc)  # This is the same method as original
    print(f"   New document has {len(new_doc)} pages")
    
    # Step 4: Check copied form fields
    print("\n4. Checking copied form fields...")
    copied_fields = []
    for page_num in range(len(new_doc)):
        page = new_doc[page_num]
        widgets = list(page.widgets())
        print(f"   Page {page_num + 1}: {len(widgets)} widgets")
        
        for widget in widgets:
            field_info = {
                'name': widget.field_name,
                'type': widget.field_type,
                'value': widget.field_value,
                'page': page_num
            }
            copied_fields.append(field_info)
            print(f"     - {widget.field_name}: '{widget.field_value}' (type: {widget.field_type})")
    
    print(f"\n   Total copied fields: {len(copied_fields)}")
    
    # Step 5: Test field modification
    print("\n5. Testing field modification...")
    if copied_fields:
        # Try to modify the first field
        first_field_name = copied_fields[0]['name']
        first_field_page = copied_fields[0]['page']
        test_value = "TEST_VALUE_123"
        
        print(f"   Attempting to set '{first_field_name}' to '{test_value}'")
        
        page = new_doc[first_field_page]
        widgets = list(page.widgets())
        
        for widget in widgets:
            if widget.field_name == first_field_name:
                print(f"   Found field: {widget.field_name}")
                print(f"   Before: '{widget.field_value}'")
                widget.field_value = test_value
                widget.update()
                print(f"   After: '{widget.field_value}'")
                break
        else:
            print(f"   ERROR: Could not find field '{first_field_name}'")
    
    # Step 6: Save and verify
    print("\n6. Saving and verifying...")
    output_path = "debug_output.pdf"
    new_doc.save(output_path, garbage=0, deflate=True, clean=False, pretty=False)
    print(f"   Saved to: {output_path}")
    
    # Reopen and check
    verify_doc = fitz.open(output_path)
    print(f"   Verification document has {len(verify_doc)} pages")
    
    for page_num in range(len(verify_doc)):
        page = verify_doc[page_num]
        widgets = list(page.widgets())
        print(f"   Verification Page {page_num + 1}: {len(widgets)} widgets")
        
        for widget in widgets:
            print(f"     - {widget.field_name}: '{widget.field_value}' (type: {widget.field_type})")
    
    # Cleanup
    doc.close()
    new_doc.close()
    verify_doc.close()
    
    print(f"\n=== Debug Complete ===")

if __name__ == "__main__":
    template_path = "/app/templates/MVHR/MVHR-v2.pdf"
    if os.path.exists(template_path):
        debug_pdf_fields(template_path)
    else:
        print(f"Template not found: {template_path}")
        # List available templates
        templates_dir = "/app/templates"
        if os.path.exists(templates_dir):
            print("\nAvailable templates:")
            for root, dirs, files in os.walk(templates_dir):
                for file in files:
                    if file.endswith('.pdf'):
                        print(f"  {os.path.join(root, file)}")

