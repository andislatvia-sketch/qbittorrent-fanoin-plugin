# FANO.IN Plugin Installation Guide

Complete step-by-step instructions for installing and configuring the FANO.IN qBittorrent search plugin.

---

## Prerequisites

- **qBittorrent** 4.3.x or later
- **Python** 3.7 or later (usually included with qBittorrent)
- Valid **FANO.IN tracker account**
- Internet connection

---

## Installation Methods

### ⚡ Quick Install (Automatic, with UI prompt)

**Easiest method for most users.**

1. Open **qBittorrent**
2. Go to **View** → **Search Engine** (if Search tab is not visible)
3. Click **Search plugins...** button (bottom right of Search tab)
4. Click **Install a new one**
5. Select **Web link**
6. Paste this URL:
   ```
   https://raw.githubusercontent.com/andislatvia-sketch/qbittorrent-fanoin-plugin/main/fanoin.py
   ```
7. Click **Install**
8. qBittorrent will prompt for username and password
9. Enter your FANO.IN credentials
10. Start searching!

---

### 📁 Manual Install (No credentials needed initially)

**Best method for advanced users who want to configure credentials separately.**

#### Step 1: Download Files

Download these files from the repository:
- `fanoin.py` — the plugin itself
- `fanoin.json` — configuration file (optional but recommended)

#### Step 2: Locate Your Plugin Folder

Navigate to your qBittorrent nova3 engines folder:

**Windows:**
```
%localappdata%\qBittorrent\nova3\engines\
```
Or in PowerShell:
```powershell
$env:LOCALAPPDATA + "\qBittorrent\nova3\engines\"
```

**Linux:**
```bash
~/.local/share/qBittorrent/nova3/engines/
```

**macOS:**
```bash
~/Library/Application\ Support/qBittorrent/nova3/engines/
```

#### Step 3: Place Files

Copy the downloaded files into the engines folder:
- `fanoin.py` → `nova3/engines/fanoin.py`
- `fanoin.json` → `nova3/engines/fanoin.json` (optional)

#### Step 4: Restart qBittorrent

Close and reopen qBittorrent for the plugin to load.

---

## Configuration Methods

### Method A: Credentials in fanoin.json (Recommended ✅)

**Most secure — credentials stay local, not hardcoded in the plugin.**

#### Step 1: Create Configuration File

In the `nova3/engines/` folder, create a file named `fanoin.json`:

**Windows (Notepad):**
1. Right-click in the folder → New → Text Document
2. Name it `fanoin.json`
3. Edit with Notepad and paste:
   ```json
   {
     "username": "your_fano_username",
     "password": "your_fano_password"
   }
   ```
4. Save (Ctrl+S)

**Linux/macOS (Terminal):**
```bash
cat > ~/.local/share/qBittorrent/nova3/engines/fanoin.json << 'EOF'
{
  "username": "your_fano_username",
  "password": "your_fano_password"
}
EOF
```

#### Step 2: Edit with Your Credentials

Replace:
- `your_fano_username` → your actual FANO.IN username
- `your_fano_password` → your actual FANO.IN password

**Example:**
```json
{
  "username": "john_doe",
  "password": "MySecurePass123!"
}
```

#### Step 3: Verify File Format

Make sure:
- File is named exactly `fanoin.json` (lowercase)
- It's in the same folder as `fanoin.py`
- Valid JSON format (use [JSONLint](https://jsonlint.com/) to validate)
- No trailing commas or extra quotes

#### Step 4: Test

1. Open qBittorrent
2. Go to Search tab
3. Select **FANO.IN** from engine dropdown
4. Try a search
5. If login fails, check:
   - Username/password are correct
   - JSON file has proper format
   - File is in correct location

---

### Method B: Credentials in fanoin.py (Hardcoded)

**Less secure — credentials embedded in the plugin file.**

#### Step 1: Edit fanoin.py

Open `fanoin.py` with any text editor and find these lines (around line 68):
```python
USERNAME = "YOUR_USERNAME"
PASSWORD = "YOUR_PASSWORD"
```

#### Step 2: Replace with Your Credentials

Change to:
```python
USERNAME = "your_fano_username"
PASSWORD = "your_fano_password"
```

**Example:**
```python
USERNAME = "john_doe"
PASSWORD = "MySecurePass123!"
```

#### Step 3: Save and Restart

1. Save the file (Ctrl+S)
2. Restart qBittorrent
3. The plugin will now use these hardcoded credentials

---

### Method C: Interactive Login (UI Prompt)

**Simplest method — enter credentials when installing.**

1. Use the **Quick Install** method above
2. qBittorrent will ask for username/password
3. Enter your FANO.IN credentials
4. Plugin saves them automatically

**Note:** This method stores credentials in qBittorrent's internal configuration.

---

## Configuration File Examples

### fanoin.json Format

**Standard format:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**With special characters (must be escaped):**
```json
{
  "username": "user@domain.com",
  "password": "Pass\"word!@#$"
}
```

**Validate JSON online:** https://jsonlint.com/

---

## Troubleshooting Configuration

### Issue: "Plugin not loading"

**Solution:**
1. Verify `fanoin.py` is in correct folder
2. Check filename is exactly `fanoin.py` (case-sensitive on Linux/macOS)
3. Verify Python version: Python 3.7+ required
4. Restart qBittorrent

### Issue: "Login failed — check username/password"

**Solution:**
1. Verify credentials are correct at FANO.IN website
2. Check if `fanoin.json` exists and is properly formatted
3. Validate JSON: paste content into https://jsonlint.com/
4. Delete `fanoin.cookies` file and retry
5. Check account status on FANO.IN (may be disabled)

### Issue: "Cannot read fanoin.json"

**Solution:**
1. Verify file name is exactly `fanoin.json` (lowercase)
2. Verify it's in the same folder as `fanoin.py`
3. Check file permissions (should be readable)
4. Validate JSON format: https://jsonlint.com/
5. On Linux/macOS, verify file encoding is UTF-8

### Issue: "Search returns no results"

**Solution:**
1. Verify you're logged in to FANO.IN
2. Check your internet connection
3. Try a simpler search query
4. Check FANO.IN website status (may be down)
5. Delete `fanoin.cookies` and retry

### Issue: "Permission denied" error

**Solution:**

**Windows:**
1. Right-click qBittorrent → Run as Administrator
2. Check folder write permissions

**Linux/macOS:**
```bash
chmod 755 ~/.local/share/qBittorrent/nova3/engines/
chmod 644 ~/.local/share/qBittorrent/nova3/engines/fanoin.*
```

---

## Security Best Practices

### ✅ DO:
- Use method with `fanoin.json` (credentials stay local)
- Use strong, unique passwords
- Keep plugin and configuration files secure
- Verify JSON format before using
- Delete `fanoin.cookies` if sharing computer

### ❌ DON'T:
- Hardcode passwords in `fanoin.py`
- Share `fanoin.json` files with others
- Store credentials in plain text emails
- Upload credentials to public repositories
- Use weak or reused passwords

---

## File Locations Reference

### Windows
```
Plugin:     C:\Users\YourName\AppData\Local\qBittorrent\nova3\engines\fanoin.py
Config:     C:\Users\YourName\AppData\Local\qBittorrent\nova3\engines\fanoin.json
Cookies:    C:\Users\YourName\AppData\Local\qBittorrent\nova3\engines\fanoin.cookies
```

### Linux
```
Plugin:     ~/.local/share/qBittorrent/nova3/engines/fanoin.py
Config:     ~/.local/share/qBittorrent/nova3/engines/fanoin.json
Cookies:    ~/.local/share/qBittorrent/nova3/engines/fanoin.cookies
```

### macOS
```
Plugin:     ~/Library/Application Support/qBittorrent/nova3/engines/fanoin.py
Config:     ~/Library/Application Support/qBittorrent/nova3/engines/fanoin.json
Cookies:    ~/Library/Application Support/qBittorrent/nova3/engines/fanoin.cookies
```

---

## Uninstalling

### Method 1: Via qBittorrent UI
1. Open qBittorrent → Search tab
2. Click **Search plugins...**
3. Select **FANO.IN**
4. Click **Uninstall**
5. Restart qBittorrent

### Method 2: Manual Removal
1. Navigate to `nova3/engines/` folder
2. Delete:
   - `fanoin.py`
   - `fanoin.json` (if present)
   - `fanoin.cookies` (if present)
3. Restart qBittorrent

---

## Updating the Plugin

### Auto-Update (Recommended)
qBittorrent can auto-update plugins. Check in Settings → Search Engine.

### Manual Update
1. Download latest `fanoin.py` from GitHub
2. Replace the old file in `nova3/engines/`
3. Keep `fanoin.json` (your configuration)
4. Restart qBittorrent

---

## Getting Help

If you encounter issues:

1. **Check this guide** — covers 90% of problems
2. **Validate JSON** — use https://jsonlint.com/
3. **Check plugin logs** — View stderr output in qBittorrent
4. **Open an Issue** — https://github.com/andislatvia-sketch/qbittorrent-fanoin-plugin/issues

---

## Version Compatibility

| Component | Version |
|-----------|---------|
| qBittorrent | 4.3.x or later |
| Python | 3.7+ |
| Plugin | 1.01 (current) |
| FANO.IN | Active tracker |

---

## Next Steps

1. ✅ Install the plugin (choose a method above)
2. ✅ Configure credentials (fanoin.json recommended)
3. ✅ Test by performing a search
4. ✅ Enjoy downloading from FANO.IN!

---

**Last Updated:** October 2024  
**Plugin Version:** 1.01  
**License:** BSD 3-Clause
