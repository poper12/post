ADSGRAM_PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Loading…</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<script src="https://sad.adsgram.ai/js/sad.min.js"></script>
<style>
  body { font-family: sans-serif; background:#0f0f10; color:#eee; display:flex;
         align-items:center; justify-content:center; height:100vh; margin:0; text-align:center; }
  .msg { padding: 24px; }
</style>
</head>
<body>
<div class="msg" id="msg">Loading ad…</div>
<script>
function getToken() {
  try {
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      var sp = window.Telegram.WebApp.initDataUnsafe && window.Telegram.WebApp.initDataUnsafe.start_param;
      if (sp) return sp;
    }
  } catch (e) {}
  var params = new URLSearchParams(window.location.search || window.location.hash.replace('#', '?'));
  return params.get('startapp') || params.get('tgWebAppStartParam') || params.get('token');
}

function goTo(url) {
  if (!url) { document.getElementById('msg').innerText = 'Link expired.'; return; }
  window.location.href = url;
}

(async function () {
  var token = getToken();
  if (!token) { document.getElementById('msg').innerText = 'Invalid link.'; return; }

  var target = null, blockId = null;
  try {
    var res = await fetch('/resolve/' + encodeURIComponent(token));
    if (res.ok) {
      var data = await res.json();
      target = data.target_url;
      blockId = data.block_id;
    }
  } catch (e) {}

  if (!target) { document.getElementById('msg').innerText = 'This link has expired.'; return; }

  if (blockId && window.Adsgram) {
    try {
      await window.Adsgram.init({ blockId: blockId }).show();
    } catch (e) {
      // no ad available or user closed it early — continue to the real link anyway
    }
  }
  goTo(target);
})();
</script>
</body>
</html>
"""
