// HORSE JUMP — p5 + ml5 side
// Webcam watches the player. RAISING A HAND (wrist above your nose) sends 'J'
// to the Arduino and the horse jumps. Lower the hand below your shoulders to
// "re-arm" it, then raise again for the next jump. Either hand works.
// Raise BOTH hands above your head for 1 second to start / restart.
// Keyboard backups for testing: SPACE = jump, S = start, D = Arduino debug.
// Open in Chrome (Web Serial only works there) via a local server:
//   cd horse-jump/p5 && python3 -m http.server   → http://localhost:8000

// ---------- tuning ----------
const MIN_CONFIDENCE = 0.3;  // ignore keypoints the model isn't sure about
const COOLDOWN_MS = 500;     // min time between jumps
const HANDS_UP_MS = 1000;    // how long to hold both hands up to start

// ---------- look ----------
const C = {
  bg: '#0f1720', card: '#17212c', card2: '#1e2a37', line: '#2a3846',
  text: '#f3f4f6', muted: '#94a3b8', gold: '#f2c14e', green: '#4ade80',
  red: '#f05252', blue: '#60a5fa',
};
const DISPLAY = 'Fredoka', BODY = 'Inter';

let video, bodyPose, skeleton = [];
let poses = [];
let modelReady = false;

let port, writer;
let serialBuffer = '';
let connected = false;
let connectBtn;

let gameState = 'idle'; // idle | running | crashed
let score = 0;
let best = 0;

// each hand must come back down before it can trigger again
const armed = { left: true, right: true };
let raiseLineY = null;   // nose height (raise wrist above this = jump)
let rearmLineY = null;   // shoulder height (drop wrist below this = re-arm)
let cooldownUntil = 0;
let jumpFlashAt = -9999;
let pointFlashAt = -9999;
let crashAt = -9999;
let handsUpSince = null;
let jumps = 0;

const VW = 640, VH = 480;

function preload() {
  bodyPose = ml5.bodyPose('MoveNet', { flipped: true });
}

function setup() {
  createCanvas(windowWidth, windowHeight);
  video = createCapture(VIDEO, { flipped: true });
  video.size(VW, VH);
  video.hide();
  bodyPose.detectStart(video, (results) => { poses = results; modelReady = true; });
  if (bodyPose.getSkeleton) skeleton = bodyPose.getSkeleton();

  connectBtn = createButton('Connect Arduino');
  connectBtn.addClass('connect');
  connectBtn.mousePressed(async () => {
    await connectSerial();
    if (connected) connectBtn.hide();
  });
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
}

// ---------- pose → hand raise ----------
function kp(pose, name) {
  const k = pose.keypoints.find((k) => k.name === name);
  return k && k.confidence > MIN_CONFIDENCE ? k : null;
}

function detectGestures() {
  if (poses.length === 0) return;
  const p = poses[0];
  const nose = kp(p, 'nose');
  const ls = kp(p, 'left_shoulder');
  const rs = kp(p, 'right_shoulder');
  if (!nose || !ls || !rs) return;

  raiseLineY = nose.y;
  rearmLineY = (ls.y + rs.y) / 2;
  const now = millis();

  const wrists = { left: kp(p, 'left_wrist'), right: kp(p, 'right_wrist') };
  for (const side of ['left', 'right']) {
    const w = wrists[side];
    if (!w || w.y > rearmLineY) {
      armed[side] = true;            // hand is down (or out of frame) → ready
    } else if (armed[side] && w.y < raiseLineY) {
      armed[side] = false;           // hand went up → one jump
      if (now > cooldownUntil) {
        triggerJump();
        cooldownUntil = now + COOLDOWN_MS;
      }
    }
  }

  // both wrists above the nose, held → start gesture
  const handsUp = wrists.left && wrists.right &&
                  wrists.left.y < raiseLineY && wrists.right.y < raiseLineY;
  if (handsUp && gameState !== 'running') {
    if (handsUpSince === null) handsUpSince = now;
    if (now - handsUpSince > HANDS_UP_MS) {
      send('S');
      handsUpSince = null;
    }
  } else {
    handsUpSince = null;
  }
}

function triggerJump() {
  jumpFlashAt = millis();
  jumps++;
  send('J');
}

// ---------- serial (Web Serial, Chrome) ----------
async function connectSerial() {
  if (!('serial' in navigator)) {
    alert('Web Serial needs Chrome or Edge.');
    return;
  }
  try {
    port = await navigator.serial.requestPort();
    await port.open({ baudRate: 9600 });
    writer = port.writable.getWriter();
    connected = true;
    readLoop();
  } catch (e) {
    console.error(e);
    if (e.name !== 'NotFoundError') {
      alert('Could not open the port. Is the Arduino IDE Serial Monitor still open? Close it and try again.');
    }
  }
}

async function readLoop() {
  const decoder = new TextDecoder();
  const reader = port.readable.getReader();
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      serialBuffer += decoder.decode(value);
      let i;
      while ((i = serialBuffer.indexOf('\n')) >= 0) {
        handleLine(serialBuffer.slice(0, i).trim());
        serialBuffer = serialBuffer.slice(i + 1);
      }
    }
  } catch (e) {
    console.error(e);
  }
  connected = false;
  connectBtn.show();
}

function send(s) {
  if (writer) writer.write(new TextEncoder().encode(s));
  else console.log('(not connected) would send', s);
}

function handleLine(line) {
  console.log('Arduino:', line);
  const [cmd, val] = line.split(',');
  if (cmd === 'READY') gameState = 'idle';
  else if (cmd === 'START') { gameState = 'running'; score = 0; }
  else if (cmd === 'SCORE') { score = int(val); pointFlashAt = millis(); best = max(best, score); }
  else if (cmd === 'CRASH') { gameState = 'crashed'; score = int(val); best = max(best, score); crashAt = millis(); }
}

// ---------- drawing helpers ----------
const ease = (t) => 1 - pow(1 - constrain(t, 0, 1), 3);
const since = (t) => millis() - t;

function card(x, y, w, h, fillCol = C.card) {
  noStroke();
  fill(fillCol);
  rect(x, y, w, h, 18);
}

function label(txt, x, y, col = C.muted, size = 13) {
  noStroke();
  fill(col);
  textFont(BODY);
  textStyle(NORMAL);
  textSize(size);
  text(txt.toUpperCase(), x, y);
}

function pill(txt, x, y, col) {
  textFont(BODY);
  textSize(14);
  const w = textWidth(txt) + 40;
  noStroke();
  const c = color(col); c.setAlpha(40);
  fill(c);
  rect(x, y, w, 30, 15);
  fill(col);
  circle(x + 15, y + 15, 8);
  textAlign(LEFT, CENTER);
  text(txt, x + 26, y + 15);
  return w;
}

// ---------- draw ----------
function draw() {
  detectGestures();
  background(C.bg);

  const M = 24, HEADER = 72;
  const wide = width >= 900;

  // header
  textAlign(LEFT, BASELINE);
  noStroke();
  fill(C.text);
  textFont(DISPLAY);
  textSize(30);
  text('Horse Jump', M, 46);
  textFont(BODY);
  textSize(14);
  fill(C.muted);
  text('Raise a hand to jump the fences', M + 175, 44);

  // connection chip
  textAlign(LEFT, CENTER);
  const chipTxt = connected ? 'Arduino connected' : 'Not connected · keyboard: SPACE / S';
  textSize(14);
  const chipW = textWidth(chipTxt) + 40;
  const chipX = connected ? width - M - chipW : width - M - 190 - chipW;
  pill(chipTxt, chipX, 21, connected ? C.green : C.muted);

  // layout
  let cx, cy, cw, ch, px, py, pw, ph;
  if (wide) {
    const pwTarget = constrain(width * 0.28, 280, 380);
    cw = min(width - pwTarget - 3 * M, (height - HEADER - 2 * M) * VW / VH);
    ch = cw * VH / VW;
    cx = M; cy = HEADER + (height - HEADER - M - ch) / 2;
    px = cx + cw + M; py = cy; pw = width - px - M; ph = ch;
  } else {
    cw = width - 2 * M; ch = cw * VH / VW;
    cx = M; cy = HEADER;
    px = M; py = cy + ch + 16; pw = cw; ph = height - py - M;
  }

  drawCamera(cx, cy, cw, ch);
  drawPanel(px, py, pw, ph, wide);
}

function drawCamera(x, y, w, h) {
  const s = w / VW;
  const ctx = drawingContext;

  // rounded video
  ctx.save();
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 22);
  ctx.clip();
  background(C.card);
  if (video.loadedmetadata) {
    image(video, x, y, w, h);
    noStroke();
    fill(15, 23, 32, 70);          // slight dim so the overlays pop
    rect(x, y, w, h);
  }

  // guide lines
  if (raiseLineY !== null) {
    const ry = y + raiseLineY * s, ay = y + rearmLineY * s;
    strokeWeight(2);
    drawingContext.setLineDash([10, 8]);
    stroke(74, 222, 128, 220);
    line(x, ry, x + w, ry);
    stroke(255, 255, 255, 110);
    line(x, ay, x + w, ay);
    drawingContext.setLineDash([]);
    tag('Raise above → jump', x + w - 14, ry, C.green);
    tag('Lower below → ready', x + w - 14, ay, '#cbd5e1');
  }

  // skeleton + keypoints
  if (poses.length) {
    const kps = poses[0].keypoints;
    stroke(242, 193, 78, 160);
    strokeWeight(3);
    for (const [a, b] of skeleton) {
      const ka = kps[a], kb = kps[b];
      if (ka && kb && ka.confidence > MIN_CONFIDENCE && kb.confidence > MIN_CONFIDENCE) {
        line(x + ka.x * s, y + ka.y * s, x + kb.x * s, y + kb.y * s);
      }
    }
    noStroke();
    for (const k of kps) {
      if (k.confidence <= MIN_CONFIDENCE) continue;
      if (k.name.endsWith('wrist')) {
        const side = k.name.startsWith('left') ? 'left' : 'right';
        fill(armed[side] ? C.green : C.gold);
        circle(x + k.x * s, y + k.y * s, 26);
        fill(C.bg);
        circle(x + k.x * s, y + k.y * s, 10);
      } else {
        fill(C.gold);
        circle(x + k.x * s, y + k.y * s, 9);
      }
    }
  }

  // jump flash: green frame + "JUMP!"
  const jt = since(jumpFlashAt);
  if (jt < 450) {
    const a = 1 - jt / 450;
    noFill();
    stroke(74, 222, 128, 255 * a);
    strokeWeight(10);
    rect(x + 5, y + 5, w - 10, h - 10, 18);
    noStroke();
    fill(74, 222, 128, 255 * a);
    textFont(DISPLAY);
    textAlign(CENTER, CENTER);
    textSize(54 + 20 * ease(jt / 200));
    text('Jump!', x + w / 2, y + 70 - 20 * ease(jt / 450));
  }

  // state overlays
  if (!video.loadedmetadata) {
    centerMsg(x, y, w, h, 'Waiting for the camera…', 'Allow camera access in the browser bar');
  } else if (!modelReady) {
    centerMsg(x, y, w, h, 'Loading the pose model…', 'This takes a few seconds the first time');
  } else if (poses.length === 0) {
    banner(x, y, w, h, 'Step back so your head, shoulders and hands are in view', C.card2);
  } else if (gameState === 'crashed') {
    const t = ease(since(crashAt) / 300);
    noStroke();
    fill(120, 20, 20, 150 * t);
    rect(x, y, w, h);
    textAlign(CENTER, CENTER);
    fill(C.text);
    textFont(DISPLAY);
    textSize(76 * (0.8 + 0.2 * t));
    text('Crash!', x + w / 2, y + h / 2 - 40);
    textFont(BODY);
    textSize(20);
    fill('#fecaca');
    text(`You cleared ${score} fence${score === 1 ? '' : 's'}`, x + w / 2, y + h / 2 + 22);
    banner(x, y, w, h, 'Raise both hands to ride again', C.red);
  } else if (gameState === 'idle') {
    banner(x, y, w, h, connected ? 'Raise both hands to start' : 'Connect the Arduino to start', C.card2);
  }

  // start ring (hold both hands up)
  if (handsUpSince !== null) {
    const pct = constrain(since(handsUpSince) / HANDS_UP_MS, 0, 1);
    const r = 110;
    noStroke();
    fill(15, 23, 32, 170);
    circle(x + w / 2, y + h / 2, r * 2 + 30);
    noFill();
    strokeWeight(12);
    stroke(255, 255, 255, 40);
    circle(x + w / 2, y + h / 2, r * 2);
    stroke(C.gold);
    strokeCap(ROUND);
    arc(x + w / 2, y + h / 2, r * 2, r * 2, -HALF_PI, -HALF_PI + TWO_PI * pct);
    noStroke();
    fill(C.text);
    textAlign(CENTER, CENTER);
    textFont(DISPLAY);
    textSize(34);
    text(gameState === 'crashed' ? 'Again!' : 'Hold…', x + w / 2, y + h / 2);
  }
  ctx.restore();
}

function tag(txt, rx, cy, col) {
  textFont(BODY);
  textSize(12);
  const w = textWidth(txt) + 16;
  noStroke();
  fill(15, 23, 32, 200);
  rect(rx - w, cy - 24, w, 20, 6);
  fill(col);
  textAlign(LEFT, CENTER);
  text(txt, rx - w + 8, cy - 14);
}

function banner(x, y, w, h, txt, col) {
  textFont(BODY);
  textSize(17);
  const bw = textWidth(txt) + 44;
  noStroke();
  fill(col);
  rect(x + (w - bw) / 2, y + h - 64, bw, 42, 21);
  fill(C.text);
  textAlign(CENTER, CENTER);
  text(txt, x + w / 2, y + h - 43);
}

function centerMsg(x, y, w, h, title, sub) {
  noStroke();
  fill(C.text);
  textAlign(CENTER, CENTER);
  textFont(DISPLAY);
  textSize(28);
  text(title, x + w / 2, y + h / 2 - 14);
  fill(C.muted);
  textFont(BODY);
  textSize(15);
  text(sub, x + w / 2, y + h / 2 + 22);
}

function drawPanel(x, y, w, h, wide) {
  const G = 16;
  textAlign(LEFT, BASELINE);

  // score card
  const scoreH = wide ? min(250, h * 0.45) : 150;
  card(x, y, w, scoreH);
  label('Score', x + 24, y + 36);
  const pop = since(pointFlashAt) < 350 ? 1 + 0.25 * (1 - since(pointFlashAt) / 350) : 1;
  textFont(DISPLAY);
  textSize((wide ? 120 : 80) * pop);
  fill(since(pointFlashAt) < 600 ? C.green : C.text);
  textAlign(LEFT, BASELINE);
  text(score, x + 22, y + (wide ? 160 : 118));
  textFont(BODY);
  textSize(15);
  fill(C.muted);
  textAlign(RIGHT, BASELINE);
  text(`Best  ${best}`, x + w - 24, y + 36);
  const st = { idle: ['Ready', C.blue], running: ['Riding', C.green], crashed: ['Crashed', C.red] }[gameState];
  pill(st[0], x + 22, y + scoreH - 50, st[1]);

  if (!wide) return;

  // hands card
  let yy = y + scoreH + G;
  const handsH = 140;
  card(x, yy, w, handsH);
  label('Your hands', x + 24, yy + 34);
  const hw = (w - 24 * 2 - 12) / 2;
  ['left', 'right'].forEach((side, i) => {
    const hx = x + 24 + i * (hw + 12), hy = yy + 52;
    noStroke();
    fill(C.card2);
    rect(hx, hy, hw, 64, 14);
    fill(armed[side] ? C.green : C.gold);
    circle(hx + 26, hy + 32, 16);
    fill(C.text);
    textFont(BODY);
    textSize(15);
    textAlign(LEFT, CENTER);
    text(side === 'left' ? 'Left' : 'Right', hx + 44, hy + 23);
    fill(C.muted);
    textSize(13);
    text(armed[side] ? 'Ready' : 'Lower to reset', hx + 44, hy + 43);
  });

  // how to play
  yy += handsH + G;
  const howH = y + h - yy;
  if (howH < 120) return;
  card(x, yy, w, howH);
  label('How to play', x + 24, yy + 34);
  const steps = [
    ['Both hands up', 'Hold for 1 second to start'],
    ['One hand up', 'The horse jumps'],
    ['Hand back down', 'Get ready for the next fence'],
  ];
  steps.forEach(([a, b], i) => {
    const sy = yy + 64 + i * 50;
    if (sy + 30 > yy + howH) return;
    noStroke();
    fill(C.card2);
    circle(x + 38, sy + 8, 28);
    fill(C.gold);
    textFont(DISPLAY);
    textSize(16);
    textAlign(CENTER, CENTER);
    text(i + 1, x + 38, sy + 7);
    textAlign(LEFT, CENTER);
    textFont(BODY);
    fill(C.text);
    textSize(15);
    text(a, x + 64, sy);
    fill(C.muted);
    textSize(13);
    text(b, x + 64, sy + 19);
  });
}

function keyPressed() {
  if (key === ' ') triggerJump();
  if (key === 's' || key === 'S') send('S');
  if (key === 'd' || key === 'D') send('D');
}
