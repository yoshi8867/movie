// 영화 등록 프록시 — GitHub Pages 정적 페이지에서 POST 받아 구글시트 pending 탭에 append.
// 배포: script.google.com → 새 프로젝트 → 이 코드 붙여넣기 → 배포 → 새 배포 → 웹 앱
//       실행: 나 / 액세스: 모든 사용자(익명 포함) → 승인 → /exec URL 복사해서 알려주기.
// 비번은 여기(서버)에서 검사하므로 페이지 소스로 뚫리지 않음.

const SHEET_ID = '1yuTP7dKqije5SDAgTp7A17lMBt5H4VjaxNwdDiE81pw';
const PW = '900311';

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (String(d.pw) !== PW) return out('bad password');
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
