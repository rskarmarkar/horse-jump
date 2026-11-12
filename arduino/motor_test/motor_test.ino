/*
  MOTOR TEST — L298N only, no game logic.
  Same pins as horse_jump: ENB=D5, IN3=D7, IN4=D8 (motor on OUT3/OUT4).
  Open Serial Monitor at 9600 and watch what it says.
  Cycle: forward full speed 3 s -> stop 1 s -> backward full 3 s -> stop 1 s
         -> forward at 210 3 s -> stop 1 s -> repeat
*/
const int MOTOR_EN  = 5;
const int MOTOR_IN1 = 7;
const int MOTOR_IN2 = 8;

void drive(int in1, int in2, int pwm, const char *label, unsigned long ms) {
  digitalWrite(MOTOR_IN1, in1);
  digitalWrite(MOTOR_IN2, in2);
  analogWrite(MOTOR_EN, pwm);
  Serial.println(label);
  delay(ms);
}

void setup() {
  Serial.begin(9600);
  pinMode(MOTOR_EN, OUTPUT);
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  Serial.println("MOTOR TEST");
}

void loop() {
  drive(HIGH, LOW, 255, "forward 255", 3000);
  drive(LOW,  LOW, 0,   "stop",        1000);
  drive(LOW,  HIGH, 255, "backward 255", 3000);
  drive(LOW,  LOW, 0,   "stop",        1000);
  drive(HIGH, LOW, 210, "forward 210", 3000);
  drive(LOW,  LOW, 0,   "stop",        1000);
}
