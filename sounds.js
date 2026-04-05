/* ======================================================== */
/* KITT AUDIO ENGINE: DIGITAL PRO SYNTHESIZER (No Mechanical Noise) */
/* ======================================================== */

const KITT_Audio = {
    ctx: null,

    init() {
        if (!this.ctx) {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
            console.log("KITT Digital Core: ONLINE");
        }
    },

    // Generador de tono digital limpio con envolvente ultra-rápida
    createDigitalNode(type, freq, gain, duration, delay = 0) {
        const now = this.ctx.currentTime + delay;
        const osc = this.ctx.createOscillator();
        const g = this.ctx.createGain();
        const filter = this.ctx.createBiquadFilter();

        osc.type = type;
        osc.frequency.setValueAtTime(freq, now);
        
        // Filtro para suavizar y dar ese tono electrónico "premium"
        filter.type = "lowpass";
        filter.frequency.setValueAtTime(freq * 2, now);

        g.gain.setValueAtTime(0, now);
        g.gain.linearRampToValueAtTime(gain, now + 0.005);
        g.gain.exponentialRampToValueAtTime(0.0001, now + duration);

        osc.connect(filter);
        filter.connect(g);
        g.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + duration);
    },

    // 1. DIGITAL PING (Sustituye al clic ruidoso antiguo)
    playClick() {
        this.init();
        if (this.ctx.state === 'suspended') this.ctx.resume();
        
        // Un ping sinusoidal de alta frecuencia, extremadamente limpio y seco
        this.createDigitalNode('sine', 2000, 0.4, 0.05); 
        this.createDigitalNode('sine', 4000, 0.2, 0.03, 0.01); // Armónico digital
    },

    // 2. CONFIRMACIÓN DUAL (Tono rápido y tecnológico)
    playMode() {
        this.init();
        const now = this.ctx.currentTime;
        // Dos pings armónicos casi simultáneos
        this.createDigitalNode('sine', 1200, 0.3, 0.1);
        this.createDigitalNode('sine', 1800, 0.2, 0.08, 0.04);
    },

    // 3. NEURAL BOOT (Secuencia descendente cristalina)
    playInit() {
        this.init();
        const now = this.ctx.currentTime;
        
        // Secuencia de pings de "escaneo de memoria"
        for (let i = 0; i < 6; i++) {
            this.createDigitalNode('triangle', 3000 - (i * 400), 0.2, 0.15, i * 0.06);
        }

        // Hum de fondo digital profundo
        const osc = this.ctx.createOscillator();
        const g = this.ctx.createGain();
        const filter = this.ctx.createBiquadFilter();
        
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(40, now);
        osc.frequency.exponentialRampToValueAtTime(100, now + 1.5);
        
        filter.type = "lowpass";
        filter.frequency.setValueAtTime(200, now);
        filter.Q.value = 10;
        filter.frequency.exponentialRampToValueAtTime(2000, now + 1.5);

        g.gain.setValueAtTime(0, now);
        g.gain.linearRampToValueAtTime(0.3, now + 0.2);
        g.gain.exponentialRampToValueAtTime(0.001, now + 1.5);

        osc.connect(filter);
        filter.connect(g);
        g.connect(this.ctx.destination);
        osc.start(now);
        osc.stop(now + 1.5);
    },

    // 4. POWER COIL (Efecto de carga de energía para PURSUIT)
    playPursuit() {
        this.init();
        const now = this.ctx.currentTime;
        const duration = 0.5;
        
        const osc = this.ctx.createOscillator();
        const g = this.ctx.createGain();
        const filter = this.ctx.createBiquadFilter();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(100, now);
        osc.frequency.exponentialRampToValueAtTime(1200, now + duration);
        
        // Filtro de resonancia que se abre
        filter.type = "lowpass";
        filter.Q.value = 15; // Resonancia metálica digital
        filter.frequency.setValueAtTime(100, now);
        filter.frequency.exponentialRampToValueAtTime(4000, now + duration);

        g.gain.setValueAtTime(0, now);
        g.gain.linearRampToValueAtTime(0.5, now + 0.1);
        g.gain.exponentialRampToValueAtTime(0.001, now + duration);

        osc.connect(filter);
        filter.connect(g);
        g.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + duration);
    }
};

// --- ESCUCHA GLOBAL DE EVENTOS (Delegación de eventos) ---
document.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;

    if (btn.id === 'btn-init') {
        KITT_Audio.playInit();
        return;
    }

    if (['btn-music', 'btn-mic', 'btn-off'].includes(btn.id)) {
        KITT_Audio.playMode();
        return;
    }

    if (btn.classList.contains('pursuit') || btn.classList.contains('turbo')) {
        KITT_Audio.playPursuit();
    } else {
        KITT_Audio.playClick();
    }
});
