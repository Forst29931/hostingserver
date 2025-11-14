# Roblox Script Server

A web-based script hosting server with authentication and mass editing features.

## Features
- 🔐 Password protected web editor
- 📝 Mass edit multiple scripts at once
- 🗂️ Organize scripts in folders
- 🚀 Public script URLs for loadstring
- ✨ Dark theme interface

## Deployment Options

### Option 1: Railway.app (Recommended)
1. Create account at https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect your GitHub and select this repository
4. Railway will auto-detect and deploy
5. Your URL: `https://your-app.railway.app`

**Cost:** $5/month (500 hours free trial)

### Option 2: Render.com
1. Create account at https://render.com
2. Click "New" → "Web Service"
3. Connect GitHub repository
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `python script_server.py`

**Cost:** Free tier available (spins down after inactivity)

### Option 3: Heroku
1. Create account at https://heroku.com
2. Install Heroku CLI
3. Run:
```bash
heroku login
heroku create your-app-name
git push heroku main
```

**Cost:** $7/month (no free tier anymore)

### Option 4: DigitalOcean/Linode VPS
1. Create a $5/month droplet
2. SSH into server
3. Install Python and requirements
4. Run with gunicorn or systemd service

**Cost:** $5-6/month

## Local Development
```bash
pip install -r requirements.txt
python script_server.py
```

Visit `http://localhost:5000`

## Default Credentials
- Username: `admin`
- Password: `changeme123`

⚠️ **Change these immediately in `server_config.json`**

## Usage in Roblox
```lua
loadstring(game:HttpGet("https://your-domain.com/scripts/folder-name/script.lua"))()
```

## Security Notes
- Script URLs (`/scripts/`) are publicly accessible (no login required)
- Only the web editor requires authentication
- Change default password before hosting publicly
- Use HTTPS in production (Railway/Render provide this automatically)

## File Structure
```
├── script_server.py       # Main server file
├── requirements.txt       # Python dependencies
├── Procfile              # For Railway/Heroku
├── lua_scripts/          # Your script folders (created automatically)
│   ├── project-1/
│   │   ├── script1.lua
│   │   └── script2.lua
│   └── project-2/
│       └── loader.lua
└── server_config.json    # Login credentials (created on first run)
```

## Environment Variables (Optional)
- `PORT` - Server port (default: 5000)

## Support
For issues or questions, check the Railway/Render documentation or contact support.
