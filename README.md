# 🎬 YouTube Clipper

Personal-use YouTube video/audio clipper — link paste karo, time-range select karo, quality/format choose karo, download karo.

## Features
- Video preview (thumbnail, title, duration)
- Accurate HH:MM:SS start/end time selection + slider
- Quality: Auto / 480p / 720p / 1080p / 1440p / 4K
- Format: MP4 / MP3 / M4A / WEBM
- Progress bar + clean error messages
- Mobile-friendly UI
- No login system (lightweight)

## Tech
- Backend: Flask + yt-dlp + FFmpeg
- Frontend: plain HTML/CSS/JS
- Deployment: Docker (Render Free tier compatible)

---

## GitHub par kaise daalein (naya project)

1. GitHub par apna existing repo kholain (jo Render se connected hai).
2. **Purani files delete karein** in sabko: `app.py`, `templates/index.html`, `static/` folder ki purani files, `Dockerfile`, `requirements.txt`.
3. **Naya folder structure** yeh hona chahiye:
   ```
   app.py
   Dockerfile
   requirements.txt
   .gitignore
   README.md
   templates/
     └── index.html
   static/
     ├── style.css
     └── script.js
   ```
4. Har file ko GitHub web UI se **"Add file" → "Upload files"** karke upload karein, ya "Create new file" karke paste karein.
5. Neeche "Commit changes" button dabayein.
6. Render apne aap naya deploy start kar dega (agar auto-deploy on hai).

## Render par deploy

1. Render dashboard me apni service kholain.
2. Environment: **Docker** (Dockerfile already diya hua hai).
3. Koi extra environment variable ki zaroorat nahi.
4. Free tier par pehli baar deploy hone me 2-5 minute lag sakte hain (FFmpeg install hota hai).
5. Deploy complete hone ke baad apna Render URL kholain aur test karein.

## Local test (optional)

```bash
pip install -r requirements.txt
python app.py
```
Browser me `http://localhost:8080` kholain.

## Note
Yeh tool sirf personal/fair-use ke liye hai. Downloaded content ka copyright uske original owner ke paas rehta hai — please YouTube ke Terms of Service ka dhyaan rakhein.
