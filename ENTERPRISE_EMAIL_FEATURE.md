# Enterprise Email Delivery Feature - Technical Overview

## Overview

This document outlines how to implement a professional bulk email delivery system for enterprise clients who want to automatically email generated PDFs (certificates, documents, etc.) to recipients.

## The Problem

- Users want to send certificates/documents via email automatically
- Emails from our domain would look unprofessional
- Need to avoid spam filters and maintain deliverability
- Must comply with 2025 email regulations (Google/Yahoo requirements)

## The Solution: Domain Authentication

**Key Insight**: Users verify their own domain/subdomain, so emails appear to come from their domain, not ours.

### How It Works

1. **User Domain Verification**
   - User provides their domain (e.g., `company.com` or `mail.company.com`)
   - System generates DNS records (SPF, DKIM, DMARC)
   - User adds records to their DNS
   - System verifies domain ownership
   - Emails sent "from" their domain (e.g., `certificates@company.com`)

2. **Email Service Provider (ESP) Integration**
   - Use transactional email APIs:
     - **SendGrid** (popular, good docs)
     - **Mailgun** (developer-friendly)
     - **AWS SES** (cost-effective at scale)
     - **Resend** (modern, great DX)
     - **Postmark** (excellent deliverability)
   - ESP handles:
     - SMTP infrastructure
     - IP reputation management
     - Bounce/complaint handling
     - Delivery tracking

3. **Email Flow**
   ```
   CSV Upload → PDF Generation → Email Queue → ESP API → Recipient Inbox
                    ↓
              (Email column in CSV)
   ```

## Technical Implementation

### Backend Components

1. **Domain Verification System**
   ```python
   # Models
   class VerifiedDomain(Base):
       user_id: UUID
       domain: str  # e.g., "mail.company.com"
       verification_token: str
       is_verified: bool
       spf_record: str
       dkim_public_key: str
       dmarc_policy: str
       verified_at: datetime
   ```

2. **Email Service Integration**
   ```python
   # Email service abstraction
   class EmailService:
       async def send_pdf_email(
           self,
           to_email: str,
           pdf_path: str,
           subject: str,
           body: str,
           from_email: str,  # user's verified domain
           from_name: str
       ) -> EmailResult
   ```

3. **CSV Processing Enhancement**
   - Add `email` column validation
   - Extract email addresses during processing
   - Queue emails after PDF generation
   - Track delivery status

### Frontend Components

1. **Domain Verification UI**
   - Domain input form
   - DNS record instructions
   - Verification status indicator
   - Test email sending

2. **Email Template Editor**
   - Subject line template (with variables)
   - Body template (HTML/text)
   - PDF attachment handling
   - Preview functionality

3. **Email Job Status**
   - Delivery status per recipient
   - Bounce/complaint tracking
   - Retry failed emails
   - Email logs

## Email Authentication (SPF, DKIM, DMARC)

### SPF (Sender Policy Framework)
```
TXT record: "v=spf1 include:sendgrid.net ~all"
```
- Authorizes ESP's mail servers to send on behalf of domain

### DKIM (DomainKeys Identified Mail)
```
TXT record: "k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC..."
```
- Adds cryptographic signature to emails
- Proves email wasn't tampered with

### DMARC (Domain-based Message Authentication)
```
TXT record: "v=DMARC1; p=quarantine; rua=mailto:reports@company.com"
```
- Policy for handling failed authentication
- Receives reports on email performance

## Compliance Requirements (2025)

### Google & Yahoo Requirements (Since Feb 2024)
1. ✅ **SPF, DKIM, DMARC authentication** (covered by domain verification)
2. ✅ **One-click unsubscribe** (required in all bulk emails)
3. ✅ **Low spam rates** (<0.3% spam complaint rate)
4. ✅ **Valid from address** (verified domain)

### GDPR/Privacy
- Opt-in consent tracking
- Data retention policies
- Right to deletion
- Privacy policy links

## Pricing Model Options

### Option 1: Credits-Based
- Each email = X credits
- Separate from PDF processing credits
- Example: 1 email = 0.5 credits

### Option 2: Quota-Based
- Monthly email quota per tier
- Standard: 1,000 emails/month
- Pro: 10,000 emails/month
- Enterprise: Unlimited

### Option 3: Hybrid
- Base quota included
- Additional emails cost credits
- Enterprise: Unlimited included

## Implementation Phases

### Phase 1: Foundation
1. Domain verification system
2. ESP integration (start with one provider)
3. Basic email sending (no templates)

### Phase 2: Enhanced Features
1. Email template editor
2. Delivery tracking
3. Bounce/complaint handling
4. Retry mechanism

### Phase 3: Advanced
1. Scheduled sending
2. A/B testing
3. Analytics dashboard
4. Multiple ESP support

## Example User Flow

1. **Setup** (one-time):
   - User enters domain: `mail.company.com`
   - System generates DNS records
   - User adds records to DNS
   - System verifies domain

2. **Processing**:
   - User uploads CSV with `email` column
   - System generates PDFs
   - For each PDF:
     - Attach to email
     - Send to corresponding email address
     - Track delivery status

3. **Monitoring**:
   - User views email delivery dashboard
   - Sees sent/delivered/bounced/failed
   - Can retry failed emails

## Benefits

✅ **Professional Appearance**: Emails from user's domain
✅ **Better Deliverability**: Proper authentication prevents spam
✅ **Compliance**: Meets 2025 email regulations
✅ **Scalability**: ESP handles infrastructure
✅ **User Control**: Users manage their sender reputation
✅ **Enterprise-Ready**: Suitable for high-volume clients

## Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| DNS complexity | Provide clear step-by-step instructions, auto-verification |
| Domain verification | Use DNS TXT record verification |
| Email deliverability | Use reputable ESP, proper authentication |
| Spam filters | Follow best practices, maintain good reputation |
| Cost at scale | Use cost-effective ESP (AWS SES) or pass costs to users |

## Recommended ESP: Resend

**Why Resend?**
- Modern API with excellent documentation
- Built-in domain verification UI
- Great developer experience
- Competitive pricing
- Good deliverability
- Webhook support for tracking

**Alternative**: AWS SES (if cost is primary concern)

## Next Steps

1. Research ESP options and pricing
2. Design domain verification flow
3. Create database schema for verified domains
4. Build DNS record generator
5. Implement email sending service
6. Add email tracking and status updates
7. Create frontend UI for domain management
8. Add email template editor
9. Implement compliance features (unsubscribe, etc.)

## References

- [Google/Yahoo Bulk Email Requirements](https://support.google.com/mail/answer/81126)
- [SPF Record Syntax](https://www.openspf.org/SPF_Record_Syntax)
- [DMARC Policy Guide](https://dmarc.org/wiki/FAQ)
- [Resend Documentation](https://resend.com/docs)


