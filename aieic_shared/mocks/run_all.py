"""
Run all mock agents at once on their default ports.

This is a convenience entry point so the Orchestrator developer can spin up
the entire mock backend with one command.

Run:
    python -m aieic_shared.mocks.run_all

Or specify which ones:
    python -m aieic_shared.mocks.run_all --no-participant   # if real one is running
"""

from __future__ import annotations
import argparse
import multiprocessing
import sys
import time

import uvicorn

from aieic_shared.mocks.assessment import app as assessment_app
from aieic_shared.mocks.curriculum_designer import app as curriculum_app
from aieic_shared.mocks.integrity import app as integrity_app
from aieic_shared.mocks.lab_companion import app as companion_app
from aieic_shared.mocks.participant import app as participant_app


def _run(app_module: str, port: int, host: str) -> None:
    uvicorn.run(app_module, host=host, port=port, log_level="info")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all AIEIC mock agents at once")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--no-companion", action="store_true")
    parser.add_argument("--no-participant", action="store_true")
    parser.add_argument("--no-curriculum", action="store_true")
    parser.add_argument("--no-assessment", action="store_true")
    parser.add_argument("--no-integrity", action="store_true")
    args = parser.parse_args()

    services = []
    if not args.no_companion:
        services.append(("aieic_shared.mocks.lab_companion:app", 8002, "companion"))
    if not args.no_participant:
        services.append(("aieic_shared.mocks.participant:app", 8001, "participant"))
    if not args.no_curriculum:
        services.append(("aieic_shared.mocks.curriculum_designer:app", 8003, "curriculum"))
    if not args.no_assessment:
        services.append(("aieic_shared.mocks.assessment:app", 8004, "assessment"))
    if not args.no_integrity:
        services.append(("aieic_shared.mocks.integrity:app", 8005, "integrity"))

    if not services:
        print("Nothing to run.")
        sys.exit(1)

    processes = []
    for app_path, port, name in services:
        p = multiprocessing.Process(
            target=_run,
            args=(app_path, port, args.host),
            name=name,
        )
        p.start()
        processes.append((p, name, port))
        time.sleep(0.2)  # Stagger startup

    print("\n" + "=" * 60)
    print("AIEIC mock servers running:")
    for _, name, port in processes:
        print(f"  http://{args.host}:{port}  →  {name}")
    print("=" * 60)
    print("Press Ctrl+C to stop all.\n")

    try:
        for p, _, _ in processes:
            p.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
        for p, _, _ in processes:
            p.terminate()


if __name__ == "__main__":
    main()
