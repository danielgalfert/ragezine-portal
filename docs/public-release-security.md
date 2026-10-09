# Public release security review

This review covers the submission portal code and its Lightsail deployment. It is not a penetration test. Merge and deploy this branch before using the checks below to approve the live site.

## Controls in this branch

| Boundary | Control |
| --- | --- |
| Public form | Django validates field types, choices, lengths, country codes, file counts, and the set of accepted fields. It normalizes text and removes control characters. |
| Uploads | The server allows only PDF, DOC, DOCX, TIFF, MP4, MOV, and WebM in the right field. It checks file signatures or the DOCX package, sets a known content type, and rejects empty files. It keeps the 5 GiB per-file and 10 GiB total limits. |
| Upload load | nginx admits at most two active submission requests and one per client IP. Other requests get HTTP 429. This limits temporary disk use while nginx and Django process large files. |
| Staff login | Login requires CSRF. The API also limits login attempts by IP and username. Staff sessions expire after eight hours or when the browser closes. |
| Staff exports | XLSX values that could run as formulas are written as text. Downloads require staff access and uploaded files are sent as attachments. |
| Browser | React escapes applicant text. The portal adds a Content Security Policy, frame protection, MIME sniffing protection, referrer policy, and HSTS on the two HTTPS hosts. |
| Dependencies | Pinned backend packages and the frontend lockfile were updated after vulnerability scans. CI now runs `pip-audit` and `npm audit` before deployment. |

Input validation accepts the text needed for artist submissions. It does not remove all HTML-like characters. React and Django escape text where they render it, and the receipt email escapes its HTML fields. This keeps submitted prose intact.

## Checks before public launch

1. The weak `superuser` password was rotated on 2026-10-09. Find its new value in the Git-ignored local deployment inventory. Rotate the Brevo SMTP key that was shared in chat, then update the private server `.env`. Keep new secrets out of Git and chat.
2. Confirm that the S3 bucket is private and that its app key can access only the needed submission objects. Keep the AWS root access key disabled.
3. Run a real submission with a small file and a receipt email. Confirm staff login, protected download, XLSX export, logout, and anonymous access denial on both HTTPS hosts.
4. Check free disk space during a large test upload. The VM had about 70 GiB free at review time. nginx and Django may each use temporary disk before the file reaches S3. Keep disk monitoring and alerts on.
5. Test a PostgreSQL and S3 restore from backup. Set alerts for failed receipts, repeated 429 responses, backend errors, and low disk space.
6. Decide how staff will scan or inspect uploaded DOC, DOCX, and video files before opening them. A file signature check does not detect malware. Keep uploads private and use safe handling or add a malware scan service.

The staff portal uses passwords and rate limits; it does not yet offer MFA. Add MFA before you give access to a larger staff group or handle more sensitive data.

## Automated checks

CI runs Django tests, `check --deploy`, frontend lint and build, and dependency audits. Django reports warnings for HSTS on subdomains, HSTS preload, and its own HTTPS redirect. Caddy terminates TLS and redirects HTTP. HSTS applies to each portal host, without claiming every subdomain of `danielgalfert.com` is HTTPS-only.
