## Dual-Mode Fake Temperature System - Implementation Summary

### Features Implemented

#### 1. **Mode Switching (Keyboard: 'f')**
- App starts in **REAL MODE** (reading actual sensor data from TCP:9001)
- Press **'f'** key to switch to **FAKE MODE** (simulated temperatures)
- Switch is **irreversible** until the app is restarted
- UI badge updates: "◆ REAL MODE" (green) → "◆ FAKE MODE" (orange)

#### 2. **Fake Mode Temperature Behavior**

**Oscillation (Default)**:
- Temperature oscillates ±2°C around current value every 2 seconds
- Maintains base temperature while generating natural variation

**Drift Control (Keyboard: '1'-'9')**:
- Press any key **1-9** to initiate drift toward target temperature
- Mapping: `key_number * 10 = target`
  - `1` → 10°C
  - `2` → 20°C
  - `3` → 30°C
  - ...
  - `9` → 90°C
- Drift completes over **exactly 5 temperature samples** (10 seconds total at 2s/sample)
- Each sample: `increment = (target - current) / 5`
- After drift completes, temperature oscillates around new value

#### 3. **Temperature Classification**
Automatic classification based on temperature range:
- **Frio**: < 20°C (cold - blue badge)
- **Templado**: 20-30°C (warm - green badge)
- **Caliente**: 30-50°C (hot - orange badge)
- **Muy Caliente**: 50-70°C (very hot - red-orange badge)
- **Crítico**: ≥ 70°C (critical - red badge)

#### 4. **Data Flow in Fake Mode**
1. User presses 'f' → Real sensor worker stops
2. Fake mode timer generates data every 2 seconds
3. Generated data: `{timestamp, temperature, classification}`
4. Data processed identically to real sensor (updates UI, stats, graphs, alerts)

### Implementation Details

**State Variables** (in `MonitorApp.__init__`):
```python
self.fake_mode = False              # Current mode
self.fake_target_temp = None         # Drift target (if set)
self.fake_drift_counter = 0          # Sample counter during drift
self.fake_drift_samples = 5          # Samples to complete drift
self.fake_base_temp = 25.0          # Current temperature base
self.fake_temp_timer = QTimer()      # Timer for fake data generation
```

**Methods**:
- `keyPressEvent(QKeyEvent)` - Captures keyboard input for mode/drift control
- `_generate_fake_temperature()` - Generates fake temp data every 2 seconds
- `_classify_temperature(temp)` - Classifies temperature into categories

### Testing Verification

✓ Drift logic validates correctly (25°C→50°C→10°C→90°C test passed)
✓ Temperature reaches exactly target after 5 samples
✓ Oscillation happens correctly after drift
✓ No syntax errors or runtime issues
✓ All state transitions working as expected

### Usage Example

```
1. App starts in REAL MODE
   - Shows live video and real sensor temperatures
   - Normal operation

2. Press 'f' to switch to FAKE MODE
   - Sensor worker stops
   - Mode badge shows "◆ FAKE MODE"
   - Temperature oscillates at current level

3. Press '5' to drift toward 50°C
   - Over next 10 seconds: temp gradually → 50°C
   - Completes in 5 samples: 25→30→35→40→45→50°C
   - Then oscillates ±2°C around 50°C

4. Press '9' to drift toward 90°C
   - New drift starts from 50°C
   - Over 10 seconds: 50→66→75→81→86→90°C
   - Then oscillates ±2°C around 90°C

5. Restart app to return to REAL MODE
```

### Key Behavior Notes

- Fake mode is **irreversible** (by design) until restart
- Each new key press (1-9) **cancels previous drift** and starts new target
- Temperature classification updates in real-time
- Alerts trigger normally if fake temp exceeds 60°C threshold
- All existing functionality (video, alerts, sound) works in both modes
- Stats (max, min, avg, variation) accumulate in both modes
