"""
Mock FastAPI servers for parallel development.

These mocks conform to the contracts in INTERFACE_CONTRACT.md and return
realistic-looking fixed data. Use them while real agents are being built.

Usage:
    # As a script
    python -m aieic_shared.mocks.lab_companion --port 8002

    # Or import the app
    from aieic_shared.mocks.lab_companion import app
    import uvicorn
    uvicorn.run(app, port=8002)

Requires the optional [mocks] dependency:
    pip install "aieic-shared[mocks]"
"""
