# Bug List

## Open Issues

### CSV File Line Detection Issue
**Status**: Open  
**Priority**: Medium  
**Description**: 
- CSV file line count detection sometimes includes empty or hidden lines
- User reported deleting all data and saving CSV but script still detected lines
- May be related to invisible characters, BOM, or line ending issues
- Progress bar shows incorrect file count based on this detection

**Steps to Reproduce**:
1. Create a CSV file with data
2. Delete all data and save
3. Upload to PDF processor
4. Check console logs for line count detection

**Expected Behavior**: 
- Empty CSV should show 0 lines
- Only actual data rows should be counted

**Actual Behavior**:
- Script detects lines even when CSV appears empty
- Progress bar shows incorrect file count

**Debug Information**:
- Console logs show: "CSV file analysis: X total lines, Y data rows"
- Need to investigate CSV parsing logic in `estimateFileCount` function

**Files Affected**:
- `frontend/src/App.jsx` - `estimateFileCount` function
- CSV file parsing logic

---

## Resolved Issues

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

