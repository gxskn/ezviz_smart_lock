\# EZVIZ Smart Lock for Home Assistant



A custom Home Assistant integration that adds support for EZVIZ Smart Locks using the official EZVIZ cloud APIs and MQTT push events.



Unlike polling-based integrations, this integration receives events in real time.



\---



\## Features



\- 🔒 Lock entity

\- ⚡ Real-time MQTT events

\- 👤 User identification for unlock events

\- 🔑 Remote Unlock (optional)

\- 🔄 Automatic token renewal

\- 📲 Two-factor authentication (MFA)

\- ☁ Cloud Push (no polling)

\- 🏠 Home Assistant Config Flow

\- 🌐 English and Portuguese translations



\---



\## Installation



\### HACS



Coming soon.



\### Manual



Copy



```

custom\_components/ezviz\_smart\_lock

```



to



```

config/custom\_components/

```



Restart Home Assistant.



Add the integration from:



Settings → Devices \& Services → Add Integration



Search for:



```

EZVIZ Smart Lock

```



\---



\## Configuration



The integration requires:



\- EZVIZ account email

\- EZVIZ password

\- Lock serial number



If your account uses MFA, you'll be prompted for the verification code during setup.



\---



\## Security



\### Remote Unlock



Remote Unlock is \*\*disabled by default\*\*.



Enabling Remote Unlock allows the door to be unlocked directly from Home Assistant.



For security reasons, enabling or disabling this feature requires removing and adding the integration again, forcing a new EZVIZ authentication (including MFA when enabled).



No EZVIZ password is stored by the integration.



\---



\## Entity



Creates one Lock entity:



```

lock.front\_door

```



State:



\- Locked

\- Unlocked (event-based)



Attributes:



\- Last user

\- Last event

\- Last event code

\- Last alert

\- Last event timestamp



\---



\## Events



The integration fires the following Home Assistant event:



```

ezviz\_smart\_lock\_event

```



Example payload:



```yaml

event\_name: door\_opened

user: John

event\_code: 17011

```



Supported events:



| Event | Description |

|--------|-------------|

| door\_opened | Door opened |

| remote\_unlock | Remote unlock |

| passcode\_added | Passcode added |



\---



\## Example automation



Turn on hallway light when the door opens.



```yaml

alias: Hallway Light



trigger:

&#x20; - platform: event

&#x20;   event\_type: ezviz\_smart\_lock\_event



condition:

&#x20; - condition: template

&#x20;   value\_template: >

&#x20;     {{ trigger.event.data.event\_name == 'door\_opened' }}



action:

&#x20; - service: light.turn\_on

&#x20;   target:

&#x20;     entity\_id: light.hallway

```



\---



\## Known limitations



Current versions of EZVIZ Smart Locks do not expose a reliable cloud endpoint to query the real-time lock state.



For this reason, the lock entity is event-based:



\- Door opened → unlocked

\- Automatically returns to locked after a few seconds



\---



\## Supported devices



Currently tested:



\- EZVIZ DL05



Other EZVIZ Smart Locks may also work.



\---



\## Roadmap



\- Additional Smart Lock models

\- More event types

\- HACS repository

\- More translations



\---



\## License



MIT License

