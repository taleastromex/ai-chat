'use strict';

const start = Date.now();
let attempt = 0;

function fmt(ms) {
  const s = Math.floor(ms / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
}

function setStep(phase) {
  const s1 = document.getElementById('s1');
  const s2 = document.getElementById('s2');

  if (phase === 'waiting_for_ollama' || phase === 'starting') {
    s1.className = 'step active';
    s2.className = 'step';
  } else if (phase === 'pulling' || phase.includes('%')) {
    s1.className = 'step done';
    s2.className = 'step active';
  }
}

async function poll() {
  attempt++;
  document.getElementById('elapsed').textContent = fmt(Date.now() - start);

  try {
    const res = await fetch('/ready');

    if (res.ok) {
      document.getElementById('s1').className = 'step done';
      document.getElementById('s2').className = 'step done';
      document.getElementById('s3').className = 'step done active';
      document.querySelector('.status').innerHTML =
        '✅ Model loaded — <span>redirecting…</span>';
      setTimeout(() => { window.location.href = '/'; }, 800);
      return;
    }

    if (res.status === 500) {
      const body = await res.json().catch(() => ({ detail: 'Unknown error' }));
      const s2el = document.getElementById('s2');
      s2el.style.color = 'var(--red)';
      s2el.querySelector('.step-dot').style.background = 'var(--red)';

      const bar = document.querySelector('.bar');
      bar.style.animation = 'none';
      bar.style.background = 'var(--red)';
      bar.style.width = '100%';

      document.querySelector('.status').innerHTML =
        `<span style="color:var(--red)">Error: ${body.detail}</span><br>
         <span style="font-size:11px">Check <code>docker logs AI-FABLE</code> or the terminal running run_local.sh</span>`;
      return;
    }

    // 503 — still loading; detail carries the phase / pull progress.
    const body = await res.json().catch(() => ({}));
    const phase = body.detail || 'loading';
    setStep(phase);
    document.querySelector('.status').innerHTML =
      `${phase} &nbsp;·&nbsp; <span>${fmt(Date.now() - start)}</span>`;
  } catch {
    document.querySelector('.status').innerHTML =
      `Connecting… <span>${fmt(Date.now() - start)}</span>`;
  }

  const delay = attempt < 5 ? 1000 : 3000;
  setTimeout(poll, delay);
}

poll();
