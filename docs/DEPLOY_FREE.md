# Free Deployment Guide

This app is best deployed for free by keeping the Python server on your own machine and sharing it with Tailscale.

That fits the project because it writes files locally, keeps a SQLite database, downloads ONNX models, and runs long CPU jobs. Cheap/free cloud platforms usually break one or more of those assumptions.

## Best Free Setup

Use this stack:

1. GitHub for source control
2. your own Windows PC or laptop for the Flask app
3. Tailscale Funnel for a public HTTPS URL

If you only want private access for yourself across devices, use normal Tailscale sharing instead of Funnel.

## Important Limitation

When the app is shared publicly, `Local Folder` mode cannot work for visitors because folder paths are checked on the machine running Flask.

This repo now includes a shared mode that disables `Local Folder` automatically when you launch through:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\share-with-tailscale.ps1
```

Visitors must upload gallery images in that mode.

## First-Time Setup

1. Install Python if needed.
2. Install Tailscale and sign in.
3. Open this project folder in PowerShell.
4. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

This installs dependencies, creates `data/` folders, and downloads the OpenCV models.

## Share The App

Public URL:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\share-with-tailscale.ps1
```

Private tailnet-only URL:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\share-with-tailscale.ps1 -Private
```

What the script does:

1. checks that Python and Tailscale are available
2. starts the Flask app in public-share mode on port `8000`
3. waits for the app to come up
4. runs `tailscale funnel 8000` or `tailscale serve 8000`

Keep both PowerShell windows open while the app is live.

## Push To GitHub Safely

Right now, Git on this machine is rooted at `C:\Users\shaan`, not this project. Do not run `git add .` from that parent repo, or you may stage your whole home folder.

Create a dedicated Git repo inside `face-sort-studio` instead:

```powershell
cd C:\Users\shaan\OneDrive\Desktop\face-sort-studio
git init
git branch -M main
git add .
git commit -m "Initial commit"
```

Then create an empty GitHub repository named `face-sort-studio` and connect it:

```powershell
git remote add origin https://github.com/<your-username>/face-sort-studio.git
git push -u origin main
```

## Ongoing Updates

After the first push:

```powershell
git add .
git commit -m "Describe your change"
git push
```

## Notes

- `.gitignore` already excludes runtime data such as SQLite, jobs, outputs, and ONNX model files.
- If your laptop sleeps or shuts down, the shared app goes offline.
- Tailscale Funnel is the cleanest free option for this project. It avoids the storage and background-job limits that usually break serverless hosting.
