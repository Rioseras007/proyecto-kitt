const container = document.getElementById("voice");
const audioEl = document.getElementById("kitt-audio");
const btnInit = document.getElementById("btn-init");
const btnMusic = document.getElementById("btn-music");
const btnMic = document.getElementById("btn-mic");
const btnOff = document.getElementById("btn-off");
const statusEl = document.getElementById("audio-status");

const columns = 3;
const ledsPerColumn = 20;
let leds = [];
let audioCtx;
let analyzer;
let sourceMicNode;   
let stream;
let animationId;
let currentMode = 'off';

// Iniciar estructura visual
function createLeds() {
    container.innerHTML = '';
    leds = [];
    for (let c = 0; c < columns; c++) {
        let column = document.createElement("div");
        column.className = "column";
        let columnLeds = [];
        for (let i = 0; i < ledsPerColumn; i++) {
            let led = document.createElement("div");
            led.className = "led";
            column.appendChild(led);
            columnLeds.push(led);
        }
        container.appendChild(column);
        leds.push(columnLeds);
    }
}

async function initContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        analyzer = audioCtx.createAnalyser();
        analyzer.fftSize = 256;
        analyzer.smoothingTimeConstant = 0.6;
        if (btnInit) btnInit.style.display = 'none';
    }
    if (audioCtx.state === 'suspended') {
        await audioCtx.resume();
    }
    updateStatus();
}

function updateStatus() {
    if (!audioCtx || !statusEl) return;
    statusEl.innerText = "SISTEMA ONLINE";
    statusEl.className = "running";
}

function clearLeds() {
    leds.forEach(col => col.forEach(led => led.classList.remove('on')));
}

function stopAll() {
    if (animationId) cancelAnimationFrame(animationId);
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    if (audioEl) audioEl.pause();
    clearLeds();
    currentMode = 'off';
    btnMusic.classList.remove('active');
    btnMic.classList.remove('active-mic');
    container.classList.remove('mic-mode');
    if (statusEl) {
        statusEl.innerText = "STANDBY";
        statusEl.className = "suspended";
    }
}

async function startMusic() {
    await initContext();
    stopAll();
    
    if (audioEl) {
        audioEl.currentTime = 0;
        audioEl.play().catch(e => console.error("KITT: Audio error", e));
    }

    btnMusic.classList.add('active');
    currentMode = 'music';
    animate();
}

async function startMic() {
    await initContext();
    stopAll();
    
    try {
        stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                autoGainControl: false,
                noiseSuppression: false,
                echoCancellation: false
            } 
        });
        sourceMicNode = audioCtx.createMediaStreamSource(stream);
        sourceMicNode.connect(analyzer);
        
        btnMic.classList.add('active-mic');
        container.classList.add('mic-mode');
        currentMode = 'mic';
        animate();
    } catch (err) {
        console.error("KITT: Mic error", err);
        alert("Sistemas: Sensor de voz no disponible.");
    }
}

function animate() {
    const bufferLength = analyzer ? analyzer.frequencyBinCount : 0;
    const dataArray = new Uint8Array(bufferLength);
    
    function update() {
        if (currentMode === 'off') return;
        
        let bands = [0, 0, 0];

        if (currentMode === 'mic' && analyzer) {
            analyzer.getByteFrequencyData(dataArray);
            let rawVolume = getAverage(dataArray, 0, 80);
            let volume = rawVolume < 5 ? 0 : rawVolume * 0.36; 

            bands = [volume * 0.7, volume, volume * 0.7];
        } else if (currentMode === 'music') {
            const time = Date.now() / 1000;
            const pulse = Math.abs(Math.sin(time * 3)) * 9.5; 
            const jitter = Math.random() * 2; 
            const center = pulse + jitter;
            bands = [center * 0.7, center, center * 0.7];
        }

        bands.forEach((val, i) => {
            let level = Math.floor(val);
            if (level > ledsPerColumn) level = ledsPerColumn;

            leds[i].forEach((led, j) => {
                if (Math.abs(j - 9.5) < (level / 2)) {
                    led.classList.add("on");
                } else {
                    led.classList.remove("on");
                }
            });
        });

        animationId = requestAnimationFrame(update);
    }
    update();
}

function getAverage(array, start, end) {
    let sum = 0;
    let count = 0;
    for (let i = start; i < end; i++) {
        if (array[i] > 0) {
            sum += array[i];
            count++;
        }
    }
    return count > 0 ? (sum / count) : 0;
}

// Initializing Listeners
if (btnInit) btnInit.addEventListener('click', initContext);
if (btnMusic) btnMusic.addEventListener('click', startMusic);
if (btnMic) btnMic.addEventListener('click', startMic);
if (btnOff) btnOff.addEventListener('click', stopAll);

// MODOS DE CONDUCCIÓN (Exclusividad: Normal, Auto, Pursuit)
document.addEventListener('click', (e) => {
    const btn = e.target.closest('.normalcruise, .autocruise, .pursuit');
    if (!btn) return;

    // Limpiamos los otros modos
    document.querySelectorAll('.normalcruise, .autocruise, .pursuit').forEach(b => b.classList.remove('active'));
    // Activamos el actual
    btn.classList.add('active');
});

createLeds();