# 🚂 Railway Deployment Guide (Easiest Method)

## Step 1: Prepare Your Files
1. Download all these files:
   - `script_server.py`
   - `requirements.txt`
   - `Procfile`
   - `.gitignore`
   - `README.md`

## Step 2: Create GitHub Repository
1. Go to https://github.com/new
2. Create a new repository (name it `roblox-script-server`)
3. Upload all the files above
4. Commit and push

**OR use GitHub Desktop:**
1. Download GitHub Desktop
2. Create new repository
3. Add files to the repository folder
4. Commit and publish

## Step 3: Deploy on Railway
1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access GitHub
5. Select your `roblox-script-server` repository
6. Railway will automatically:
   - Detect it's a Python app
   - Install requirements
   - Start the server

## Step 4: Get Your URL
1. In Railway dashboard, click on your deployment
2. Go to "Settings" tab
3. Under "Domains", click "Generate Domain"
4. You'll get something like: `https://roblox-script-server-production.up.railway.app`

## Step 5: Change Password
1. In Railway dashboard, click "Variables" tab
2. You can add environment variables or...
3. SSH into Railway console and edit `server_config.json`

**Better way:**
Add to your code to use environment variables:
- Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in Railway variables

## Step 6: Use Your Server
**Web Editor:**
```
https://your-app.railway.app/
```

**In Roblox:**
```lua
loadstring(game:HttpGet("https://your-app.railway.app/scripts/folder/script.lua"))()
```

## Costs
- **Free Trial:** 500 hours ($5 credit)
- **After trial:** ~$5/month for 24/7 hosting
- No sleep/downtime (unlike Render free tier)

## Tips
✅ Keep your repository private (scripts are sensitive)
✅ Change default password immediately
✅ Enable 2FA on Railway account
✅ Railway provides automatic HTTPS
✅ Check logs in Railway dashboard if issues occur

## Alternative: No GitHub Method
If you don't want to use GitHub:
1. Railway → "Deploy from template"
2. Use Railway CLI:
```bash
npm i -g @railway/cli
railway login
railway init
railway up
```

## Troubleshooting
**Server won't start?**
- Check Railway logs for errors
- Verify `requirements.txt` has Flask
- Make sure `Procfile` is correct

**Can't access website?**
- Check if domain is generated
- Wait 2-3 minutes for first deployment
- Check if service is running in Railway dashboard

**Scripts not loading?**
- Verify folder structure in Railway files
- Check script URLs are correct
- HTTPS required for Roblox to load scripts
