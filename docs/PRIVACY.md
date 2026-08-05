# Privacy

**Leafkit does not upload your files.**

- All processing is local.
- No telemetry or crash phoning-home.
- No accounts.
- Optional Ghostscript (if you install it) is also local.

- Session passwords stay in memory only (never written to disk).
- The local job log stores **file names only**, not full paths.
- **Diagnostics export** is **optional, defaults to off, and is anonymous**:
  - No name, account, email, device ID, or hostname.
  - Crash/job log tails **redact** home paths, usernames, IPs, and emails.
  - First launch asks once; Settings can change it later.
  - Export is built **on your PC** only; you choose whether to paste it into a GitHub Issue.
- Installed app data lives under **`%LOCALAPPDATA%\Leafkit`** (not Program Files).

See [LIMITS.md](LIMITS.md) and [REPORTING.md](REPORTING.md).
