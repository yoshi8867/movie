// 영화 등록 프록시 — GitHub Pages 정적 페이지에서 POST 받아 구글시트 pending 탭에 append.
// 배포: script.google.com → 새 프로젝트 → 이 코드 붙여넣기 → 배포 → 새 배포 → 웹 앱
//       실행: 나 / 액세스: 모든 사용자(익명 포함) → 승인 → /exec URL 복사해서 알려주기.
// 비번은 여기(서버)에서 검사하므로 페이지 소스로 뚫리지 않음.
//
// kind:'seoichu'가 오면 서이추 완료 기록으로 보고 seoichu 탭에 append한다.
// 고칠 때는 배포 → 배포 관리 → 편집 → 버전: 새 버전 (URL이 안 바뀐다. '새 배포'는 URL이 바뀜)

const SHEET_ID = '1yuTP7dKqije5SDAgTp7A17lMBt5H4VjaxNwdDiE81pw';
const PW = '900311';

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (String(d.pw) !== PW) return out('bad password');
    if (d.kind === 'seoichu') return seoichuPost(d);
    const title = (d.title || '').toString().trim();
    if (!title) return out('no title');
    const action = (d.action === 'done') ? '완료' : '추가';
    const list = (d.list || '영화').toString().trim();
    const ss = SpreadsheetApp.openById(SHEET_ID);
    let sh = ss.getSheetByName('pending');
    if (!sh) { sh = ss.insertSheet('pending'); sh.appendRow(['시각', '동작', '목록', '제목', '메모']); }
    sh.appendRow([new Date(), action, list, title, (d.note || '').toString()]);
    return out('ok');
  } catch (err) {
    return out('err: ' + err);
  }
}

function out(s) { return ContentService.createTextOutput(s); }

function jsonp(cb, obj) {
  return ContentService.createTextOutput(cb + '(' + JSON.stringify(obj) + ')')
    .setMimeType(ContentService.MimeType.JAVASCRIPT);
}

// 페이지가 pending을 실시간으로 읽어 오버레이. JSONP(?callback=)로 CORS 우회.
function doGet(e) {
  const p = (e && e.parameter) || {};
  const cb = p.callback || 'cb';
  if (p.kind === 'seoichu') return jsonp(cb, seoichuRows());
  const sh = SpreadsheetApp.openById(SHEET_ID).getSheetByName('pending');
  let rows = [];
  if (sh && sh.getLastRow() > 1) {
    rows = sh.getRange(2, 1, sh.getLastRow() - 1, 5).getValues().map(function (r) {
      return {
        ts: (r[0] instanceof Date) ? Utilities.formatDate(r[0], 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss') : String(r[0]),
        act: String(r[1]), list: String(r[2]), title: String(r[3]), note: String(r[4])
      };
    });
  }
  return jsonp(cb, rows);
}

// ── 서이추 ──────────────────────────────────────────────
// 폰에서 [완료]를 누르면 한 줄씩 쌓인다. 같은 사람을 두 번 눌러도 그냥 두 줄 —
// 중복은 읽는 쪽(tools/seoichu.py)에서 거른다. 여기서 찾아 지우면 느리기만 하다.

function seoichuSheet() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let sh = ss.getSheetByName('seoichu');
  if (!sh) { sh = ss.insertSheet('seoichu'); sh.appendRow(['시각', '블로그ID', '닉네임', '등급']); }
  return sh;
}

function seoichuPost(d) {
  const bid = (d.bid || '').toString().trim();
  if (!bid) return out('no bid');
  seoichuSheet().appendRow([new Date(), bid, (d.who || '').toString(), (d.grade || '').toString()]);
  return out('ok');
}

function seoichuRows() {
  const sh = seoichuSheet();
  if (sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, 4).getValues().map(function (r) {
    return {
      ts: (r[0] instanceof Date) ? Utilities.formatDate(r[0], 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss') : String(r[0]),
      bid: String(r[1]), who: String(r[2]), grade: String(r[3])
    };
  });
}
