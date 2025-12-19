# PDF Form Filler SaaS

A web-based SaaS application for batch-filling PDF forms using data from CSV files. Evolved from a desktop application to a modern web platform.

## Features

- **Multi-tenant SaaS**: Support for multiple organizations
- **Template Management**: Upload and manage PDF templates with categorization
- **Batch Processing**: Process multiple PDFs from CSV data
- **Real-time Progress**: Background processing with live progress updates
- **User Management**: Role-based access control
- **REST API**: Full API for integrations

## Architecture

- **Backend**: FastAPI (Python) with PostgreSQL database
- **Frontend**: React with modern UI components
- **Queue System**: Celery with Redis for background processing
- **Deployment**: Docker containers for easy deployment

## Local Development Setup

### Prerequisites

- Docker and Docker Compose
- Git

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Optimodo/pdf-form-filler-saas.git
   cd pdf-form-filler-saas
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

3. **Start the development environment:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Manual Setup (Alternative)

If you prefer to run without Docker:

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
# Set up environment variables (see .env.example)
uvicorn app.main:app --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## Project Structure

```
pdf-form-filler-saas/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── core/         # Core business logic
│   │   ├── models/       # Database models
│   │   ├── services/     # Business services
│   │   └── utils/        # Utility functions
│   ├── templates/        # PDF templates
│   ├── uploads/          # User-uploaded files
│   └── outputs/          # Generated PDFs
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API calls
│   │   └── utils/        # Frontend utilities
│   └── public/
├── docker/               # Docker configurations
├── archive-desktop-app/  # Original desktop application (reference)
└── docker-compose.yml    # Development environment
```

## Migration from Desktop App

This project evolved from a Windows desktop PDF form filler. The original desktop application code is preserved in the `archive-desktop-app/` directory for reference.

### Key Changes:
- **GUI**: Migrated from PySide6 (Qt) to React web interface
- **Architecture**: Single-user desktop → Multi-tenant web SaaS
- **Processing**: Synchronous → Asynchronous background processing
- **Storage**: Local files → Database with organized file management
- **Deployment**: Windows executable → Docker containers

### Reused Components:
- PDF processing logic (PyMuPDF)
- Template structure and CSV data format
- Field mapping and validation logic

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is proprietary software. All rights reserved.

## Contact

**Developer:** Mike McLean  
**Company:** Malcolm Building Services  
**Email:** mike.mclean@malcolmbuildingservices.co.uk
