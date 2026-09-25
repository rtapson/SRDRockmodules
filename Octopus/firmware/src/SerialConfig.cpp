#include "SerialConfig.h"
#include "RelayBank.h"

SerialConfig::SerialConfig(PresetStore& presets) : presets_(presets) {}

void SerialConfig::begin() {
    lineBuffer_.reserve(48);
}

void SerialConfig::update() {
    while (Serial.available()) {
        char c = static_cast<char>(Serial.read());
        if (c == '\n' || c == '\r') {
            if (lineBuffer_.length() > 0) {
                handleLine(lineBuffer_);
                lineBuffer_ = "";
            }
        } else {
            lineBuffer_ += c;
        }
    }
}

void SerialConfig::handleLine(const String& line) {
    String cmd = line;
    cmd.trim();
    cmd.toUpperCase();

    if (cmd == "HELP") {
        printHelp();
        return;
    }
    if (cmd == "DUMP") {
        printDump();
        return;
    }
    if (cmd.startsWith("CH=")) {
        int value = cmd.substring(3).toInt();
        if (value < 0 || value > 16) {
            Serial.println(F("ERR: channel must be 0 (omni) - 16"));
            return;
        }
        presets_.setMidiChannel(static_cast<uint8_t>(value));
        Serial.print(F("OK channel="));
        Serial.println(value);
        return;
    }
    if (cmd.startsWith("P")) {
        int eq = cmd.indexOf('=');
        if (eq < 1) {
            Serial.println(F("ERR: expected P<n>=<16 chars of 0/1>"));
            return;
        }
        int index = cmd.substring(1, eq).toInt();
        // spaces, '-' and '_' are allowed as separators, e.g. P12=00110101 00000000
        String bits;
        for (unsigned int i = eq + 1; i < cmd.length(); i++) {
            char c = cmd[i];
            if (c == ' ' || c == '-' || c == '_') continue;
            if (c != '0' && c != '1') {
                Serial.println(F("ERR: pattern must contain only 0/1 (separators: space - _)"));
                return;
            }
            bits += c;
        }
        if (index < 0 || index >= static_cast<int>(PresetStore::kPresetCount) ||
            bits.length() != RelayBank::kChannelCount) {
            Serial.println(F("ERR: preset must be 0-127, pattern must be 16 chars of 0/1"));
            return;
        }
        uint16_t pattern = 0;
        for (uint8_t i = 0; i < RelayBank::kChannelCount; i++) {
            if (bits[i] == '1') pattern |= static_cast<uint16_t>(1u << i);
        }
        presets_.setPreset(static_cast<uint8_t>(index), pattern);
        Serial.print(F("OK preset "));
        Serial.print(index);
        Serial.print(F(" = "));
        printPattern(pattern);
        Serial.println();
        return;
    }

    Serial.println(F("ERR: unknown command, try HELP"));
}

// Tips (lines 1-8) then rings (lines 9-16), with a space between, e.g. "00110101 00000000".
void SerialConfig::printPattern(uint16_t pattern) {
    for (uint8_t bit = 0; bit < RelayBank::kChannelCount; bit++) {
        if (bit == 8) Serial.print(' ');
        Serial.print((pattern & (1u << bit)) ? '1' : '0');
    }
}

void SerialConfig::printHelp() {
    Serial.println(F("Octopus config console:"));
    Serial.println(F("  P<n>=<16 bits>  set preset n (0-127). Char i = line i+1: chars 1-8 are jack 1-8 TIP,"));
    Serial.println(F("                  chars 9-16 are jack 1-8 RING. e.g. P12=00110101 00000001"));
    Serial.println(F("  CH=<n>          set MIDI channel, 0 = omni, 1-16 = fixed channel"));
    Serial.println(F("  DUMP            list all non-empty presets and current channel"));
    Serial.println(F("  HELP            show this message"));
}

void SerialConfig::printDump() {
    Serial.print(F("channel="));
    Serial.println(presets_.midiChannel());
    for (uint16_t i = 0; i < PresetStore::kPresetCount; i++) {
        uint16_t pattern = presets_.preset(static_cast<uint8_t>(i));
        if (pattern == 0) continue;
        Serial.print(F("preset "));
        Serial.print(i);
        Serial.print(F(" = "));
        printPattern(pattern);
        Serial.println();
    }
}
