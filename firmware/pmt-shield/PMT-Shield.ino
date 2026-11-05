#include <SPI.h>

const int CS_PIN = 10;
const float DAC_FULL_SCALE = 4.096f;  // MCP4821 full-scale voltage

// Convert desired voltage (0 to 1 V) into DAC code
uint16_t voltageToCode(float volts) {
  // Clamp to 0–1 V range
  if (volts < 0.0f) volts = 0.0f;
  if (volts > 1.0f) volts = 1.0f;

  // Map 0–1 V into 0–4095 range, based on 4.096 V full-scale
  float ratio = volts / DAC_FULL_SCALE;       // 0–1/4.096
  uint16_t code = (uint16_t)(ratio * 4095.0f + 0.5f);  // round to nearest
  return code;
}

// Send a 12-bit code to the MCP4821
void writeDAC(uint16_t code) {
  // Build 16-bit command:
  // [C1 C0 GA SHDN D11 ... D0]
  // C1=0, C0=0
  // GA=0 (gain=2x -> 0–4.096 V range)
  // SHDN=1 (active)
  uint16_t command = 0;
  command |= (0 << 15);          // C1
  command |= (0 << 14);          // C0
  command |= (0 << 13);          // GA = 0 (2x gain, full 4.096 V)
  command |= (1 << 12);          // SHDN = 1 (active)
  command |= (code & 0x0FFF);    // 12-bit DAC code

  digitalWrite(CS_PIN, LOW);
  SPI.transfer(command >> 8);    // upper 8 bits
  SPI.transfer(command & 0xFF);  // lower 8 bits
  digitalWrite(CS_PIN, HIGH);
}

void setup() {
  // Serial for user interface
  Serial.begin(115200);
  while (!Serial) {
    ; // wait for Serial on some boards (ok on Uno too)
  }

  Serial.println(F("MCP4821 0–1 V controller"));
  Serial.println(F("Type a voltage between 0.000 and 1.000 and press Enter."));
  Serial.println(F("Example: 0.250"));

  // SPI + DAC setup
  SPI.begin();
  pinMode(CS_PIN, OUTPUT);
  digitalWrite(CS_PIN, HIGH);    // deselect DAC

  // Start at 0 V
  writeDAC(0);
}

void loop() {
  if (Serial.available() > 0) {
    // Read a float from serial input
    float requested = Serial.parseFloat();

    // Clear rest of the line (up to newline)
    while (Serial.available() > 0) {
      char c = Serial.read();
      if (c == '\n' || c == '\r') break;
    }

    // Basic sanity check
    if (requested < 0.0f || requested > 1.2f) {
      Serial.println(F("Please enter a value between 0.000 and 1.000 V."));
      return;
    }

    // Clamp strictly to 0–1 V
    if (requested < 0.0f) requested = 0.0f;
    if (requested > 1.0f) requested = 1.0f;

    uint16_t code = voltageToCode(requested);
    writeDAC(code);

    // Compute the ideal analog output based on code (for info)
    float actual = (code / 4095.0f) * DAC_FULL_SCALE;

    Serial.print(F("Requested: "));
    Serial.print(requested, 4);
    Serial.print(F(" V, DAC code = "));
    Serial.print(code);
    Serial.print(F(", ideal output ≈ "));
    Serial.print(actual, 4);
    Serial.println(F(" V"));
  }
}