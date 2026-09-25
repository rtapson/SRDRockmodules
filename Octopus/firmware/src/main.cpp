#include <Arduino.h>
#include "RelayBank.h"
#include "PresetStore.h"
#include "MidiHandler.h"
#include "SerialConfig.h"
#include "Panel.h"

RelayBank relays;
PresetStore presets;
MidiHandler midi(relays, presets);
SerialConfig config(presets);
Panel panel(relays, presets, midi);

void setup() {
    Serial.begin(115200);
    relays.begin();
    presets.begin();
    midi.begin();
    config.begin();
    panel.begin();
}

void loop() {
    midi.update();
    config.update();
    panel.update();
}
