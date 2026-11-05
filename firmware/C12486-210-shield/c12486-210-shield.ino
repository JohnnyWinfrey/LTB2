#include <SPI.h>

const int CS_PIN = 10;
const int TEMP_PIN = A0;          // analog pin carrying the temperature-sensor voltage

// Assumed reference for analogRead (5 V on a standard Uno/Nano)
const float ADC_VREF = 5.0f;

// MCP4821 with GA=0 (2x gain) and the 2.048 V internal VREF:
//   VOUT = 2 * 2.048 * D/4096  ->  1 mV per LSB, 0-4.096 V range
// 2.500 V -> DAC code 2500
const uint16_t OUTPUT_CODE = 2500;

// How often the A0 input voltage is printed to serial
const unsigned long PRINT_INTERVAL_MS = 500;

// Average a few ADC samples for a steadier reading
float readInputVolts() {
  uint32_t sum = 0;
  const uint8_t samples = 8;
  for (uint8_t i = 0; i < samples; i++) {
    sum += analogRead(TEMP_PIN);
  }
  return (sum / (float)samples) * ADC_VREF / 1023.0f;
}

// Send a 12-bit code to the MCP4821
void writeDAC(uint16_t code) {
  // Build 16-bit command:
  // [C1 C0 GA SHDN D11 ... D0]
  // C1=0, C0=0
  // GA=0 (gain=2x -> 0-4.096 V range)
  // SHDN=1 (active)
  uint16_t command = 0;
  command |= (0 << 15);          // C1
  command |= (0 << 14);          // C0
  command |= (0 << 13);          // GA = 0 (2x gain)
  command |= (1 << 12);          // SHDN = 1 (active)
  command |= (code & 0x0FFF);    // 12-bit DAC code

  digitalWrite(CS_PIN, LOW);
  SPI.transfer(command >> 8);    // upper 8 bits
  SPI.transfer(command & 0xFF);  // lower 8 bits
  digitalWrite(CS_PIN, HIGH);
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // wait for the serial port to connect (no-op on Uno)
  }
  Serial.println(F("C12486-210-Shield"));

  // SPI + DAC setup
  SPI.begin();
  pinMode(CS_PIN, OUTPUT);
  digitalWrite(CS_PIN, HIGH);    // deselect DAC

  // Set the static 2.500 V output
  writeDAC(OUTPUT_CODE);

  pinMode(TEMP_PIN, INPUT);
}

void loop() {
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint < PRINT_INTERVAL_MS) return;
  lastPrint = millis();

  // Voltage on the A0 input, e.g. "1.710 V"
  Serial.print(readInputVolts(), 3);
  Serial.println(F(" V"));
}
