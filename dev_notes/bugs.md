# Known Bugs & Issues

## Summary List

**Fixed:**
- Google OAuth user creation missing required fields
- PDF Job Activity Log "Not Found" error (missing endpoint)
- ProcessingHistory date display issue
- ProcessingHistory CSV column missing data
- Dashboard container width constraint issue

**Ongoing:**
- None currently

---

## Detailed Descriptions

### Fixed Bugs

#### Google OAuth User Creation Missing Fields
**Status:** ✅ Fixed  
**Issue:** Google OAuth user creation was failing because new User objects weren't being created with all required fields (credits_used_this_month, credits_rollover, credits_used_total, total_pdf_runs, is_premium, custom_limits_enabled).  
**Fix:** Updated `google_oauth_callback` in `backend/app/api/auth_routes.py` to explicitly set all required fields during user creation. Also fixed `expires_at` calculation for OAuthAccount.

#### PDF Job Activity Log "Not Found" Error
**Status:** ✅ Fixed  
**Issue:** Admin panel PDF Job Activity Log was showing "Error: Not Found" when trying to view jobs.  
**Fix:** Restored the accidentally deleted `@router.get("/jobs")` endpoint in `backend/app/api/admin_routes.py`.

#### ProcessingHistory Date Display Issue
**Status:** ✅ Fixed  
**Issue:** Date column in ProcessingHistory was not displaying correctly.  
**Fix:** Updated date formatting to use `new Date(job.created_at).toLocaleString()` instead of previous formatting method.

#### ProcessingHistory CSV Column Missing Data
**Status:** ✅ Fixed  
**Issue:** CSV column in ProcessingHistory was showing empty cells even when CSV files existed.  
**Fix:** Updated CSV display logic to properly check for `csv_file` object and fall back to `csv_filename`, with better error handling.

#### Dashboard Container Width Constraint
**Status:** ✅ Fixed  
**Issue:** User dashboard was constrained to 800px width instead of using wider 1400px layout like admin pages.  
**Fix:** Added `dashboard-main-container` class to override `main-container` width constraint, allowing dashboard-container to use full 1400px width.

### Ongoing Issues

*No known ongoing bugs at this time.*

---

## Notes

- This list should only be updated when explicitly requested
- Fixed bugs remain in the list for reference
- All bugs should include: status, description, and fix details

