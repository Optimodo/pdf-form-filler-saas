"""
PDF Processing API Routes

Provides endpoints for PDF form filling using the proven desktop logic.
"""
import os
import tempfile
import logging
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import aiofiles

from ..core.pdf_processor import process_pdf_batch, PDFProcessor

router = APIRouter(prefix="/api/pdf", tags=["PDF Processing"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.post("/process-batch")
async def process_pdf_batch_endpoint(
    template: UploadFile = File(..., description="PDF template file"),
    csv_data: UploadFile = File(..., description="CSV data file"),
    output_name: Optional[str] = Form(None, description="Custom output directory name")
):
    """
    Process a batch of PDFs using template and CSV data.
    
    This endpoint uses the exact same logic as the desktop application
    to ensure consistent, compatible PDF output.
    """
    temp_dir = None
    try:
        # Validate file types
        if not template.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Template must be a PDF file")
        
        if not csv_data.filename.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="Data file must be a CSV file")
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        
        # Save uploaded files
        template_path = os.path.join(temp_dir, template.filename)
        csv_path = os.path.join(temp_dir, csv_data.filename)
        
        # Save template file
        async with aiofiles.open(template_path, 'wb') as f:
            content = await template.read()
            await f.write(content)
        
        # Save CSV file
        async with aiofiles.open(csv_path, 'wb') as f:
            content = await csv_data.read()
            await f.write(content)
        
        # Set output directory
        output_dir = os.path.join(temp_dir, output_name or "output")
        
        # Process PDFs using the proven desktop logic
        logger.info(f"Starting PDF batch processing: {template.filename} with {csv_data.filename}")
        result = process_pdf_batch(template_path, csv_path, output_dir)
        
        if result["success"]:
            # List generated files
            generated_files = []
            if os.path.exists(output_dir):
                generated_files = [f for f in os.listdir(output_dir) if f.endswith('.pdf')]
            
            result["generated_files"] = generated_files
            result["output_directory"] = output_dir  # For potential file downloads
            
            logger.info(f"Batch processing completed: {result['successful_count']} of {result['total_count']} PDFs")
            
        return result
        
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    finally:
        # Cleanup will happen when temp_dir goes out of scope
        # In production, you might want to schedule cleanup or use a job queue
        pass


@router.get("/templates")
async def list_available_templates():
    """
    List available PDF templates.
    
    Returns templates from the backend/templates directory.
    """
    try:
        templates_dir = Path(__file__).parent.parent.parent / "templates"
        templates = []
        
        if templates_dir.exists():
            for category_dir in templates_dir.iterdir():
                if category_dir.is_dir():
                    category_templates = []
                    for file in category_dir.iterdir():
                        if file.suffix.lower() == '.pdf':
                            # Look for corresponding CSV file
                            csv_files = list(category_dir.glob(f"{file.stem}*.csv"))
                            
                            template_info = {
                                "name": file.stem,
                                "filename": file.name,
                                "path": str(file),
                                "category": category_dir.name,
                                "has_sample_data": len(csv_files) > 0,
                                "sample_csv": csv_files[0].name if csv_files else None
                            }
                            category_templates.append(template_info)
                    
                    if category_templates:
                        templates.append({
                            "category": category_dir.name,
                            "templates": category_templates
                        })
        
        return {
            "templates": templates,
            "total_categories": len(templates),
            "total_templates": sum(len(cat["templates"]) for cat in templates)
        }
        
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.get("/templates/{category}/{template_name}")
async def get_template_info(category: str, template_name: str):
    """
    Get detailed information about a specific template.
    """
    try:
        templates_dir = Path(__file__).parent.parent.parent / "templates"
        template_path = templates_dir / category / f"{template_name}.pdf"
        
        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Get template info
        csv_files = list(template_path.parent.glob(f"{template_name}*.csv"))
        
        # Try to read PDF fields using our processor
        try:
            processor = PDFProcessor(str(template_path))
            # This would need additional method to extract field info
            # For now, just return basic info
        except Exception as e:
            logger.warning(f"Could not analyze PDF fields: {e}")
        
        return {
            "name": template_name,
            "category": category,
            "path": str(template_path),
            "size": template_path.stat().st_size,
            "has_sample_data": len(csv_files) > 0,
            "sample_csv_files": [f.name for f in csv_files]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get template info: {str(e)}")


@router.get("/download/{output_directory}/{filename}")
async def download_generated_pdf(output_directory: str, filename: str):
    """
    Download a generated PDF file.
    
    Note: In production, you'd want better security and cleanup policies.
    """
    try:
        # Validate filename for security
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        file_path = Path(output_directory) / filename
        
        if not file_path.exists() or not file_path.suffix.lower() == '.pdf':
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/pdf'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

