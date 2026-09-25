#include "Panel.h"
#include <Wire.h>

namespace {
// PCA9685 registers
constexpr uint8_t kMode1 = 0x00, kMode2 = 0x01, kLed0 = 0x06, kAllLedOffH = 0xFD, kPrescale = 0xFE;
constexpr uint8_t kMode1Sleep = 0x10, kMode1AutoInc = 0x20;
// MODE2: INVRT=1, OUTDRV=0 (open drain) -- NXP PCA9685 datasheet Fig. 15, "direct LED
// connection": LED anode on +5V, cathode (via resistor) into the 5.5 V-tolerant output.
constexpr uint8_t kMode2DirectLed = 0x10;
constexpr uint8_t kPrescale1kHz = 5;       // 25 MHz / (4096 * (5 + 1)) = ~1 kHz, no visible flicker
constexpr uint8_t kFullBit = 0x10;         // bit 4 of LEDn_ON_H / LEDn_OFF_H

// MCP23008 registers
constexpr uint8_t kIodir = 0x00, kIpol = 0x01, kGpinten = 0x02, kIntcon = 0x04, kIocon = 0x05,
                  kGppu = 0x06, kGpio = 0x09;
constexpr uint8_t kIoconOdr = 0x04;        // INT as open-drain (Teensy pin has a pull-up)
}  // namespace

Panel::Panel(RelayBank& relays, PresetStore& presets, MidiHandler& midi)
    : relays_(relays), presets_(presets), midi_(midi) {}

bool Panel::probe(uint8_t addr) {
    Wire.beginTransmission(addr);
    return Wire.endTransmission() == 0;
}

void Panel::writeReg(uint8_t addr, uint8_t reg, uint8_t value) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
}

uint8_t Panel::readReg(uint8_t addr, uint8_t reg) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(addr, static_cast<uint8_t>(1));
    return Wire.available() ? Wire.read() : 0;
}

void Panel::begin() {
    Wire.begin();
    Wire.setClock(400000);
    present_ = probe(kPcaRG) && probe(kPcaB) && probe(kMcp);
    if (!present_) {
        Serial.println(F("button panel not found on I2C; running without it"));
        return;
    }

    for (uint8_t pca : {kPcaRG, kPcaB}) {
        writeReg(pca, kMode1, kMode1Sleep);          // prescaler only writable while asleep
        writeReg(pca, kPrescale, kPrescale1kHz);
        writeReg(pca, kMode2, kMode2DirectLed);
        writeReg(pca, kAllLedOffH, kFullBit);        // everything dark
        writeReg(pca, kMode1, kMode1AutoInc);        // wake, register auto-increment
    }
    delayMicroseconds(500);                          // oscillator start-up

    writeReg(kMcp, kIodir, 0xFF);                    // all inputs
    writeReg(kMcp, kGppu, 0xFF);                     // pull-ups; buttons short to GND
    writeReg(kMcp, kIpol, 0xFF);                     // so a pressed button reads 1
    writeReg(kMcp, kIocon, kIoconOdr);
    writeReg(kMcp, kIntcon, 0x00);                   // interrupt on any change
    writeReg(kMcp, kGpinten, 0xFF);
    pinMode(kIntPin, INPUT_PULLUP);
    stable_ = lastRaw_ = readReg(kMcp, kGpio);       // also clears any pending interrupt

    shown_ = -1;
    refreshLeds(millis());
}

void Panel::update() {
    if (!present_) return;
    uint32_t now = millis();
    // Poll while the MCP23008 flags a change, a button is held (long-press timing),
    // or a change is still settling; otherwise the bus stays idle.
    bool busy = digitalRead(kIntPin) == LOW || stable_ != 0 || lastRaw_ != stable_;
    if (busy && now - lastPoll_ >= kPollMs) {
        lastPoll_ = now;
        pollButtons(now);
    }
    for (uint8_t b = 0; b < kButtons; b++) {
        if ((stable_ & (1u << b)) && !(longFired_ & (1u << b)) && now - pressStart_[b] >= kLongPressMs) {
            longFired_ |= (1u << b);
            save(now);
        }
    }
    refreshLeds(now);
}

void Panel::pollButtons(uint32_t now) {
    uint8_t raw = readReg(kMcp, kGpio);
    if (raw != lastRaw_) {
        lastRaw_ = raw;
        lastChange_ = now;
        return;
    }
    if (raw == stable_ || now - lastChange_ < kDebounceMs) return;
    uint8_t changed = raw ^ stable_;
    stable_ = raw;
    for (uint8_t b = 0; b < kButtons; b++) {
        if (!(changed & (1u << b))) continue;
        if (raw & (1u << b)) {
            onPress(b, now);
        } else {
            onRelease(b);
        }
    }
}

void Panel::onPress(uint8_t b, uint32_t now) {
    pressStart_[b] = now;
    longFired_ &= ~(1u << b);
}

void Panel::onRelease(uint8_t b) {
    if (longFired_ & (1u << b)) return;   // that hold was a save, not a step
    cycle(b);
}

// Jack b+1: line b+1 is its tip, line b+9 its ring. State s = tip + 2*ring steps
// 0 (off) -> 1 (tip, red) -> 2 (ring, green) -> 3 (both, blue) -> 0.
void Panel::cycle(uint8_t b) {
    uint16_t p = relays_.pattern();
    uint8_t s = ((p >> b) & 1) | (((p >> (b + 8)) & 1) << 1);
    s = (s + 1) & 3;
    relays_.setChannel(b, s & 1);
    relays_.setChannel(b + 8, s & 2);
}

void Panel::save(uint32_t now) {
    uint8_t slot = midi_.currentPreset();
    presets_.setPreset(slot, relays_.pattern());
    flashUntil_ = now + kFlashMs;
    Serial.print(F("panel: saved preset "));
    Serial.println(slot);
}

void Panel::setChannel(uint8_t addr, uint8_t ch, uint16_t level) {
    uint8_t onH = 0, offL = level & 0xFF, offH = (level >> 8) & 0x0F;
    if (level == 0) {
        offL = 0;
        offH = kFullBit;          // fully off
    } else if (level >= 4095) {
        onH = kFullBit;           // fully on (no PWM)
        offL = offH = 0;
    }
    Wire.beginTransmission(addr);
    Wire.write(kLed0 + 4 * ch);   // ON_L, ON_H, OFF_L, OFF_H (auto-increment)
    Wire.write(0);
    Wire.write(onH);
    Wire.write(offL);
    Wire.write(offH);
    Wire.endTransmission();
}

void Panel::refreshLeds(uint32_t now) {
    bool flash = static_cast<int32_t>(flashUntil_ - now) > 0;
    uint16_t p = relays_.pattern();
    if (static_cast<int32_t>(p) == shown_ && flash == shownFlash_) return;
    for (uint8_t b = 0; b < kButtons; b++) {
        bool tip = (p >> b) & 1, ring = (p >> (b + 8)) & 1;
        bool r = flash || (tip && !ring);
        bool g = flash || (ring && !tip);
        bool bl = flash || (tip && ring);
        setChannel(kPcaRG, b, r ? kLevelRed : 0);
        setChannel(kPcaRG, 8 + b, g ? kLevelGreen : 0);
        setChannel(kPcaB, b, bl ? kLevelBlue : 0);
    }
    shown_ = p;
    shownFlash_ = flash;
}
