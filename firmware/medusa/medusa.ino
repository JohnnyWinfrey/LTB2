// Medusa -- five steppers on one Arduino Mega (replaces the two DeathStars).
//
// Talks a line-based ASCII protocol at 115200 baud, newline terminated.
// Every command gets exactly one reply line: "ok", "error: ...", or (for ?)
// the status line. Motion is non-blocking: a MOVE replies "ok" right away and
// the host polls ? until it reads "Idle". Commands are case-insensitive, so
// the serial monitor works for poking at it by hand.
//
//   MOVE <axis> <pos> [<axis> <pos> ...]   absolute move, all axes start together
//   JOG <axis> <delta>                     relative move (stacks onto a move in progress)
//   HOME [axis]                            move to 0 (every axis if none given)
//   ZERO [axis]                            call the current position 0 (must be stopped)
//   SPEED <axis> <units/s>                 max speed
//   ACCEL <axis> <units/s^2>               acceleration
//   STOP                                   decelerate every axis to a halt
//   ?                                      "Idle|Run GP=.. GW=.. X=.. AW=.. AP=.."
//
// Axes (units: deg for rotary, mm for the xwing):
//   GP  PSG polarizer   PUL 2,  DIR 3
//   GW  PSG waveplate   PUL 4,  DIR 5
//   X   xwing (linear)  PUL 6,  DIR 7
//   AW  PSA waveplate   PUL 8,  DIR 9
//   AP  PSA polarizer   PUL 10, DIR 11

#include <AccelStepper.h>

const long PPR = 4000;                        // match each driver's microstep switches
const float STEPS_PER_DEG = PPR / 200.0;      // 1 full step = 1 deg of stage rotation
const float XWING_MM_PER_REV = 0.025 * 25.4;  // 0.025" lead screw = 0.635 mm/rev
const float XWING_STEPS_PER_MM = PPR / XWING_MM_PER_REV;   // ~6299

const int NUM_AXES = 5;
const int LINE_MAX = 96;

struct Axis {
  const char *name;
  AccelStepper stepper;
  float stepsPerUnit;
  float speed;        // units/s
  float accel;        // units/s^2
  bool invertDir;     // flip if the stage turns the wrong way
};

Axis axes[NUM_AXES] = {
  { "GP", AccelStepper(AccelStepper::DRIVER, 2, 3),   STEPS_PER_DEG,      30,  60,  false },
  { "GW", AccelStepper(AccelStepper::DRIVER, 4, 5),   STEPS_PER_DEG,      30,  60,  false },
  // xwing kept slow: 0.2 mm/s is ~1260 steps/s, and the Mega tops out near
  // 4000 steps/s summed over every axis moving at once.
  { "X",  AccelStepper(AccelStepper::DRIVER, 6, 7),   XWING_STEPS_PER_MM, 0.2, 0.5, false },
  { "AW", AccelStepper(AccelStepper::DRIVER, 8, 9),   STEPS_PER_DEG,      30,  60,  false },
  { "AP", AccelStepper(AccelStepper::DRIVER, 10, 11), STEPS_PER_DEG,      30,  60,  false },
};

char line[LINE_MAX];
int lineLen = 0;
bool lineOverflow = false;

// ── helpers ─────────────────────────────────────────────────────────────────

Axis *findAxis(const char *name) {
  if (!name) return NULL;
  for (int i = 0; i < NUM_AXES; i++)
    if (strcasecmp(name, axes[i].name) == 0) return &axes[i];
  return NULL;
}

bool parseNumber(const char *tok, float &out) {
  if (!tok) return false;
  char *end;
  out = strtod(tok, &end);
  return end != tok && *end == '\0';
}

long toSteps(Axis &a, float units) { return lround(units * a.stepsPerUnit); }
float toUnits(Axis &a, long steps) { return steps / a.stepsPerUnit; }

void applyMotion(Axis &a) {
  a.stepper.setMaxSpeed(a.speed * a.stepsPerUnit);
  a.stepper.setAcceleration(a.accel * a.stepsPerUnit);
}

bool anyRunning() {
  for (int i = 0; i < NUM_AXES; i++)
    if (axes[i].stepper.isRunning()) return true;
  return false;
}

void error(const char *msg) {
  Serial.print(F("error: "));
  Serial.println(msg);
}

// ── commands ────────────────────────────────────────────────────────────────

void cmdMove() {
  // Validate every pair before moving anything, so a typo never half-moves.
  Axis *targets[NUM_AXES];
  float values[NUM_AXES];
  int n = 0;
  char *name;
  while ((name = strtok(NULL, " ")) != NULL) {
    Axis *a = findAxis(name);
    if (!a) return error("unknown axis");
    if (n == NUM_AXES) return error("too many axes");
    if (!parseNumber(strtok(NULL, " "), values[n])) return error("bad number");
    targets[n++] = a;
  }
  if (n == 0) return error("MOVE needs <axis> <pos>");
  for (int i = 0; i < n; i++) targets[i]->stepper.moveTo(toSteps(*targets[i], values[i]));
  Serial.println(F("ok"));
}

void cmdJog() {
  Axis *a = findAxis(strtok(NULL, " "));
  float delta;
  if (!a) return error("unknown axis");
  if (!parseNumber(strtok(NULL, " "), delta)) return error("bad number");
  a->stepper.moveTo(a->stepper.targetPosition() + toSteps(*a, delta));
  Serial.println(F("ok"));
}

void cmdHome() {
  char *name = strtok(NULL, " ");
  if (name) {
    Axis *a = findAxis(name);
    if (!a) return error("unknown axis");
    a->stepper.moveTo(0);
  } else {
    for (int i = 0; i < NUM_AXES; i++) axes[i].stepper.moveTo(0);
  }
  Serial.println(F("ok"));
}

void cmdZero() {
  char *name = strtok(NULL, " ");
  if (name) {
    Axis *a = findAxis(name);
    if (!a) return error("unknown axis");
    if (a->stepper.isRunning()) return error("axis is moving");
    a->stepper.setCurrentPosition(0);
  } else {
    if (anyRunning()) return error("axes are moving");
    for (int i = 0; i < NUM_AXES; i++) axes[i].stepper.setCurrentPosition(0);
  }
  Serial.println(F("ok"));
}

void cmdSpeedOrAccel(bool isSpeed) {
  Axis *a = findAxis(strtok(NULL, " "));
  float v;
  if (!a) return error("unknown axis");
  if (!parseNumber(strtok(NULL, " "), v) || v <= 0) return error("bad number");
  if (isSpeed) a->speed = v; else a->accel = v;
  applyMotion(*a);
  Serial.println(F("ok"));
}

void cmdStop() {
  for (int i = 0; i < NUM_AXES; i++) axes[i].stepper.stop();
  Serial.println(F("ok"));
}

void cmdStatus() {
  Serial.print(anyRunning() ? F("Run") : F("Idle"));
  for (int i = 0; i < NUM_AXES; i++) {
    Serial.print(' ');
    Serial.print(axes[i].name);
    Serial.print('=');
    Serial.print(toUnits(axes[i], axes[i].stepper.currentPosition()), 3);
  }
  Serial.println();
}

void handleLine(char *s) {
  char *cmd = strtok(s, " ");
  if (!cmd) return;                                   // blank line: no reply
  if      (strcmp(cmd, "?") == 0)             cmdStatus();
  else if (strcasecmp(cmd, "MOVE") == 0)      cmdMove();
  else if (strcasecmp(cmd, "JOG") == 0)       cmdJog();
  else if (strcasecmp(cmd, "HOME") == 0)      cmdHome();
  else if (strcasecmp(cmd, "ZERO") == 0)      cmdZero();
  else if (strcasecmp(cmd, "SPEED") == 0)     cmdSpeedOrAccel(true);
  else if (strcasecmp(cmd, "ACCEL") == 0)     cmdSpeedOrAccel(false);
  else if (strcasecmp(cmd, "STOP") == 0)      cmdStop();
  else error("unknown command");
}

// Collect serial bytes without blocking, so the steppers keep running.
void pollSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      line[lineLen] = '\0';
      if (lineOverflow) error("line too long");
      else handleLine(line);
      lineLen = 0;
      lineOverflow = false;
    } else if (lineLen < LINE_MAX - 1) {
      line[lineLen++] = c;
    } else {
      lineOverflow = true;
    }
  }
}

// ── main ────────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < NUM_AXES; i++) {
    AccelStepper &s = axes[i].stepper;
    s.setMinPulseWidth(5);
    s.setPinsInverted(axes[i].invertDir, false, false);
    applyMotion(axes[i]);
  }
  Serial.println(F("Medusa ready"));
}

void loop() {
  for (int i = 0; i < NUM_AXES; i++) axes[i].stepper.run();
  pollSerial();
}
