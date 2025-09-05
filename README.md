# 🏥 Claims Management System

A comprehensive Django web application for managing insurance claims with modern UI, enterprise-grade security, and powerful data management capabilities.

## ✨ Key Features

### 🎯 Core Functionality
- **Smart Claims Table**: Full-width responsive table with professional pagination (10/20/50 per page)
- **Modal Details View**: Large, scrollable modals for claim details with HTMX interactivity
- **Live Search & Filter**: Real-time search by patient/insurer with status filtering
- **Flag & Annotate System**: User-generated flags and notes with timestamps
- **Professional Formatting**: Currency amounts with thousands separators ($1,234.56)

### 🛡️ Security & Administration  
- **Role-Based Access**: Admin-only dashboard with visual role indicators
- **Secure Data Management**: Protected file upload/export with validation
- **Multi-User Support**: User authentication with activity tracking
- **Error Handling**: Comprehensive logging and graceful error recovery

### 📊 Data Management
- **File Upload System**: Support for CSV (pipe-delimited) and JSON formats
- **Bulk Operations**: Add new data or overwrite existing with transaction safety
- **Export Capabilities**: JSON, CSV export with metadata for backup/analysis
- **Data Validation**: Automatic file format and field validation

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Virtual environment

### Steps to run
```bash
# 1. Clone the repo and Navigate to project
git clone https://github.com/abhin2149/erisa-dev-challenge
cd erisa-dev-challenge

# 2. Install requirements  
pip install -r requirements.txt

# 3. Activate venv
source venv/bin/activate

# 4. Run setup
bash start.sh

# 5. Start server
python manage.py runserver

# 6. Login
admin
admin123

# 7. Navigate to /data-admin/data-upload/
Upload the required claim_list and claim_detail_data.csv files (or any other with the specified format)
```

### 🔐 Access Credentials
- **Admin User**: `admin` / `admin123` (Full access + dashboard)
- **Regular User**: `testuser` / `testpass` (Claims access only)

### 🌐 Application URLs
- **Main App**: `http://localhost:8000/` (Claims interface)
- **Django Admin**: `http://localhost:8000/admin/` (User management)
- **Data Admin**: `http://localhost:8000/data-admin/` (File upload/export)

## 🏗️ Architecture

### Technology Stack
- **Backend**: Django 4.2.24 with SQLite
- **Frontend**: Bootstrap 5.3 + HTMX 1.8 + Alpine.js  
- **Security**: Multi-layer access control with logging
- **Performance**: Optimized queries with pagination

### Data Models
```python
Claim              # Core insurance claim data
├── ClaimDetail    # CPT codes, denial reasons
├── Flag          # User review flags
└── Note          # User annotations
```

### File Structure
```
insurance-claim-app/
├── claims/                    # Main Django app
│   ├── models.py             # Data models
│   ├── views.py              # HTMX-powered views  
│   ├── data_views.py         # File upload/export
│   ├── utils.py              # Data import utilities
│   └── management/commands/  # CLI data loading
├── templates/                # Modern UI templates
├── static/                   # CSS/JS assets
└── venv/                     # Python environment
```

## 📋 User Guide

### Claims Management
1. **Browse Claims**: Full-width table with smart pagination
2. **Search & Filter**: Live search + status filtering
3. **View Details**: Click any row to open modal with full details
4. **Add Notes**: Quick note addition with user attribution
5. **Flag Claims**: Mark claims for review with timestamps

### Admin Features (Admin/Staff Only)
1. **Dashboard Access**: `/claims/dashboard/` - Analytics and statistics
2. **Data Upload**: `/data-admin/data-upload/` - Bulk CSV/JSON import
3. **Data Export**: `/data-admin/data-export/` - Backup and analysis
4. **User Management**: Django admin for user roles

### File Format Support
**CSV (Pipe-delimited)**:
```csv
id|patient_name|billed_amount|paid_amount|status|insurer_name|discharge_date
99001|John Doe|15000.50|12000.00|Paid|Blue Cross|2025-01-15
```

**JSON Format**:
```json
[{
  "id": 99001,
  "patient_name": "John Doe", 
  "billed_amount": "15000.50",
  "paid_amount": "12000.00",
  "status": "Paid",
  "insurer_name": "Blue Cross",
  "discharge_date": "2025-01-15"
}]
```

## 🔧 Advanced Features

### Security Implementation
- **View-Level Protection**: Backend permission checks
- **UI Access Control**: Conditional navigation based on roles
- **Error Handling**: Graceful redirects with user messages
- **File Validation**: Upload security with size/format limits

### Performance Optimizations  
- **Smart Pagination**: 20-50 records per page (vs 6,201+ before)
- **Database Optimization**: `select_related` and `prefetch_related`
- **HTMX Integration**: Partial page updates without reloads
- **Query Efficiency**: 99% reduction in data loading overhead

### Data Management Features
- **Import Modes**: Add new records or overwrite existing data
- **File Validation**: Format checking, required fields, data types
- **Error Reporting**: Detailed row-by-row error messages
- **Transaction Safety**: Database rollback on import failures
- **Export Options**: Multiple formats with backup metadata

## 🧪 Testing & Validation

### Quick Test Scenarios
1. **Search**: Try "Virginia" or "Blue Cross" 
2. **Pagination**: Switch between 10/20/50 records per page
3. **Modal Details**: Click any Claim ID to open details
4. **Permissions**: Test dashboard access with both user types
5. **File Upload**: Use provided sample files for testing

### Sample Data Included
- **6,201 realistic claims** with complete data
- **Sample CSV/JSON files** for upload testing
- **Pre-configured users** for immediate access
- **Professional formatting** throughout
