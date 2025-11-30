const int adcPin = A0;
const long sampleRate = 10000;       // 10 kS/s
const long samplePeriod_us = 1000000 / sampleRate; // 100 us
const long duration_ms = 5000;       // 5 seconds
const long totalSamples = sampleRate * 5;

void setup() {
  Serial.begin(115200);
  delay(2000);            // allow Python to open serial
  Serial.println("START"); // signal Python to begin
}

void loop() {
  unsigned long startTime = micros();

  for (long i = 0; i < totalSamples; i++) {
    int value = analogRead(adcPin);
    Serial.println(value);

    // Wait until next sample
    while (micros() - startTime < samplePeriod_us) {}
    startTime += samplePeriod_us;
  }

  Serial.println("END"); // signal Python to stop reading

  while (1); // stop forever
}
