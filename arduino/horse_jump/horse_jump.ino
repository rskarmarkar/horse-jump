/*
  HORSE JUMP — Arduino side
  ------------------------------------------------------------
  p5 (webcam) detects the player raising a hand and sends 'J' over serial.
  The servo lifts the horse. A belt (DC motor) carries jumps under it.
  An LED + LDR "break-beam" sits right under the horse: when a jump
  post breaks the beam, we check if the horse is in the air.
    in the air  -> point
    on the ground -> CRASH: belt brakes, red LEDs flash

  Serial IN  (from p5):  'J' = jump   'S' = start/restart   'D' = toggle debug
  Serial OUT (to p5):    READY | START | SCORE,<n> | CRASH,<n>

  WIRING (Uno R3)
  ------------------------------------------------------------
  Servo signal ............ D9   (servo + to 5V, - to GND)
  L298N ENB ............... D5   (REMOVE the ENB jumper cap first)
  L298N IN3 ............... D7
  L298N IN4 ............... D8
  L298N OUT3/OUT4 ......... DC motor  (motor uses the B side of the driver)
  L298N +12V/VIN .......... 9V supply +   (keep the 5V-EN jumper ON, leave the 5V terminal empty)
  L298N GND ............... supply - AND Arduino GND (common ground!)
  Beam LED ................ D4 -> 220Ω -> LED -> GND (points at the LDR)
  LDR ..................... 5V -> LDR -> A0 -> 10kΩ -> GND
  Red LEDs (x2, parallel).. D11 -> 220Ω each -> LED -> GND
  Green LED ............... D12 -> 220Ω -> LED -> GND
  Start button ............ D2 -> button -> GND (uses INPUT_PULLUP)
  Put a 100–470µF capacitor across servo 5V/GND if the Arduino resets
  when the horse jumps.
*/

#include <Servo.h>

// ---------- pins ----------
const int SERVO_PIN     = 9;
const int MOTOR_EN      = 5;   // -> L298N ENB
const int MOTOR_IN1     = 7;   // -> L298N IN3
const int MOTOR_IN2     = 8;   // -> L298N IN4
const int LDR_PIN       = A0;
const int BEAM_LED_PIN  = 4;
const int RED_LED_PIN   = 11;
const int GREEN_LED_PIN = 12;
const int BUTTON_PIN    = 2;

// ---------- tuning (change these while testing) ----------
const int HORSE_REST = 13;            // servo angle with horse on the ground. Below ~13 the axle hits the slot end and the servo stalls
const int HORSE_UP   = 45;            // servo angle with horse in the air
const bool SERVO_REVERSED = true;     // true = servo turns the other way (horse went DOWN on a jump). Flip if wrong.
const unsigned long LIFT_TIME = 120;  // ms until horse is high enough to clear a post
const unsigned long AIR_TIME  = 650;  // ms the horse stays up

const int SPEED_START = 255;          // belt PWM (0–255). 255 = full speed always
const int SPEED_STEP  = 0;            // added per point
const int SPEED_MAX   = 255;

const float BLOCK_RATIO = 0.70;       // beam "blocked" below 70% of baseline light
const float CLEAR_RATIO = 0.85;       // beam "clear" again above 85%

// ---------- state ----------
enum State { IDLE, RUNNING, CRASHED };
State state = IDLE;

Servo horse;
int score = 0;
int beltSpeed = SPEED_START;

bool jumping = false;
unsigned long jumpStart = 0;

float baseline = 0;
bool beamBlocked = false;

unsigned long greenUntil = 0;
unsigned long lastButton = 0;
unsigned long lastDebug = 0;
bool debug = false;

// ---------- motor ----------
void motorRun(int pwm) {
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  analogWrite(MOTOR_EN, pwm);
}

void motorBrake() {              // both inputs HIGH = active brake on L298N
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, HIGH);
  analogWrite(MOTOR_EN, 255);
}

void motorOff() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  analogWrite(MOTOR_EN, 0);
}

// ---------- horse ----------
void horseWrite(int a) {          // all servo moves go through here so the direction can be flipped
  horse.write(SERVO_REVERSED ? 180 - a : a);
}

void startJump() {
  if (jumping || state == CRASHED) return;
  jumping = true;
  jumpStart = millis();
  horseWrite(HORSE_UP);
}

void updateJump() {
  if (jumping && millis() - jumpStart > LIFT_TIME + AIR_TIME) {
    horseWrite(HORSE_REST);
    jumping = false;
  }
}

bool horseInAir() {
  return jumping && (millis() - jumpStart >= LIFT_TIME);
}

// ---------- beam (LED + LDR) ----------
void calibrateBeam() {
  long sum = 0;
  for (int i = 0; i < 50; i++) {
    sum += analogRead(LDR_PIN);
    delay(10);
  }
  baseline = sum / 50.0;
  beamBlocked = false;
}

// returns true once, at the moment a post enters the beam
bool postArrived() {
  int v = analogRead(LDR_PIN);

  if (!beamBlocked && v < baseline * BLOCK_RATIO) {
    beamBlocked = true;
    return true;
  }
  if (beamBlocked && v > baseline * CLEAR_RATIO) {
    beamBlocked = false;
  }
  // slowly follow room-light changes while the beam is clear
  if (!beamBlocked) baseline += (v - baseline) * 0.002;

  if (debug && millis() - lastDebug > 100) {
    lastDebug = millis();
    Serial.print("LDR,"); Serial.print(v);
    Serial.print(",base,"); Serial.println((int)baseline);
  }
  return false;
}

// ---------- game ----------
void startGame() {
  digitalWrite(RED_LED_PIN, LOW);
  horseWrite(HORSE_REST);
  jumping = false;
  score = 0;
  beltSpeed = SPEED_START;
  calibrateBeam();           // belt is stopped here, so the beam should be clear
  motorRun(255);             // kick to overcome the gearbox's stiction
  delay(300);
  motorRun(beltSpeed);
  state = RUNNING;
  Serial.println("START");
}

void crash() {
  motorBrake();
  state = CRASHED;
  Serial.print("CRASH,"); Serial.println(score);
}

void addPoint() {
  score++;
  beltSpeed = min(beltSpeed + SPEED_STEP, SPEED_MAX);
  motorRun(beltSpeed);
  greenUntil = millis() + 250;
  Serial.print("SCORE,"); Serial.println(score);
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'J') startJump();
    else if (c == 'S' && state != RUNNING) startGame();
    else if (c == 'D') debug = !debug;
  }
}

void readButton() {
  if (digitalRead(BUTTON_PIN) == LOW && millis() - lastButton > 400) {
    lastButton = millis();
    if (state != RUNNING) startGame();
  }
}

void updateLeds() {
  unsigned long t = millis();
  if (state == CRASHED) {
    digitalWrite(RED_LED_PIN, (t / 150) % 2);     // fast flash
    digitalWrite(GREEN_LED_PIN, LOW);
  } else if (state == IDLE) {
    digitalWrite(RED_LED_PIN, LOW);
    digitalWrite(GREEN_LED_PIN, (t / 600) % 2);   // slow "ready" blink
  } else {
    digitalWrite(RED_LED_PIN, LOW);
    digitalWrite(GREEN_LED_PIN, t < greenUntil);  // blip on each point
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(MOTOR_EN, OUTPUT);
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(BEAM_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  digitalWrite(BEAM_LED_PIN, HIGH);
  motorOff();
  horse.attach(SERVO_PIN);
  horseWrite(HORSE_REST);
  calibrateBeam();
  Serial.println("READY");
}

void loop() {
  readSerial();
  readButton();
  updateJump();

  bool arrived = postArrived();
  if (state == RUNNING && arrived) {
    if (horseInAir()) addPoint();
    else crash();
  }

  updateLeds();
}
