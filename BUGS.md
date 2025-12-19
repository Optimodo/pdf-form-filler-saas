# Bug List

## Open Issues

*No open issues at this time.*


## Resolved Issues

### CSV File Line Detection Issue
**Status**: Resolved  
**Description**: CSV file line count detection was including empty or hidden lines  
**Solution**: Enhanced CSV parsing to handle BOM, improved line ending detection, and better filtering of empty rows

### Authentication Token Not Being Sent
**Status**: Resolved  
**Description**: Frontend was not sending authentication headers with PDF processing requests  
**Solution**: Added `getAuthHeaders()` to all PDF processing API calls

### Database Schema Issues
**Status**: Resolved  
**Description**: Database columns were too small for processing time values  
**Solution**: Updated VARCHAR column lengths from 10 to 20 characters

### Output Path Issues
**Status**: Resolved  
**Description**: Files were being saved to `/app/outputs` instead of `/app/storage/outputs`  
**Solution**: Updated all output paths to use storage directory

---

## Notes
- Bug list will be updated as new issues are discovered
- Priority levels: High, Medium, Low
- Status levels: Open, In Progress, Resolved, Won't Fix

