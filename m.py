#!/usr/bin/env python3
"""m.py [-u] [키워드...]                  검색 (-u: 아직 안 본 것만, 인자 없으면 전체)
m.py add 제목 감독 연도 OTT 설명 URL     추가
m.py seen [--month YYYY-MM] 키워드       본 것으로 표시 (달 미지정 시 이번 달 기록)
m.py csv                                 movies.csv로 내보내기 (엑셀용)
m.py html                                index.html 생성 (GitHub Pages용 자체완결 페이지)"""
import sqlite3, sys, os, csv, json, datetime

sys.stdout.reconfigure(encoding="utf-8")  # ponytail: 파이프로 넘길 때 Windows가 cp949를 쓰면 아랍문자에서 죽음

DB =os.path.join(os.path.dirname(os.path.abspath(__file__)), "movies.db")
COLS = "title director ott description".split()


def where(words, unwatched):
    sql = [f"({' OR '.join(f'{c} LIKE ?' for c in COLS)})" for _ in words]
    args = [f"%{w}%" for w in words for _ in COLS]
    if unwatched:
        sql.append("watched = 0")
    return (" WHERE " + " AND ".join(sql) if sql else ""), args


def search(con, words, unwatched=False):
    # ponytail: LIKE 풀스캔. 수천 편 넘어가서 느려지면 FTS5로.
    w, args = where(words, unwatched)
    sql = "SELECT title, director, year, ott, description, url, watched, seen_month FROM movies"
    return con.execute(sql + w + " ORDER BY id DESC", args).fetchall()


PAGE = r"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🎬 movie</title>
<style>
:root{--bg:#fafafa;--card:#fff;--line:#e5e5e5;--fg:#1a1a1a;--dim:#888;--seen:#12a150}
@media(prefers-color-scheme:dark){:root{--bg:#161616;--card:#1f1f1f;--line:#333;--fg:#e8e8e8;--dim:#999;--seen:#3fd67a}}
*{box-sizing:border-box}
body{margin:0;font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--fg)}
.wrap{max-width:820px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:22px;margin:0 0 2px}
.meta{color:var(--dim);font-size:13px;margin-bottom:16px}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:1}
#q{flex:1;min-width:180px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);font-size:15px}
.tabs{display:flex;gap:6px}
.tab{padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);cursor:pointer;font-size:14px;white-space:nowrap}
.tab.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.ott{display:flex;gap:10px;flex-wrap:wrap;margin:-4px 0 16px}
.ott button{width:42px;height:42px;padding:0;border:none;background:none;cursor:pointer;border-radius:50%;line-height:0;opacity:.88;transition:transform .1s,opacity .1s}
.ott button:hover{transform:scale(1.08);opacity:1}
.ott button.on{outline:2px solid var(--fg);outline-offset:2px;opacity:1}
.ott img{width:42px;height:42px;display:block}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:10px}
.card.seen{opacity:.62}
.t{font-weight:600;font-size:17px}
.t .chk{color:var(--seen);margin-right:5px}
.sub{color:var(--dim);font-size:13px;margin:3px 0 0}
.mon{color:var(--seen)}
.desc{font-size:14px;margin:8px 0 0}
.card a{font-size:13px;color:#3b82f6;text-decoration:none;word-break:break-all}
.empty{color:var(--dim);text-align:center;padding:40px}
</style></head><body><div class="wrap">
<h1>🎬 movie</h1>
<div class="meta" id="meta"></div>
<div class="bar">
  <input id="q" placeholder="제목·감독·OTT·설명 검색" autocomplete="off">
  <div class="tabs">
    <button class="tab on" data-m="unseen">안 본 것</button>
    <button class="tab" data-m="all">전체</button>
    <button class="tab" data-m="seen">본 것</button>
  </div>
</div>
<div class="ott">
  <button data-kw="넷플릭스" title="넷플릭스"><img src="icons/netflix.png" alt="넷플릭스"></button>
  <button data-kw="왓챠" title="왓챠"><img src="icons/watcha.png" alt="왓챠"></button>
  <button data-kw="웨이브" title="웨이브"><img src="icons/wavve.png" alt="웨이브"></button>
  <button data-kw="쿠팡" title="쿠팡플레이"><img src="icons/coupangplay.png" alt="쿠팡플레이"></button>
  <button data-kw="디즈니" title="디즈니+"><img src="icons/disneyplus.png" alt="디즈니+"></button>
</div>
<div id="list"></div>
<script>
const DATA=__DATA__, TS="__TS__";
const list=document.getElementById('list'), q=document.getElementById('q'), meta=document.getElementById('meta');
let mode='unseen';
const esc=s=>(s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function draw(){
  const kw=q.value.trim().toLowerCase();
  const rows=DATA.filter(m=>{
    if(mode==='unseen'&&m.w)return false;
    if(mode==='seen'&&!m.w)return false;
    if(kw){const hay=(m.t+' '+(m.d||'')+' '+(m.o||'')+' '+(m.desc||'')).toLowerCase();if(!hay.includes(kw))return false;}
    return true;
  });
  const seen=DATA.filter(m=>m.w).length;
  meta.textContent=`전체 ${DATA.length} · 본 것 ${seen} · 안 본 것 ${DATA.length-seen}  ·  갱신 ${TS}`;
  list.innerHTML=rows.length?rows.map(m=>`
    <div class="card${m.w?' seen':''}">
      <div class="t">${m.w?'<span class="chk">✓</span>':''}${esc(m.t)}</div>
      <div class="sub">${esc(m.y||'?')} · ${esc(m.d||'?')} · ${esc(m.o||'-')}${m.w&&m.mon?` · <span class="mon">👁 ${esc(m.mon)}</span>`:''}</div>
      ${m.desc?`<div class="desc">${esc(m.desc)}</div>`:''}
      ${m.u?`<a href="${esc(m.u)}" target="_blank" rel="noopener">${esc(m.u)}</a>`:''}
    </div>`).join(''):'<div class="empty">해당 없음</div>';
}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{
  document.querySelector('.tab.on').classList.remove('on');b.classList.add('on');mode=b.dataset.m;draw();
});
const ott=document.querySelectorAll('.ott button');
ott.forEach(b=>b.onclick=()=>{
  const kw=b.dataset.kw; q.value=(q.value===kw)?'':kw;
  ott.forEach(x=>x.classList.remove('on')); if(q.value)b.classList.add('on'); draw();
});
q.oninput=()=>{ott.forEach(x=>x.classList.remove('on'));draw();}; draw();
</script>
</div></body></html>"""


def render(con):
    rows = con.execute("SELECT title,director,year,ott,description,url,watched,seen_month "
                       "FROM movies ORDER BY watched, id DESC").fetchall()
    data = [{"t": t, "d": d, "y": y, "o": o, "desc": desc, "u": u, "w": w, "mon": sm}
            for t, d, y, o, desc, u, w, sm in rows]
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")  # ponytail: </script> 방어
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return PAGE.replace("__DATA__", payload).replace("__TS__", ts)


def main():
    argv = sys.argv[1:]
    if argv[:1] == ["add"]:
        with sqlite3.connect(DB) as con:
            con.execute("INSERT INTO movies (title,director,year,ott,description,url) VALUES (?,?,?,?,?,?)",
                        (argv[1:7] + [None] * 6)[:6])
        return print("추가됨")
    if argv[:1] == ["csv"]:
        cur = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).execute("SELECT * FROM movies ORDER BY id")
        out = os.path.join(os.path.dirname(DB), "movies.csv")
        # ponytail: utf-8-sig — BOM 없으면 엑셀이 한글을 cp949로 읽어서 깨뜨림
        with open(out, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([d[0] for d in cur.description])
            w.writerows(cur)
        return print(out)
    if argv[:1] == ["html"]:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        out = os.path.join(os.path.dirname(DB), "index.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(render(con))
        return print(out)
    if argv[:1] == ["seen"]:
        rest = argv[1:]
        month = datetime.datetime.now().strftime("%Y-%m")
        if "--month" in rest:  # 지난 달 소급 기록용
            i = rest.index("--month"); month = rest[i + 1]; rest = rest[:i] + rest[i + 2:]
        if not rest:  # 키워드 없으면 where가 비어 전체가 걸림 — 사고 방지
            return print("키워드를 지정해라 (예: m.py seen 싸이코). 전체 대상 방지.")
        with sqlite3.connect(DB) as con:
            w, args = where(rest, False)
            n = con.execute("UPDATE movies SET watched = 1, seen_month = ?" + w, [month] + args).rowcount
        return print(f"{n}편 본 것으로 표시 ({month})")

    unwatched = "-u" in argv
    rows = search(sqlite3.connect(f"file:{DB}?mode=ro", uri=True),
                  [a for a in argv if a != "-u"], unwatched)
    for t, d, y, o, desc, url, w, sm in rows:
        seen = f" · 본 {sm}" if w and sm else ""
        print(f"\n{'✓ ' if w else ''}{t} ({y or '?'})  · {d or '?'} · {o or '-'}{seen}")
        if desc:
            print(f"  {desc}")
        if url:
            print(f"  {url}")
    print(f"\n{len(rows)}편")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--selftest"]:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE movies (id INTEGER PRIMARY KEY, title, director, year, ott, description, url, watched, seen_month)")
        con.execute("INSERT INTO movies VALUES (1,'기생충','봉준호',2019,'넷플릭스','계급 스릴러','http://a',0,NULL)")
        con.execute("INSERT INTO movies VALUES (2,'버닝','이창동',2018,'왓챠','미스터리','http://b',1,'2026-08')")
        assert len(search(con, [])) == 2
        assert search(con, ["봉준호"])[0][0] == "기생충"
        assert search(con, ["스릴러"])[0][0] == "기생충"
        assert len(search(con, ["봉준호", "미스터리"])) == 0        # AND 조건
        assert [r[0] for r in search(con, [], unwatched=True)] == ["기생충"]
        assert [r[0] for r in search(con, ["이창동"], unwatched=True)] == []
        html = render(con)
        assert html.lower().startswith("<!doctype") and "기생충" in html and "__DATA__" not in html
        print("ok")
    else:
        main()
