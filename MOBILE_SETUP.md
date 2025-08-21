# 📱 Mobile Access Setup Guide

## Quick Fix for Mobile QR Code Issues

### Step 1: Find Your Computer's IP Address
Your computer's IP addresses are:
- `172.21.160.1` (Docker/WSL network)
- `172.20.217.125` (WiFi network)

### Step 2: Mobile Access URLs
Try these URLs on your mobile device:

**HTTPS (Recommended for camera access):**
- `https://172.20.217.125:3443/mobile`
- `https://172.21.160.1:3443/mobile`

**HTTP (Fallback):**
- `http://172.20.217.125:3000/mobile`
- `http://172.21.160.1:3000/mobile`

### Step 3: Troubleshooting

#### If QR Code Doesn't Work:
1. **Manual URL Entry**: Type the URL directly in your mobile browser
2. **Network Check**: Ensure both devices are on the same WiFi network
3. **Certificate Warning**: For HTTPS, accept the security warning (self-signed certificate)

#### If Camera Doesn't Start:
1. **Use HTTPS**: Mobile browsers require HTTPS for camera access
2. **Allow Permissions**: Grant camera permissions when prompted
3. **Try Different Browser**: Chrome/Safari work best

#### If Connection Fails:
1. **Firewall**: Check Windows Firewall isn't blocking ports 3000/3443
2. **Network**: Ensure mobile and laptop are on same WiFi
3. **Docker**: Verify container is running: `docker compose ps`

### Step 4: Test Connection
1. Open desktop version: `http://localhost:3000`
2. Scan QR code or manually enter mobile URL
3. Accept certificate warning on mobile
4. Grant camera permissions
5. Start camera on mobile device

### Alternative Testing
If QR code still doesn't work, try:
1. **Direct IP**: `https://[YOUR_IP]:3443/mobile`
2. **Mobile hotspot**: Connect laptop to phone's hotspot
3. **Different network**: Try different WiFi network

## Success Indicators
✅ Desktop shows QR code with correct IP
✅ Mobile can access the URL (even with certificate warning)
✅ Mobile camera permissions granted
✅ Video stream appears on mobile device
✅ Object detection works on mobile

## Need Help?
- Check Docker logs: `docker compose logs -f`
- Verify IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
- Test desktop first: `http://localhost:3000`