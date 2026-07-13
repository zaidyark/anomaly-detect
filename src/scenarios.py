"""Synthetic attack scenarios with ground-truth labels for detector evaluation."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd


BASE_TIME = datetime(2025, 3, 1, 8, 0, 0)
WINDOW_MINUTES = 480
# Attack traffic is injected into the last quarter of the window so the
# new-neighbour-ratio feature (early 75% vs late 25%) can pick it up.
ATTACK_START_MINUTE = int(WINDOW_MINUTES * 0.78)


@dataclass(frozen=True)
class ScenarioResult:
    """A generated dataset plus the nodes that are anomalous by construction."""

    key: str
    name: str
    description: str
    frame: pd.DataFrame
    true_anomalies: tuple[str, ...]


def _row(source: str, destination: str, minute: float, protocol: str) -> dict:
    return {
        "source": source,
        "destination": destination,
        "timestamp": BASE_TIME + timedelta(minutes=minute),
        "protocol": protocol,
    }


def _baseline_network(rng: random.Random) -> tuple[list[dict], dict[str, list[str]]]:
    """Build normal office traffic: 3 departments behind switches, a core router, servers.

    Returns the traffic rows and the department -> workstation mapping so
    scenarios can pick victims from realistic positions in the topology.
    """
    departments = {
        "HR": [f"HR-PC{i}" for i in range(1, 8)],
        "ENG": [f"ENG-PC{i}" for i in range(1, 10)],
        "FIN": [f"FIN-PC{i}" for i in range(1, 7)],
    }
    servers = ["FileServer", "MailServer", "WebServer"]
    rows: list[dict] = []

    for dept, machines in departments.items():
        switch = f"{dept}-Switch"
        rows.append(_row(switch, "Router", rng.uniform(0, 5), "TCP"))
        for machine in machines:
            # Regular chatter with the department switch and shared servers.
            for _ in range(rng.randint(3, 6)):
                rows.append(_row(machine, switch, rng.uniform(0, ATTACK_START_MINUTE), "TCP"))
            for server in rng.sample(servers, k=rng.randint(1, 2)):
                for _ in range(rng.randint(1, 3)):
                    rows.append(_row(machine, server, rng.uniform(0, ATTACK_START_MINUTE), rng.choice(["TCP", "TCP", "UDP"])))
            # Occasional peer-to-peer traffic inside the department.
            for peer in rng.sample(machines, k=min(2, len(machines) - 1)):
                if peer != machine:
                    rows.append(_row(machine, peer, rng.uniform(0, ATTACK_START_MINUTE), "TCP"))

    for server in servers:
        rows.append(_row(server, "Router", rng.uniform(0, 10), "TCP"))
        for _ in range(3):
            rows.append(_row(server, rng.choice(servers), rng.uniform(0, ATTACK_START_MINUTE), "TCP"))

    # Light steady-state traffic continues in the late window so "recent
    # activity" alone is not anomalous.
    for dept, machines in departments.items():
        for machine in rng.sample(machines, k=3):
            rows.append(_row(machine, f"{dept}-Switch", rng.uniform(ATTACK_START_MINUTE, WINDOW_MINUTES), "TCP"))

    return rows, departments


def _scanner(rng: random.Random, rows: list[dict], departments: dict[str, list[str]]) -> tuple[str, ...]:
    """A compromised workstation sweeps almost every device on the network."""
    scanner = departments["ENG"][2]
    targets = [machine for dept in departments.values() for machine in dept if machine != scanner]
    targets += ["FileServer", "MailServer", "WebServer", "HR-Switch", "FIN-Switch"]
    for index, target in enumerate(targets):
        minute = ATTACK_START_MINUTE + index * (WINDOW_MINUTES - ATTACK_START_MINUTE) / max(1, len(targets))
        rows.append(_row(scanner, target, minute, "ICMP"))
    return (scanner,)


def _exfiltration(rng: random.Random, rows: list[dict], departments: dict[str, list[str]]) -> tuple[str, ...]:
    """Many machines funnel data into one staging host, which ships it outside."""
    staging = "STAGING-01"
    victims = (
        rng.sample(departments["FIN"], k=5)
        + rng.sample(departments["HR"], k=4)
        + rng.sample(departments["ENG"], k=5)
    )
    for victim in victims:
        for _ in range(rng.randint(2, 4)):
            rows.append(_row(victim, staging, rng.uniform(ATTACK_START_MINUTE, WINDOW_MINUTES), "TCP"))
    for _ in range(8):
        rows.append(_row(staging, "EXT-198.51.100.7", rng.uniform(ATTACK_START_MINUTE, WINDOW_MINUTES), "TCP"))
    return (staging,)


def _rogue_bridge(rng: random.Random, rows: list[dict], departments: dict[str, list[str]]) -> tuple[str, ...]:
    """A rogue access point becomes the only link between an unmanaged segment and the LAN."""
    rogue = "ROGUE-AP"
    iot_devices = [f"IOT-CAM{i}" for i in range(1, 6)]
    for device in iot_devices:
        for _ in range(rng.randint(2, 4)):
            rows.append(_row(device, rogue, rng.uniform(ATTACK_START_MINUTE, WINDOW_MINUTES), "UDP"))
    rows.append(_row(rogue, "ENG-Switch", ATTACK_START_MINUTE + 5, "TCP"))
    rows.append(_row(rogue, "FileServer", ATTACK_START_MINUTE + 20, "TCP"))
    return (rogue,)


def _botnet(rng: random.Random, rows: list[dict], departments: dict[str, list[str]]) -> tuple[str, ...]:
    """Infected workstations beacon to a command-and-control host and mesh together."""
    c2 = "C2-SERVER"
    bots = [
        departments["HR"][1],
        departments["ENG"][4],
        departments["ENG"][6],
        departments["FIN"][2],
        departments["FIN"][4],
    ]
    all_machines = [machine for dept in departments.values() for machine in dept]
    for bot in bots:
        for beacon in range(5):
            minute = ATTACK_START_MINUTE + beacon * 18 + rng.uniform(0, 4)
            rows.append(_row(bot, c2, min(minute, WINDOW_MINUTES - 1), "TCP"))
        for peer in bots:
            if peer != bot:
                rows.append(_row(bot, peer, rng.uniform(ATTACK_START_MINUTE, WINDOW_MINUTES), "UDP"))
        # Lateral movement: each bot probes a handful of uninfected machines.
        for target in rng.sample([machine for machine in all_machines if machine not in bots], k=6):
            rows.append(_row(bot, target, rng.uniform(ATTACK_START_MINUTE, WINDOW_MINUTES), "TCP"))
    return tuple([c2, *bots])


_SCENARIOS = {
    "scanner": (
        "Network Scanner",
        "A compromised engineering workstation sweeps nearly every device on the network "
        "(sudden fan-out of new, one-off ICMP connections).",
        _scanner,
    ),
    "exfiltration": (
        "Data Exfiltration Hub",
        "Finance and HR machines funnel data into an unknown staging host, which then "
        "uploads it to an external address (sudden high in-degree hub).",
        _exfiltration,
    ),
    "rogue_bridge": (
        "Rogue Bridge Device",
        "An unauthorized access point becomes the only link between an unmanaged IoT "
        "segment and the corporate LAN (isolated bridge with low clustering).",
        _rogue_bridge,
    ),
    "botnet": (
        "Botnet Beaconing",
        "Four infected workstations beacon repeatedly to a command-and-control server and "
        "mesh with each other (new tightly-connected clique spanning departments).",
        _botnet,
    ),
}


def list_scenarios() -> list[dict[str, str]]:
    """Return scenario metadata for building UI options."""
    return [
        {"key": key, "name": name, "description": description}
        for key, (name, description, _) in _SCENARIOS.items()
    ]


def generate_scenario(key: str, seed: int = 42) -> ScenarioResult:
    """Generate a labelled dataset: normal office traffic plus one injected attack."""
    if key not in _SCENARIOS:
        raise ValueError(f"Unknown scenario: {key}")
    name, description, inject = _SCENARIOS[key]
    rng = random.Random(seed)
    rows, departments = _baseline_network(rng)
    true_anomalies = inject(rng, rows, departments)
    frame = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return ScenarioResult(
        key=key,
        name=name,
        description=description,
        frame=frame,
        true_anomalies=true_anomalies,
    )
