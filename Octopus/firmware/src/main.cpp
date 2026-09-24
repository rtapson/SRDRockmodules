#include <Arduino.h>
#include "RelayBank.h"
#include "PresetStore.h"
#include "MidiHandler.h"
#include "SerialConfig.h"

RelayBank relays;
PresetStore presets;
MidiHandler midi(relays, presets);
SerialConfig config(presets);

void setup() {
    Serial.begin(115200);
    relays.begin();
    presets.begin();
    midi.begin();
    config.begin();
}

void loop() {
    midi.update();
    config.update();
}
