<div align="center">

# EZVIZ Smart Lock

Real-time Home Assistant integration for EZVIZ Smart Locks using the official EZVIZ Cloud APIs and MQTT Push events.

Supports automatic token renewal, two-factor authentication (MFA), real-time events and optional Remote Unlock.

</div>

> **⚠️ Important**
>
> This integration is **not affiliated with or endorsed by EZVIZ**.
> It uses the official EZVIZ cloud APIs to integrate supported smart locks with Home Assistant.
---

<p align="center">

<img src="https://img.shields.io/badge/Home_Assistant-Custom_Integration-41BDF5?style=for-the-badge&logo=homeassistant&logoColor=white">

<img src="https://img.shields.io/badge/MQTT-Real_Time-success?style=for-the-badge">

<img src="https://img.shields.io/badge/MFA-Supported-green?style=for-the-badge">

<img src="https://img.shields.io/badge/Remote_Unlock-Optional-orange?style=for-the-badge">

<img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge">

</p>

---

| Feature | Status |
|---------|:------:|
| Real-time MQTT events | ✅ |
| Home Assistant Lock entity | ✅ |
| Automatic token renewal | ✅ |
| MQTT automatic reconnection | ✅ |
| Remote Unlock | ✅ |
| Two-Factor Authentication (MFA) | ✅ |
| Config Flow | ✅ |
| Device Registry | ✅ |
| English & Portuguese | ✅ |

---

## Supported devices

Currently tested:

- EZVIZ DL05

Other EZVIZ Smart Locks may also work.

---

## Installation

### HACS

1. Open HACS.
2. Go to **Integrations**.
3. Click the menu (**⋮**) → **Custom repositories**.
4. Add:

```
https://github.com/gxskn/ezviz_smart_lock
```

Category:

```
Integration
```

5. Search for **EZVIZ Smart Lock**.
6. Install.
7. Restart Home Assistant.

---

### Manual Installation

Copy

```
custom_components/ezviz_smart_lock
```

to

```
config/custom_components/
```

Restart Home Assistant.

Go to:

Settings → Devices & Services

Click:

Add Integration

Search for:

```
EZVIZ Smart Lock
```

---

## Configuration

The integration requires:

- EZVIZ account email
- EZVIZ password
- Lock serial number

If your account uses MFA, you'll be prompted to enter the verification code during setup.

---

## Security

This integration was designed with security as a priority.

### Remote Unlock

Remote Unlock is disabled by default.

Enabling this feature allows the door to be unlocked directly from Home Assistant.

For security reasons, enabling or disabling Remote Unlock requires removing and adding the integration again, forcing a new EZVIZ authentication (including MFA when enabled).

This behavior is intentional.

### Security Model

• EZVIZ passwords are never stored.

• Remote Unlock is disabled by default.

• Remote Unlock requires explicit user opt-in.

• Enabling Remote Unlock requires a new EZVIZ authentication.

• MFA is fully supported.

• No sensitive information is written to Home Assistant logs.

• MQTT is used only for receiving events.

• Commands are sent using authenticated EZVIZ Cloud APIs.

---

## Home Assistant Entity

Creates one Lock entity.

Example:

```
lock.front_door
```

Supported states:

- Locked
- Unlocked (event-based)

Attributes:

| Attribute | Description |
|------------|-------------|
| last_user | User who opened the door |
| last_event | Event identifier |
| last_event_label | Human-readable event |
| last_event_code | EZVIZ event code |
| last_alert | Alert message |
| last_event_time | Timestamp |

---

## Events

The integration fires the following Home Assistant event:

```
ezviz_smart_lock_event
```

Example:

```yaml
event_name: door_opened
user: John
event_code: 17011
```

Supported events:

| Event | Description |
|--------|-------------|
| door_opened | Door opened |
| remote_unlock | Remote unlock |
| passcode_added | Passcode added |

---

## Example Automation

Turn on the hallway light when the door opens.

```yaml
alias: Hallway Light

trigger:
  - platform: event
    event_type: ezviz_smart_lock_event

condition:
  - condition: template
    value_template: >
      {{ trigger.event.data.event_name == 'door_opened' }}

action:
  - service: light.turn_on
    target:
      entity_id: light.hallway
```

---

## Known Limitations

Current EZVIZ Smart Locks do not expose a reliable cloud endpoint to retrieve the real-time lock state.

For this reason, the Lock entity is event-based.

When the door is opened, the entity changes to **Unlocked** and automatically returns to **Locked** after a few seconds.

---

## Roadmap

- Additional EZVIZ Smart Lock models
- More event types
- More translations
- Community contributions

---

## Contributing

Bug reports, feature requests and pull requests are welcome.

If you find a bug or have a suggestion, please open an Issue on GitHub.

---

## About this project

I created this integration because I wanted to use my EZVIZ Smart Lock with Home Assistant, but I couldn't find an existing integration that met my needs.

I'm not an experienced Python developer, so this project was developed entirely with the help of AI. I was responsible for defining the requirements, testing every feature, investigating the EZVIZ APIs, validating the results, and making the design and security decisions, while the implementation itself was largely generated with AI assistance.

Because of that, there may still be bugs, edge cases, or opportunities to improve the code.

That said, the primary goal of this project—to integrate my EZVIZ Smart Lock with Home Assistant—has been achieved, and it has been working reliably in my own environment.

If you find any issues or have ideas for improvements, feel free to open an Issue or submit a Pull Request. Any contribution is greatly appreciated.
