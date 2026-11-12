import os, secrets
import requests
from flask import Flask, Response, abort, jsonify, make_response, redirect, request
from ytmusicapi import YTMusic
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

GID, GSEC = os.environ["GOOGLE_CLIENT_ID"], os.environ["GOOGLE_CLIENT_SECRET"]
BASE = os.environ.get("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
SECURE = BASE.startswith("https")
app = Flask(__name__)
YT = YTMusic()  # חיפוש בלי התחברות

PAGE = r"""<!doctype html><html lang=he dir=rtl><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Spotify → YouTube</title>
<style>body{font-family:system-ui;max-width:520px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}
button,a.b{background:#1db954;color:#000;border:0;border-radius:20px;padding:.6rem 1.2rem;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block;margin:.2rem 0}
input[type=text]{width:100%;padding:.5rem;margin:.5rem 0;box-sizing:border-box}.d{color:#999;font-size:.85rem}progress{width:100%}</style>
<h1>העברת פלייליסט מספוטיפיי ליוטיוב</h1>
<div id=form>
<p class=d>1. ייצא את הפלייליסט ל-CSV ב-<a href="https://exportify.app" target=_blank style="color:#1db954">exportify.app</a><br>2. בחר את הקובץ כאן והתחבר ליוטיוב. זהו.<br>הקובץ נקרא בדפדפן שלך ולא נשמר אצלנו.</p>
<input type=file id=f accept=.csv><input type=text id=n placeholder="שם הפלייליסט ביוטיוב (לא חובה)">
<button id=b>המשך והתחבר ליוטיוב</button></div>
<div id=o></div>
<script>
const $=id=>document.getElementById(id),el=(t,x,c)=>{const e=document.createElement(t);e.textContent=x;if(c)e.className=c;return e};
function parseCSV(t){const rows=[];let r=[],c='',q=false;t=t.replace(/^\uFEFF/,'');
for(let i=0;i<t.length;i++){const ch=t[i];
 if(q){if(ch=='"'){if(t[i+1]=='"'){c+='"';i++}else q=false}else c+=ch}
 else if(ch=='"')q=true;else if(ch==','){r.push(c);c=''}
 else if(ch=='\n'||ch=='\r'){if(ch=='\r'&&t[i+1]=='\n')i++;r.push(c);rows.push(r);r=[];c=''}
 else c+=ch}
if(c||r.length){r.push(c);rows.push(r)}return rows}
$('b').onclick=async()=>{
  const file=$('f').files[0];if(!file)return alert('בחר קובץ CSV');
  const rows=parseCSV(await file.text()),h=rows[0]||[];
  const ti=h.findIndex(x=>x.includes('Track Name')),ai=h.findIndex(x=>x.includes('Artist'));
  if(ti<0||ai<0)return alert('הקובץ לא נראה כמו CSV של Exportify');
  const tracks=rows.slice(1).filter(r=>r[ti]).map(r=>r[ai].split(';')[0]+' '+r[ti]).slice(0,2000);
  if(!tracks.length)return alert('לא נמצאו שירים בקובץ');
  sessionStorage.setItem('job',JSON.stringify({name:$('n').value||file.name.replace('.csv',''),tracks}));
  location='/login';
};
const post=async(u,b)=>{const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});
  const j=await r.json();if(!r.ok)throw new Error(r.status==401?'ההתחברות פגה, התחל מחדש':(j.error||r.status));return j};
function progress(txt,d,t){const o=$('o');o.textContent='';o.append(el('p',txt+': '+d+' / '+t));
  const p=document.createElement('progress');p.max=t;p.value=d;o.append(p,el('p','השאר את הדף פתוח.','d'))}
async function run(S){
  $('form').style.display='none';
  try{
    const ids=[],missed=[];
    for(let i=0;i<S.tracks.length;i+=10){
      const q=S.tracks.slice(i,i+10),r=await post('/api/search',{queries:q});
      r.ids.forEach((v,k)=>{if(!v)missed.push(q[k]);else if(!ids.includes(v))ids.push(v)});
      progress('מחפש ביוטיוב',Math.min(i+10,S.tracks.length),S.tracks.length);
    }
    let url=null,added=0;
    const pl=await post('/api/playlist',{name:S.name});
    if(!pl.quota){
      url='https://www.youtube.com/playlist?list='+pl.id;
      for(let i=0;i<ids.length;i+=10){
        const r=await post('/api/add',{playlistId:pl.id,ids:ids.slice(i,i+10)});
        added+=r.added;progress('מוסיף לפלייליסט',added,ids.length);if(r.quota)break;
      }
    }
    const rest=ids.slice(added),o=$('o');o.textContent='';o.append(el('h2','סיימנו ✓'));
    if(url){const a=el('a','פתח את הפלייליסט ביוטיוב','b');a.href=url;a.target='_blank';o.append(el('p','נוספו '+added+' שירים.'),a)}
    if(rest.length){o.append(el('p','מכסת היוטיוב היומית נגמרה. לחץ על כל קישור ושמור את הפלייליסט שנפתח (Save playlist):','d'));
      for(let i=0;i<rest.length;i+=50){const c=rest.slice(i,i+50),a=el('a','חלק '+(i/50+1)+' ('+c.length+' שירים)','b');
        a.href='https://www.youtube.com/watch_videos?video_ids='+c.join(',');a.target='_blank';o.append(a,document.createElement('br'))}}
    if(missed.length)o.append(el('p','לא נמצאו: '+missed.join(' | '),'d'));
    sessionStorage.removeItem('job');
  }catch(e){$('o').textContent='שגיאה: '+e.message}
}
const S=JSON.parse(sessionStorage.getItem('job')||'null');
if(S&&location.search.includes('go=1')){history.replaceState(null,'','/');run(S)}
</script></html>"""

def g(token, path, qs, body=None):
    r = requests.request("POST" if body else "GET", "https://www.googleapis.com/youtube/v3/" + path,
                         params=qs, json=body, headers={"Authorization": "Bearer " + token}, timeout=20)
    j = r.json()
    if not r.ok:
        raise RuntimeError(j.get("error", {}).get("message", str(r.status_code)))
    return j

def token():
    t = request.cookies.get("yt")
    if not t: abort(401)
    return t

def is_quota(e): return "quota" in str(e).lower()

@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")

@app.get("/login")
def login():
    state = secrets.token_urlsafe(16)
    url = requests.Request("GET", "https://accounts.google.com/o/oauth2/v2/auth", params=dict(
        client_id=GID, response_type="code", redirect_uri=BASE + "/callback",
        scope="https://www.googleapis.com/auth/youtube", state=state)).prepare().url
    resp = make_response(redirect(url))
    resp.set_cookie("st", state, max_age=600, httponly=True, secure=SECURE, samesite="Lax")
    return resp

@app.get("/callback")
def callback():
    if "code" not in request.args or request.args.get("state") != request.cookies.get("st"):
        return redirect("/")
    r = requests.post("https://oauth2.googleapis.com/token", data=dict(
        code=request.args["code"], client_id=GID, client_secret=GSEC,
        redirect_uri=BASE + "/callback", grant_type="authorization_code"), timeout=20)
    if not r.ok: return "Google login failed", 400
    resp = make_response(redirect("/?go=1"))
    resp.set_cookie("yt", r.json()["access_token"], max_age=3300, httponly=True, secure=SECURE, samesite="Lax")
    resp.delete_cookie("st")
    return resp

@app.post("/api/search")
def search():
    token()
    out = []
    for q in (request.get_json(silent=True) or {}).get("queries", [])[:12]:
        try:
            r = YT.search(q, filter="songs", limit=1) or YT.search(q, filter="videos", limit=1)
            out.append(r[0]["videoId"] if r else None)
        except Exception:
            out.append(None)
    return jsonify(ids=out)

@app.post("/api/playlist")
def playlist():
    t = token()
    name = str((request.get_json(silent=True) or {}).get("name") or "Spotify import")[:100]
    try:
        pl = g(t, "playlists", {"part": "snippet,status"},
               {"snippet": {"title": name, "description": "Imported from Spotify"}, "status": {"privacyStatus": "private"}})
        return jsonify(id=pl["id"])
    except RuntimeError as e:
        if is_quota(e): return jsonify(quota=True)
        return jsonify(error=str(e)), 500

@app.post("/api/add")
def add():
    t = token()
    d = request.get_json(silent=True) or {}
    added = 0
    for vid in d.get("ids", [])[:12]:
        try:
            g(t, "playlistItems", {"part": "snippet"},
              {"snippet": {"playlistId": d["playlistId"], "resourceId": {"kind": "youtube#video", "videoId": vid}}})
            added += 1
        except RuntimeError as e:
            if is_quota(e): return jsonify(added=added, quota=True)
            return jsonify(error=str(e), added=added), 500
    return jsonify(added=added)

if __name__ == "__main__":
    app.run(port=3000)
