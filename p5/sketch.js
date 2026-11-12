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

let video, bodyPose;
let poses = [];

let port, writer;
let serialBuffer = '';
let connected = false;

let gameState = 'idle'; // idle | running | crashed
let score = 0;
let best = 0;

// each hand must come back down before it can trigger again
const armed = { left: true, right: true };
let raiseLineY = null;   // nose height (raise wrist above this = jump)
let rearmLineY = null;   // shoulder height (drop wrist below this = re-arm)
let cooldownUntil = 0;
let jumpFlashUntil = 0;
let pointFlashUntil = 0;
let handsUpSince = null;

const VW = 640, VH = 480;

function preload() {
  bodyPose = ml5.bodyPose('MoveNet', { flipped: true });
}

function setup() {
  createCanvas(windowWidth, windowHeight);
  video = createCapture(VIDEO, { flipped: true });
  video.size(VW, VH);
  video.hide();
  bodyPose.detectStart(video, (results) => (poses = results));

  const btn = createButton('Connect Arduino');
  btn.mousePressed(async () => {
    await connectSerial();
    if (connected) btn.hide();
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
  jumpFlashUntil = millis() + 250;
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
    alert('Could not open the port. Is the Arduino IDE Serial Monitor still open? Close it and try again.');
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
    connected = false;
  }
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
  else if (cmd === 'SCORE') { score = int(val); pointFlashUntil = millis() + 300; }
  else if (cmd === 'CRASH') { gameState = 'crashed'; score = int(val); best = max(best, score); }
}

// ---------- draw ----------
function draw() {
  detectGestures();
  background(17);

  // camera, fit to the left 2/3 of the screen
  const vw = width * 0.66;
  const vh = vw * (VH / VW);
  const vy = (height - vh) / 2;
  const sx = vw / VW;
  image(video, 0, vy, vw, vh);

  // pose dots (wrists drawn bigger)
  if (poses.length) {
    noStroke();
    for (const k of poses[0].keypoints) {
      if (k.confidence <= MIN_CONFIDENCE) continue;
      const isWrist = k.name.endsWith('wrist');
      fill(isWrist ? color(80, 220, 120) : color(242, 193, 78));
      circle(k.x * sx, vy + k.y * sx, isWrist ? 22 : 10);
    }
  }

  // green = raise wrist above this to jump; white = lower below this to re-arm
  if (raiseLineY !== null) {
    strokeWeight(2);
    stroke(80, 220, 120, 200);
    line(0, vy + raiseLineY * sx, vw, vy + raiseLineY * sx);
    stroke(255, 255, 255, 110);
    line(0, vy + rearmLineY * sx, vw, vy + rearmLineY * sx);
    noStroke();
    textSize(14);
    fill(80, 220, 120);
    textAlign(LEFT, BOTTOM);
    text('raise wrist above → JUMP', 8, vy + raiseLineY * sx - 4);
    fill(255, 255, 255, 160);
    text('drop below → re-arm', 8, vy + rearmLineY * sx - 4);
  }

  // flashes
  noStroke();
  if (millis() < jumpFlashUntil) { fill(80, 220, 120, 70); rect(0, vy, vw, vh); }
  if (gameState === 'crashed' && floor(millis() / 200) % 2 === 0) {
    fill(230, 40, 40, 90);
    rect(0, 0, width, height);
  }

  // score panel
  const px = vw + 30;
  fill(255);
  textAlign(LEFT, TOP);
  textSize(22);
  text('SCORE', px, 60);
  textSize(millis() < pointFlashUntil ? 150 : 130);
  fill(millis() < pointFlashUntil ? color(80, 220, 120) : 255);
  text(score, px, 90);
  fill(180);
  textSize(22);
  text('BEST  ' + best, px, 260);

  textSize(20);
  fill(255);
  let msg = '';
  if (!connected) msg = 'Click "Connect Arduino"\n(SPACE / S to test)';
  else if (gameState === 'idle') msg = 'Raise both hands\nto start';
  else if (gameState === 'running') msg = 'RAISE A HAND\nto jump the fences!';
  else msg = 'CRASH!\nBoth hands up to try again';
  text(msg, px, 330);

  // hand-ready indicators
  textSize(16);
  fill(armed.left ? color(80, 220, 120) : 90);
  text('● left hand ready', px, 410);
  fill(armed.right ? color(80, 220, 120) : 90);
  text('● right hand ready', px, 434);

  if (handsUpSince !== null) {
    const pct = constrain((millis() - handsUpSince) / HANDS_UP_MS, 0, 1);
    fill(60);
    rect(px, 470, 200, 14, 7);
    fill(242, 193, 78);
    rect(px, 470, 200 * pct, 14, 7);
  }
}

function keyPressed() {
  if (key === ' ') triggerJump();
  if (key === 's' || key === 'S') send('S');
  if (key === 'd' || key === 'D') send('D');
}
