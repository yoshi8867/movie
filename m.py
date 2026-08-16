#!/usr/bin/env python3
"""m.py [-u] [키워드...]                  검색 (-u: 아직 안 본 것만, 인자 없으면 전체)
m.py add 제목 감독 연도 OTT 설명 URL     추가
m.py seen [--month YYYY-MM] 키워드       본 것으로 표시 (달 미지정 시 이번 달 기록)
m.py csv                                 movies.csv로 내보내기 (엑셀용)
m.py html                                index.html 생성 (GitHub Pages용 자체완결 페이지)
m.py item add 목록 제목 [메모]           일반 목록(와먹 등)에 항목 추가
m.py item done 목록 키워드 [--month YYYY-MM]  일반 목록 항목 완료 표시"""
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
[hidden]{display:none!important}
body{margin:0;font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--fg)}
.wrap{max-width:820px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:22px;margin:0 0 2px}
.meta{color:var(--dim);font-size:13px;margin-bottom:16px}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:1}
#q{flex:1;min-width:180px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);font-size:15px}
.tabs{display:flex;gap:6px}
.tab{padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);cursor:pointer;font-size:14px;white-space:nowrap}
.tab.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.lists{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.lists button{padding:8px 15px;border:1px solid var(--line);border-radius:20px;background:var(--card);color:var(--fg);cursor:pointer;font-size:15px}
.lists button.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
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
.pend{color:#e0a000;font-weight:600}
.done-btn{margin-top:10px;padding:6px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);font-size:13px;cursor:pointer}
.done-btn:hover{background:var(--line)}
.reg{margin:0 0 16px}
.reg summary{cursor:pointer;color:var(--dim);font-size:14px;user-select:none}
.reg form{display:flex;flex-direction:column;gap:8px;margin-top:10px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.reg input,.reg textarea{padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);font-size:15px;font-family:inherit}
.reg textarea{resize:vertical;min-height:44px}
.reg button{padding:9px;border:none;border-radius:8px;background:var(--fg);color:var(--bg);font-size:15px;cursor:pointer}
.reg .msg{font-size:13px;color:var(--dim);min-height:1em}
.desc{font-size:14px;margin:8px 0 0}
.card a{font-size:13px;color:#3b82f6;text-decoration:none;word-break:break-all}
.empty{color:var(--dim);text-align:center;padding:40px}
</style></head><body><div class="wrap">
<h1 id="h1">🎬 movie</h1>
<div class="meta" id="meta"></div>
<div class="lists" id="lists"></div>
<div class="bar">
  <input id="q" placeholder="검색" autocomplete="off">
  <div class="tabs">
    <button class="tab" data-m="want"></button>
    <button class="tab" data-m="all">전체</button>
    <button class="tab" data-m="done"></button>
  </div>
</div>
<div class="ott" id="ottbar">
  <button data-kw="넷플릭스" title="넷플릭스"><img src="icons/netflix.png" alt="넷플릭스"></button>
  <button data-kw="왓챠" title="왓챠"><img src="icons/watcha.png" alt="왓챠"></button>
  <button data-kw="웨이브" title="웨이브"><img src="icons/wavve.png" alt="웨이브"></button>
  <button data-kw="쿠팡" title="쿠팡플레이"><img src="icons/coupangplay.png" alt="쿠팡플레이"></button>
  <button data-kw="디즈니" title="디즈니+"><img src="icons/disneyplus.png" alt="디즈니+"></button>
</div>
<details class="reg" id="reg" hidden>
  <summary>➕ 등록 (대충 적어도 됨)</summary>
  <form id="regform" autocomplete="on">
    <input type="password" id="pw" placeholder="비밀번호" autocomplete="current-password" required>
    <select id="rl"></select>
    <input type="text" id="rt" placeholder="제목 (대충)" required>
    <textarea id="rn" placeholder="메모 (감독·연도 등 기억나는 대로, 선택)"></textarea>
    <button type="submit">등록</button>
    <div class="msg" id="rmsg"></div>
  </form>
</details>
<div id="list"></div>
<script>
const DATA=__DATA__, ITEMS=__ITEMS__, TS="__TS__", GAS="__GAS__";
const LAB={'영화':['안 본 것','본 것','👁'],'와먹':['안 먹은 것','먹은 것','🍽']};
const DEF=['안 한 것','한 것','✓'];
const lists=['영화',...new Set(ITEMS.map(x=>x.l))];
const $=id=>document.getElementById(id);
const list=$('list'), q=$('q'), meta=$('meta'), h1=$('h1'), ottbar=$('ottbar'), lbar=$('lists');
const esc=s=>(s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const lab=l=>LAB[l]||DEF;
const P=new URLSearchParams(location.search);
let curList=lists.includes(P.get('list'))?P.get('list'):'영화';
let mode=['all','want','done'].includes(P.get('tab'))?P.get('tab'):'want';

lbar.innerHTML=lists.map(l=>`<button data-l="${esc(l)}">${l==='영화'?'🎬 영화':esc(l)}</button>`).join('');

function paint(){
  const[w,d]=lab(curList);
  document.querySelector('[data-m="want"]').textContent=w;
  document.querySelector('[data-m="done"]').textContent=d;
  h1.textContent=curList==='영화'?'🎬 movie':`🍽 ${curList}`;
  ottbar.hidden=curList!=='영화';
  [...lbar.children].forEach(b=>b.classList.toggle('on',b.dataset.l===curList));
  document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('on',b.dataset.m===mode));
  const p=new URLSearchParams();p.set('list',curList);p.set('tab',mode);
  history.replaceState(null,'',location.pathname+'?'+p.toString());
  draw();
}
function draw(){
  const kw=q.value.trim().toLowerCase();
  if(curList==='영화'){
    const rows=DATA.filter(m=>{
      if(mode==='want'&&m.w)return false;
      if(mode==='done'&&!m.w)return false;
      if(kw&&!((m.t+' '+(m.d||'')+' '+(m.o||'')+' '+(m.desc||'')).toLowerCase().includes(kw)))return false;
      return true;});
    const seen=DATA.filter(m=>m.w).length;
    meta.textContent=`전체 ${DATA.length} · 본 것 ${seen} · 안 본 것 ${DATA.length-seen}  ·  갱신 ${TS}`;
    list.innerHTML=rows.length?rows.map(m=>`
      <div class="card${m.w?' seen':''}">
        <div class="t">${m.w?'<span class="chk">✓</span>':''}${esc(m.t)}${m.s==='user'?' <span class="pend">🕗 대기</span>':''}</div>
        <div class="sub">${esc(m.y||'?')} · ${esc(m.d||'?')} · ${esc(m.o||'-')}${m.w&&m.mon?` · <span class="mon">👁 ${esc(m.mon)}</span>`:''}</div>
        ${m.desc?`<div class="desc">${esc(m.desc)}</div>`:''}
        ${m.u?`<a href="${esc(m.u)}" target="_blank" rel="noopener">${esc(m.u)}</a>`:''}
      </div>`).join(''):'<div class="empty">해당 없음</div>';
  }else{
    const ic=lab(curList)[2], all=ITEMS.filter(x=>x.l===curList);
    const rows=all.filter(x=>{
      const dn=x.st==='done';
      if(mode==='want'&&dn)return false;
      if(mode==='done'&&!dn)return false;
      if(kw&&!((x.t+' '+(x.note||'')).toLowerCase().includes(kw)))return false;
      return true;});
    const done=all.filter(x=>x.st==='done').length;
    meta.textContent=`전체 ${all.length} · ${lab(curList)[1]} ${done} · ${lab(curList)[0]} ${all.length-done}  ·  갱신 ${TS}`;
    list.innerHTML=rows.length?rows.map(x=>{const dn=x.st==='done',rd=x.c?x.c.slice(5,10).replace('-','/'):'';return `
      <div class="card${dn?' seen':''}">
        <div class="t">${dn?'<span class="chk">✓</span>':''}${esc(x.t)}${x.s==='user'?' <span class="pend">🕗 대기</span>':''}</div>
        ${x.note?`<div class="desc">${esc(x.note)}</div>`:''}
        <div class="sub">${rd?`등록 ${rd}`:''}${dn&&x.mon?`${rd?' · ':''}<span class="mon">${ic} ${esc(x.mon)}</span>`:''}</div>
        ${!dn&&GAS?`<button class="done-btn" data-t="${esc(x.t)}">✅ ${curList==='와먹'?'먹었다':'완료'}</button>`:''}
      </div>`;}).join(''):'<div class="empty">해당 없음</div>';
  }
}
lbar.onclick=e=>{const b=e.target.closest('button');if(!b)return;curList=b.dataset.l;paint();};
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{mode=b.dataset.m;paint();});
const ott=document.querySelectorAll('.ott button');
ott.forEach(b=>b.onclick=()=>{
  const kw=b.dataset.kw; q.value=(q.value===kw)?'':kw;
  ott.forEach(x=>x.classList.remove('on')); if(q.value)b.classList.add('on'); draw();
});
q.oninput=()=>{ott.forEach(x=>x.classList.remove('on'));draw();};
// 완료(먹었다) 처리 — 비번 필요, GAS로 지시 전송 후 내가 반영. 낙관적으로 카드만 즉시 흐리게.
list.addEventListener('click',e=>{
  const b=e.target.closest('.done-btn'); if(!b||!GAS)return;
  const pw=localStorage.getItem('pw')||prompt('비밀번호'); if(!pw)return;
  localStorage.setItem('pw',pw);
  fetch(GAS,{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain;charset=utf-8'},
    body:JSON.stringify({pw,action:'done',list:curList,title:b.dataset.t})});
  b.textContent='✅ 접수됨'; b.disabled=true; b.closest('.card').style.opacity=.4;
});
paint();

// 등록 폼 — GAS 웹앱으로 전송. no-cors라 응답은 못 읽으므로 낙관적 처리.
if(GAS){
  const reg=$('reg'); reg.hidden=false;
  const pw=$('pw'), rt=$('rt'), rn=$('rn'), rl=$('rl'), rmsg=$('rmsg');
  rl.innerHTML=lists.map(l=>`<option>${esc(l)}</option>`).join(''); rl.value=curList;
  pw.value=localStorage.getItem('pw')||'';  // ponytail: 브라우저 저장 실패 대비 localStorage로도 채움
  $('regform').onsubmit=async e=>{
    e.preventDefault();
    localStorage.setItem('pw',pw.value);
    rmsg.textContent='전송 중...';
    try{
      await fetch(GAS,{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain;charset=utf-8'},
        body:JSON.stringify({pw:pw.value,list:rl.value,title:rt.value.trim(),note:rn.value.trim()})});
      rmsg.textContent='✅ 등록됨. 곧 반영됩니다.'; rt.value=''; rn.value='';
    }catch(_){ rmsg.textContent='❌ 전송 실패. 네트워크 확인.'; }
  };
}
</script>
</div></body></html>"""


GAS_URL = "https://script.google.com/macros/s/AKfycbwJ27_GZz3O8LH8dMm-1PnGLX9o-bO7MexEaYnRhO0PKEd-_jy92IDnKp_vcMr5QCs8pw/exec"  # ponytail: GAS 웹앱 /exec URL. 비면 등록폼 숨김.


def render(con):
    rows = con.execute("SELECT title,director,year,ott,description,url,watched,seen_month,source "
                       "FROM movies ORDER BY watched, id DESC").fetchall()
    data = [{"t": t, "d": d, "y": y, "o": o, "desc": desc, "u": u, "w": w, "mon": sm, "s": src}
            for t, d, y, o, desc, u, w, sm, src in rows]
    irows = con.execute("SELECT list,title,note,status,done_month,source,created_at "
                        "FROM items ORDER BY status DESC, id DESC").fetchall()
    items = [{"l": l, "t": t, "note": n, "st": st, "mon": dm, "s": src, "c": c}
             for l, t, n, st, dm, src, c in irows]
    j = lambda x: json.dumps(x, ensure_ascii=False).replace("</", "<\\/")  # ponytail: </script> 방어
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return (PAGE.replace("__DATA__", j(data)).replace("__ITEMS__", j(items))
                .replace("__TS__", ts).replace("__GAS__", GAS_URL))


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
    if argv[:2] == ["item", "add"]:  # item add <목록> <제목> [메모]
        lst, title = argv[2:4]
        note = argv[4] if len(argv) > 4 else None
        with sqlite3.connect(DB) as con:
            con.execute("INSERT INTO items (list,title,note) VALUES (?,?,?)", (lst, title, note))
        return print(f"[{lst}] 추가됨")
    if argv[:2] == ["item", "done"]:  # item done <목록> <키워드...> [--month YYYY-MM]
        lst, rest = argv[2], argv[3:]
        month = datetime.datetime.now().strftime("%Y-%m")
        if "--month" in rest:
            i = rest.index("--month"); month = rest[i + 1]; rest = rest[:i] + rest[i + 2:]
        if not rest:  # 키워드 없으면 목록 전체가 걸림 — 사고 방지
            return print("키워드를 지정해라. 목록 전체 대상 방지.")
        cond = " AND ".join(f"(title LIKE ? OR note LIKE ?)" for _ in rest)
        args = [f"%{w}%" for w in rest for _ in range(2)]
        with sqlite3.connect(DB) as con:
            n = con.execute("UPDATE items SET status='done', done_month=? WHERE list=? AND " + cond,
                            [month, lst] + args).rowcount
        return print(f"[{lst}] {n}개 완료 표시 ({month})")

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
        con.execute("CREATE TABLE movies (id INTEGER PRIMARY KEY, title, director, year, ott, description, url, watched, seen_month, source)")
        con.execute("INSERT INTO movies VALUES (1,'기생충','봉준호',2019,'넷플릭스','계급 스릴러','http://a',0,NULL,NULL)")
        con.execute("INSERT INTO movies VALUES (2,'버닝','이창동',2018,'왓챠','미스터리','http://b',1,'2026-08',NULL)")
        con.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, list, title, note, status, done_month, source, created_at)")
        con.execute("INSERT INTO items VALUES (1,'와먹','도넛',NULL,'want',NULL,NULL,NULL)")
        assert len(search(con, [])) == 2
        assert search(con, ["봉준호"])[0][0] == "기생충"
        assert search(con, ["스릴러"])[0][0] == "기생충"
        assert len(search(con, ["봉준호", "미스터리"])) == 0        # AND 조건
        assert [r[0] for r in search(con, [], unwatched=True)] == ["기생충"]
        assert [r[0] for r in search(con, ["이창동"], unwatched=True)] == []
        html = render(con)
        assert html.lower().startswith("<!doctype") and "기생충" in html and "__DATA__" not in html
        assert "도넛" in html and "__ITEMS__" not in html  # 목록(와먹) 주입 확인
        print("ok")
    else:
        main()
