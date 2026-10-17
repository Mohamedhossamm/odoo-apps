// Customer-facing order status screen. Plain script, no framework: it runs on
// TV browsers and is served without login, outside Odoo's asset bundles.
(function () {
    "use strict";

    const POLL_MS = 3000;
    const FRESH_MS = 15000; // how long a newly ready number blinks
    const SPEECH_DELAY_MS = 900; // let the chime finish before the voice starts

    const dataUrl = document.body.dataset.url;
    const columns = {
        preparing: document.getElementById("preparing"),
        ready: document.getElementById("ready"),
    };
    const offlineBadge = document.getElementById("offline");
    const enableSoundButton = document.getElementById("enable-sound");
    const soundStatus = document.getElementById("sound-status");

    let settings = { voice: "both", repeat: 1 };
    let knownReadyIds = null; // null until the first load, so orders already ready are not called out
    const readySince = new Map();
    let audioContext = null; // created on the first tap: browsers block sound before a user gesture

    function render(column, orders, now) {
        column.replaceChildren(
            ...orders.map((order) => {
                const tile = document.createElement("div");
                tile.className = "number";
                tile.textContent = order.number;
                if (readySince.has(order.id) && now - readySince.get(order.id) < FRESH_MS) {
                    tile.classList.add("fresh");
                }
                return tile;
            })
        );
    }

    function chime() {
        if (!audioContext) {
            return;
        }
        const start = audioContext.currentTime;
        [880, 1320].forEach((frequency, index) => {
            const at = start + index * 0.25;
            const oscillator = audioContext.createOscillator();
            const gain = audioContext.createGain();
            oscillator.type = "sine";
            oscillator.frequency.value = frequency;
            gain.gain.setValueAtTime(0.0001, at);
            gain.gain.exponentialRampToValueAtTime(0.4, at + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.45);
            oscillator.connect(gain).connect(audioContext.destination);
            oscillator.start(at);
            oscillator.stop(at + 0.5);
        });
    }

    function voiceFor(language) {
        return window.speechSynthesis
            .getVoices()
            .find((voice) => voice.lang.toLowerCase().startsWith(language));
    }

    function phrasesFor(number) {
        const spoken = String(parseInt(number, 10));
        const phrases = [];
        if (settings.voice === "ar" || settings.voice === "both") {
            phrases.push({ language: "ar", text: `الطلب رقم ${spoken} جاهز` });
        }
        if (settings.voice === "en" || settings.voice === "both") {
            phrases.push({ language: "en", text: `Order number ${spoken} is ready` });
        }
        return phrases;
    }

    function callOut(number) {
        chime();
        if (!audioContext || !("speechSynthesis" in window)) {
            return;
        }
        setTimeout(() => {
            for (let round = 0; round < settings.repeat; round++) {
                for (const phrase of phrasesFor(number)) {
                    const voice = voiceFor(phrase.language);
                    // An Arabic sentence read by an English voice is noise: skip it, the chime still plays.
                    if (!voice) {
                        continue;
                    }
                    const utterance = new SpeechSynthesisUtterance(phrase.text);
                    utterance.voice = voice;
                    utterance.lang = voice.lang;
                    utterance.rate = 0.9;
                    window.speechSynthesis.speak(utterance);
                }
            }
        }, SPEECH_DELAY_MS);
    }

    async function poll() {
        try {
            const response = await fetch(dataUrl, { cache: "no-store" });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            offlineBadge.hidden = true;
            settings = { voice: data.voice, repeat: data.repeat };

            const now = Date.now();
            const newlyReady = knownReadyIds ? data.ready.filter((order) => !knownReadyIds.has(order.id)) : [];
            for (const order of newlyReady) {
                readySince.set(order.id, now);
            }
            knownReadyIds = new Set(data.ready.map((order) => order.id));
            for (const id of readySince.keys()) {
                if (!knownReadyIds.has(id)) {
                    readySince.delete(id);
                }
            }

            render(columns.preparing, data.preparing, now);
            render(columns.ready, data.ready, now);
            newlyReady.forEach((order) => callOut(order.number));
        } catch {
            offlineBadge.hidden = false;
        } finally {
            setTimeout(poll, POLL_MS);
        }
    }

    enableSoundButton.addEventListener("click", () => {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        audioContext = AudioContextClass ? new AudioContextClass() : null;
        if ("speechSynthesis" in window) {
            // A silent utterance inside the tap unlocks speech on browsers that require a gesture.
            const unlock = new SpeechSynthesisUtterance(" ");
            unlock.volume = 0;
            window.speechSynthesis.speak(unlock);
        }
        chime();
        enableSoundButton.hidden = true;
        document.documentElement.requestFullscreen?.().catch(() => {});
        // Voices can arrive a moment after the tap; check once they had time to load.
        setTimeout(reportSound, 1500);
    });

    /** Say a test sentence and show what this browser can do, so setup problems are visible on the TV. */
    function reportSound() {
        const lines = [audioContext ? "✓ النغمة · Chime" : "✗ النغمة غير مدعومة · Chime not supported"];
        if (!("speechSynthesis" in window)) {
            lines.push("✗ هذا المتصفح لا يدعم نطق الكلام · This browser cannot speak");
        } else {
            const arabic = voiceFor("ar");
            const english = voiceFor("en");
            lines.push(arabic ? `✓ صوت عربي · Arabic voice (${arabic.name})` : "✗ لا يوجد صوت عربي · No Arabic voice");
            lines.push(english ? `✓ English voice (${english.name})` : "✗ No English voice");
            const test = arabic
                ? { voice: arabic, text: "تم تشغيل الصوت" }
                : english && { voice: english, text: "Sound is on" };
            if (test) {
                const utterance = new SpeechSynthesisUtterance(test.text);
                utterance.voice = test.voice;
                utterance.lang = test.voice.lang;
                window.speechSynthesis.speak(utterance);
            }
        }
        soundStatus.replaceChildren(
            ...lines.map((line) => Object.assign(document.createElement("div"), { textContent: line }))
        );
        soundStatus.hidden = false;
        setTimeout(() => (soundStatus.hidden = true), 20000);
    }

    // Voices load asynchronously in Chrome; asking once starts the loading.
    if ("speechSynthesis" in window) {
        window.speechSynthesis.getVoices();
    }
    poll();
})();
