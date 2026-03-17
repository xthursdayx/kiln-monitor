# Kiln Monitor

A Home Assistant custom integration for monitoring **Bartlett Instruments
KilnAid-enabled kilns**.

Connects to the KilnAid cloud API and exposes kiln telemetry, firing progress,
program information, target firing curve data, and diagnostic sensors inside
Home Assistant. Supports **multiple kilns per account**.

---

## Installation

### Via HACS (recommended)

1. Install [HACS](https://hacs.xyz) if you do not already have it.
2. Go to **HACS -> Integrations -> Custom repositories**.
3. Add this repository (`xthursdayx/kiln-monitor`) as an **Integration**.
4. Install **Kiln Monitor** and restart Home Assistant.

### Manual

Copy the `custom_components/kiln_monitor/` folder into your Home Assistant
`config/custom_components/` directory and restart.

---

## Configuration

1. Go to **Settings -> Devices & Services -> Add Integration**.
2. Search for **Kiln Monitor**.
3. Enter your KilnAid account credentials (the same email and password used
   in the KilnAid mobile app).

The integration automatically discovers all kilns associated with your account.

### Options

After setup, the polling interval can be adjusted under the integration options:

- **Update interval** -- how often to poll the KilnAid API (5-60 minutes,
  default 5). During an active firing, shorter intervals give more responsive
  dashboards and automations.

---

## Entities

### Temperature Sensors

| Entity | Description | Notes |
|---|---|---|
| Temperature | Primary kiln temperature | |
| Thermocouple 1 | Zone 1 temperature | |
| Thermocouple 2 | Zone 2 temperature | |
| Thermocouple 3 | Zone 3 temperature | |
| Set Point | Current target temperature | |
| Max Temperature | Peak temperature of current firing | |

### Firing Status

| Entity | Description | Notes |
|---|---|---|
| Status | Current mode (Firing, Complete, Idle, Cooling) | |
| Program Name | Active firing program name | Attributes include raw program segments and steps |
| Current Segment | Segment number currently running | |
| Estimated Time Remaining | Remaining time in current firing | |
| Hold Remaining Time | Remaining time in current hold | |
| Firing Time | Total elapsed firing time | |

### Firing Analysis

| Entity | Description | Notes |
|---|---|---|
| Cooling Rate | Rate of temperature change during cooling (deg/h) | Positive value; 0 when not cooling |
| Target Firing Curve | Summary of the programmed firing schedule | Attributes contain full target_points and segments arrays for charting |

The `Target Firing Curve` sensor exposes a `target_points` attribute -- a list
of `{minute, temp, label}` objects representing the programmed temperature
profile. Time-shifting this list to the session start time and overlaying it on
the live temperature history gives an actual-vs-planned firing curve chart.

### Program Information

| Entity | Description | Category |
|---|---|---|
| Program Type | Type of firing program | Diagnostic |
| Program Speed | Speed (slow / medium / fast) | Diagnostic |
| Program Cone | Cone rating | Diagnostic |
| Program Step Count | Number of segments | Diagnostic |

### Kiln Metadata

| Entity | Description | Category |
|---|---|---|
| Firmware Version | Controller firmware version | Diagnostic |
| Number of Firings | Lifetime firing count | Diagnostic |
| Zone Count | Number of thermocouples | Diagnostic |

### Firing Cost and Peak

| Entity | Description | Notes |
|---|---|---|
| Firing Cost | Estimated cost of current or last firing | Disabled by default |
| Max Temperature | Peak temperature reached this firing | Disabled by default |

### Diagnostics

These sensors are disabled by default. Enable them under
**Settings -> Devices -> (your kiln) -> Entities**.

| Entity | Description |
|---|---|
| Board Temperature | Controller board temperature |
| Amperage 1 / 2 / 3 | Element amperage per zone |
| Voltage 1 / 2 / 3 | Element voltage per zone |
| Supply Voltage | Power supply voltage |
| No-Load Voltage | Voltage with no load |
| Full-Load Voltage | Voltage under full load |
| Error Text | Human-readable error description |
| Error Number | Numeric error code |
| Last Error Code | Most recent error code from diagnostics |

---

## Binary Sensors

| Entity | Description | Useful for |
|---|---|---|
| Firing Active | True while kiln is firing | Session tracking, notifications |
| Cooling Active | True while kiln is in API-reported cooling | Safe-to-open automations |
| Firing Complete | True when firing program finishes | Session end, notifications |
| Alarm Active | True when kiln alarm is active | Alert automations |
| Kiln Fault | True if kiln reports an error | Fault alert automations |

**Note:** `Cooling Active` reflects what the KilnAid API reports. Custom
firing programs that use a final AFAP-to-150F segment to keep the ventilation
fan running will not set `Cooling Active` during that phase. See the
[Custom Program Cooling](#custom-program-cooling) section below.

---

## API Endpoints

| Endpoint | Called when | Provides |
|---|---|---|
| `/kilnaid-data/status` | Every update | Temperature, status, program, ETR, alarms, errors |
| `/kilns/data` | Every update | Kiln name, firmware, zone count, firings |
| `/kilns/view` | Every update during firing; periodically when idle | Amperage, voltage, board temp, program steps, firing cost |

The `/kilns/view` endpoint is rate-limited to reduce unnecessary API calls
during idle periods (`IDLE_VIEW_REFRESH_EVERY = 6` polls).

---

## Custom Program Cooling

Some custom Bartlett firing programs append a final segment of the form:

```
Rate: 9999 F/hr  Target: 150F  Hold: 0 min
```

This keeps the ventilation fan running through the full cool-down. However,
the KilnAid API continues to report `mode: firing` during this segment, so
the `Cooling Active` binary sensor never activates.

The recommended workaround is to add a template binary sensor in Home
Assistant that detects this condition by checking `Set Point <= 150` while a
firing session is active and the program name matches a known custom program:

```yaml
- binary_sensor:
    - name: Kiln Actually Cooling
      unique_id: kiln_actually_cooling
      state: >
        {% set custom_programs = ['C6DAS'] %}
        {{
          is_state('binary_sensor.kiln_cooling_active', 'on')
          or (
            is_state('input_boolean.kiln_firing_session_active', 'on')
            and states('sensor.kiln_program_name') in custom_programs
            and states('sensor.kiln_set_point') | float(9999) <= 150
          )
        }}
```

Use this sensor in place of `cooling_active` in safe-to-open automations.

---

## Example Automations

### Notify when firing starts

```yaml
alias: Kiln Firing Started
trigger:
  - platform: state
    entity_id: binary_sensor.kiln_firing_active
    to: "on"
action:
  - action: notify.mobile_app_phone
    data:
      message: >-
        Firing started.
        Program: {{ states('sensor.kiln_program_name') }}.
```

### Notify when firing completes

```yaml
alias: Kiln Firing Complete
trigger:
  - platform: state
    entity_id: binary_sensor.kiln_firing_complete
    to: "on"
    for: "00:00:30"
action:
  - action: notify.mobile_app_phone
    data:
      message: >-
        Firing finished.
        Peak: {{ states('sensor.kiln_max_temperature') }}F.
        Cost: ${{ states('sensor.kiln_firing_cost') }}.
```

### Alert on kiln fault

```yaml
alias: Kiln Fault Alert
trigger:
  - platform: state
    entity_id: binary_sensor.kiln_kiln_fault
    to: "on"
    for: "00:01:00"
action:
  - action: notify.mobile_app_phone
    data:
      message: >-
        Kiln fault detected.
        Error: {{ states('sensor.kiln_error_text') }}.
```

### Notify when safe to open

```yaml
alias: Kiln Safe to Open
trigger:
  - platform: numeric_state
    entity_id: sensor.kiln_temperature
    below: 200
condition:
  - condition: state
    entity_id: binary_sensor.kiln_cooling_active
    state: "on"
action:
  - action: notify.mobile_app_phone
    data:
      message: "Kiln is below 200F -- safe to open."
```

---

## Troubleshooting

### Integration cannot connect

Verify that the credentials match the KilnAid mobile app. The login endpoint
is `bartinst-user-service-prod.herokuapp.com`.

### Sensors unavailable

Ensure the kiln is powered on, connected to WiFi, and visible in the KilnAid
mobile app. The integration cannot reach the API if the kiln is offline.

### Diagnostic sensors not visible

Diagnostic sensors are disabled by default. Enable them under
**Settings -> Devices -> (your kiln) -> Entities -> show disabled**.

### Blocking call warning in HA logs (Python 3.14+)

If you see a `Detected blocking call to import_module` warning, ensure you
have the latest version of the integration. The `__init__.py` pre-imports
both platform modules at load time to prevent this.

---

## Roadmap

### Historical Firing Data

Support for the `/singleFiring/{externalId}` API endpoint to retrieve the
programmed firing profile for any completed firing by its external ID. This
will enable:

- Overlay of actual vs planned firing curve for historical firings
- Retrieval of firing cost, peak temperature, and duration per firing directly
  from the API

### Historical Firing Statistics

Aggregate metrics across multiple firings:

- Total firing hours
- Average firing duration
- Average firing cost per cone

---

## Disclaimer

This integration is not affiliated with or endorsed by Bartlett Instruments.
Use at your own risk. Always monitor kiln firings responsibly.

## Contributing

Pull requests are welcome. If you improve the integration or fix a bug, please
open a PR against the main branch.
