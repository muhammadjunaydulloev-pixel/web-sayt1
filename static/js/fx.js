/* ===========================================================
   1300 Луғат — овозҳо, эффектҳои визуалӣ ва талаффузи русӣ
   =========================================================== */
(function () {
  'use strict';

  /* ---------- Аудио контекст (як бор сохта мешавад) ---------- */
  var ctx = null;
  function getCtx() {
    if (!ctx) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (AC) ctx = new AC();
    }
    if (ctx && ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  function tone(freq, startTime, duration, opts) {
    var ac = getCtx();
    if (!ac) return;
    opts = opts || {};
    var osc = ac.createOscillator();
    var gain = ac.createGain();
    osc.type = opts.type || 'sine';
    osc.frequency.setValueAtTime(freq, startTime);
    if (opts.glideTo) {
      osc.frequency.exponentialRampToValueAtTime(opts.glideTo, startTime + duration);
    }
    var peak = opts.volume != null ? opts.volume : 0.18;
    gain.gain.setValueAtTime(0.0001, startTime);
    gain.gain.exponentialRampToValueAtTime(peak, startTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);
    osc.connect(gain);
    gain.connect(ac.destination);
    osc.start(startTime);
    osc.stop(startTime + duration + 0.02);
  }

  /* Хушоҳанг, боло-баранда — барои ҷавоби ДУРУСТ */
  function playCorrectSound() {
    var ac = getCtx();
    if (!ac) return;
    var t = ac.currentTime;
    tone(523.25, t, 0.14, { volume: 0.16 });        // C5
    tone(659.25, t + 0.11, 0.14, { volume: 0.16 });  // E5
    tone(783.99, t + 0.22, 0.22, { volume: 0.18 });  // G5
  }

  /* Садои паст, мулоим — барои ҷавоби ХАТО (на дағал) */
  function playWrongSound() {
    var ac = getCtx();
    if (!ac) return;
    var t = ac.currentTime;
    tone(220, t, 0.16, { type: 'triangle', volume: 0.15, glideTo: 174 });
    tone(164, t + 0.14, 0.22, { type: 'triangle', volume: 0.13, glideTo: 130 });
  }

  /* Садои хурсандӣ дар охири тест */
  function playFinishSound(success) {
    var ac = getCtx();
    if (!ac) return;
    var t = ac.currentTime;
    if (success) {
      [523.25, 659.25, 783.99, 1046.5].forEach(function (f, i) {
        tone(f, t + i * 0.1, 0.28, { volume: 0.15 });
      });
    } else {
      tone(392, t, 0.2, { volume: 0.14 });
      tone(329.63, t + 0.16, 0.3, { volume: 0.14 });
    }
  }

  /* ---------- Эффекти визуалӣ: конфетти барои ҷавоби дуруст ---------- */
  function burstConfetti(anchorEl) {
    var layer = document.createElement('div');
    layer.className = 'fx-confetti-layer';
    document.body.appendChild(layer);

    var rect = anchorEl ? anchorEl.getBoundingClientRect() : null;
    var originX = rect ? rect.left + rect.width / 2 : window.innerWidth / 2;
    var originY = rect ? rect.top + rect.height / 2 : window.innerHeight / 3;

    var emojis = ['🎉', '✨', '⭐', '💚', '🟢'];
    var n = 18;
    for (var i = 0; i < n; i++) {
      var p = document.createElement('span');
      p.className = 'fx-confetti-piece';
      p.textContent = emojis[Math.floor(Math.random() * emojis.length)];
      var angle = (Math.random() * Math.PI) - Math.PI / 2 - Math.PI / 2; // upward spread
      var dist = 60 + Math.random() * 120;
      var dx = Math.cos(angle) * dist * (Math.random() < 0.5 ? -1 : 1);
      var dy = -(80 + Math.random() * 100);
      p.style.left = originX + 'px';
      p.style.top = originY + 'px';
      p.style.setProperty('--dx', dx + 'px');
      p.style.setProperty('--dy', dy + 'px');
      p.style.setProperty('--rot', (Math.random() * 360 - 180) + 'deg');
      p.style.animationDelay = (Math.random() * 0.06) + 's';
      layer.appendChild(p);
    }
    setTimeout(function () {
      if (layer.parentNode) layer.parentNode.removeChild(layer);
    }, 1100);
  }

  /* ---------- Эффекти визуалӣ: ларзиш ва флеши сурх барои ҷавоби хато ---------- */
  function shakeWrong(targetEl) {
    var el = targetEl || document.body;
    el.classList.remove('fx-shake');
    // force reflow to restart animation
    void el.offsetWidth;
    el.classList.add('fx-shake');
    setTimeout(function () { el.classList.remove('fx-shake'); }, 420);

    var flash = document.createElement('div');
    flash.className = 'fx-flash-wrong';
    document.body.appendChild(flash);
    setTimeout(function () {
      if (flash.parentNode) flash.parentNode.removeChild(flash);
    }, 450);
  }

  function flashCorrect() {
    var flash = document.createElement('div');
    flash.className = 'fx-flash-correct';
    document.body.appendChild(flash);
    setTimeout(function () {
      if (flash.parentNode) flash.parentNode.removeChild(flash);
    }, 450);
  }

  /* Комбинатсияи пурра — овоз + эффект барои ҷавоби дуруст */
  function celebrateCorrect(anchorEl) {
    playCorrectSound();
    flashCorrect();
    burstConfetti(anchorEl);
  }

  /* Комбинатсияи пурра — овоз + эффект барои ҷавоби хато */
  function signalWrong(targetEl) {
    playWrongSound();
    shakeWrong(targetEl);
  }

  /* ---------- Талаффузи русӣ (Web Speech API) ---------- */
  var ruVoice = null;
  var voicesReady = false;

  function pickRuVoice() {
    if (!('speechSynthesis' in window)) return null;
    var voices = window.speechSynthesis.getVoices() || [];
    if (!voices.length) return null;
    voicesReady = true;
    var ru = voices.filter(function (v) { return /^ru/i.test(v.lang); });
    if (!ru.length) return null;
    var preferred = ru.find(function (v) { return /Google|Microsoft|Yandex|Natural/i.test(v.name); });
    return preferred || ru[0];
  }

  if ('speechSynthesis' in window) {
    pickRuVoice();
    window.speechSynthesis.onvoiceschanged = function () {
      ruVoice = pickRuVoice();
    };
  }

  function speakRu(text, btnEl) {
    if (!('speechSynthesis' in window) || !text) {
      return false;
    }
    try {
      window.speechSynthesis.cancel();
      var utter = new SpeechSynthesisUtterance(text);
      if (!ruVoice) ruVoice = pickRuVoice();
      if (ruVoice) utter.voice = ruVoice;
      utter.lang = 'ru-RU';
      utter.rate = 0.92;
      utter.pitch = 1.0;
      utter.volume = 1.0;

      if (btnEl) {
        btnEl.classList.add('speaking');
        utter.onend = function () { btnEl.classList.remove('speaking'); };
        utter.onerror = function () { btnEl.classList.remove('speaking'); };
      }
      window.speechSynthesis.speak(utter);
      return true;
    } catch (e) {
      return false;
    }
  }

  window.SlFx = {
    playCorrectSound: playCorrectSound,
    playWrongSound: playWrongSound,
    playFinishSound: playFinishSound,
    celebrateCorrect: celebrateCorrect,
    signalWrong: signalWrong,
    flashCorrect: flashCorrect,
    shakeWrong: shakeWrong,
    speakRu: speakRu
  };
})();
