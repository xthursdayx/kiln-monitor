# Kiln Monitor (Home Assistant Integration)

A Home Assistant custom integration for monitoring **Bartlett Instruments KilnAid-enabled kilns**.

This integration connects to the KilnAid cloud API and exposes kiln telemetry, firing progress, program information, and diagnostic data inside Home Assistant.

It supports **multiple kilns per account** and provides both **sensor entities** and **binary sensors** suitable for dashboards and automations.

---

# Features

* Monitor kiln **temperature and firing status**
* Track **thermocouple temperatures per zone**
* See **current firing program and segment**
* Monitor **estimated time remaining**
* Track **firing duration and hold time**
* Access **diagnostic telemetry**

  * element amperage
  * voltage
  * board temperature
* Binary sensors for automation

  * firing active
  * firing complete
  * cooling
  * kiln fault
  * alarm active

---

# Installation

## Install via HACS

1. Install **HACS** if you don't already have it.
2. Go to:

HACS → Integrations → Custom repositories

3. Add your fork of this repository.

Repository type:

Integration

4. Install **Kiln Monitor**
5. Restart Home Assistant.

---

# Configuration

After installation:

1. Go to:

Settings → Devices & Services → Add Integration

2. Search for:

Kiln Monitor

3. Enter your **KilnAid account credentials**

Email
Password

The integration will automatically discover the kilns associated with your account.

---

# Entities

## Sensors

### Temperature Sensors

| Entity          | Description                   |
| --------------- | ----------------------------- |
| Temperature     | Primary kiln temperature      |
| Thermocouple 1  | Zone 1 temperature            |
| Thermocouple 2  | Zone 2 temperature            |
| Thermocouple 3  | Zone 3 temperature            |
| Set Point       | Current target temperature    |
| Max Temperature | Maximum temperature of firing |

---

### Firing Status

| Entity                   | Description                           |
| ------------------------ | ------------------------------------- |
| Kiln Status              | Current mode (Firing, Complete, Idle) |
| Program Name             | Current firing program                |
| Current Segment          | Segment currently running             |
| Estimated Time Remaining | Remaining firing time                 |
| Hold Remaining Time      | Remaining hold time                   |
| Firing Time              | Total elapsed firing time             |

---

### Program Information

| Entity             | Description                  |
| ------------------ | ---------------------------- |
| Program Type       | Type of firing program       |
| Program Speed      | Speed (slow / medium / fast) |
| Program Cone       | Cone rating                  |
| Program Step Count | Number of segments           |

---

### Kiln Metadata

| Entity            | Description             |
| ----------------- | ----------------------- |
| Firmware Version  | Controller firmware     |
| Number of Firings | Lifetime firing count   |
| Zone Count        | Number of thermocouples |

---

### Diagnostics Sensors

These are **disabled by default**.

| Entity            | Description                  |
| ----------------- | ---------------------------- |
| Board Temperature | Controller board temperature |
| Amperage 1        | Element 1 amperage           |
| Amperage 2        | Element 2 amperage           |
| Amperage 3        | Element 3 amperage           |
| Voltage 1         | Element 1 voltage            |
| Voltage 2         | Element 2 voltage            |
| Voltage 3         | Element 3 voltage            |
| Supply Voltage    | Power supply voltage         |
| No Load Voltage   | Voltage with no load         |
| Full Load Voltage | Voltage under load           |
| Last Error Code   | Last kiln error code         |

These sensors are useful for diagnosing element failures or electrical issues.

---

# Binary Sensors

Binary sensors make automations easier.

| Entity          | Description                   |
| --------------- | ----------------------------- |
| Firing Active   | True while kiln firing        |
| Cooling Active  | True while kiln cooling       |
| Firing Complete | True when firing finished     |
| Alarm Active    | True when kiln alarm active   |
| Kiln Fault      | True if kiln reports an error |

---

# Example Automations

## Notify when firing completes

alias: Kiln Firing Complete
trigger:

* platform: state
  entity_id: binary_sensor.kiln_firing_complete
  to: "on"

action:

* service: notify.mobile_app_phone
  data:
  message: "Your kiln firing is complete."

---

## Alert on kiln fault

alias: Kiln Fault Alert
trigger:

* platform: state
  entity_id: binary_sensor.kiln_fault
  to: "on"

action:

* service: notify.mobile_app_phone
  data:
  message: "Kiln fault detected!"

---

## Notify when firing begins

alias: Kiln Started Firing
trigger:

* platform: state
  entity_id: binary_sensor.kiln_firing_active
  to: "on"

action:

* service: notify.mobile_app_phone
  data:
  message: "Kiln firing has started."

---

# API Endpoints Used

The integration uses several KilnAid API endpoints.

## Primary Live Data

/kilnaid-data/status

Provides:

* thermocouple temperatures
* firing status
* program name
* current segment
* estimated time remaining
* hold time
* firing time
* alarms
* errors

This endpoint is the **primary polling source**.

---

## Summary Metadata

/kilns/data

Provides:

* kiln name
* firmware version
* number of zones
* number of firings
* current temperature fallback

---

## Diagnostic Data

/kilns/view

Provides:

* amperage
* voltage
* board temperature
* diagnostic error codes
* firing cost
* program details

This endpoint is called **only when needed** to reduce API load.

---

# API Call Strategy

To minimize unnecessary calls:

| Endpoint               | When Used                               |
| ---------------------- | --------------------------------------- |
| `/kilnaid-data/status` | every update                            |
| `/kilns/data`          | every update                            |
| `/kilns/view`          | during firing or occasionally when idle |

---

# Troubleshooting

### Integration cannot connect

Verify your credentials are correct.

The login uses the same credentials as the **KilnAid mobile app**.

---

### Sensors unavailable

Ensure the kiln:

* is powered
* is connected to WiFi
* appears in the KilnAid app

---

### Diagnostic sensors not visible

They may be **disabled by default**.

Enable them in:

Settings → Devices → Kiln → Entities

---

# Roadmap / Future Improvements

Planned enhancements:

### Firing Chart

Support for:

/singleFiring/{externalId}

This will allow:

* live firing curve charts
* comparison to programmed firing profile

---

### Cooling Rate Sensor

Expose a cooling rate sensor (°/hour).

This allows monitoring kiln cooling speed for glaze firing analysis.

---

### Historical Firing Statistics

Track:

* total firing hours
* average firing duration
* average firing cost

---

### Energy Cost Tracking

Track firing energy usage and cost over time.

---

# Disclaimer

This integration is **not affiliated with Bartlett Instruments**.

Use at your own risk.

Always monitor kiln firings responsibly.

---

# Contributions

Pull requests are welcome.

If you improve the integration or add features, please consider submitting a PR.
