"""Tests for Circuit Tracks MCP Server."""

import pytest
from src.mcp.server import CircuitTracksMCPServer, TOOLS_REGISTRY, dispatch_tool


@pytest.fixture
def mcp_server():
    return CircuitTracksMCPServer()


def test_tool_registry():
    assert "compose_pattern_batch" in TOOLS_REGISTRY
    assert "design_synth_patch" in TOOLS_REGISTRY
    assert "configure_mix_and_fx" in TOOLS_REGISTRY
    assert "hardware_sync" in TOOLS_REGISTRY


def test_compose_pattern_batch_stock(mcp_server):
    patterns = [
        {
            "track": "synth1",
            "length": 16,
            "steps": [
                {"note": 60, "velocity": 100, "gate": 12, "probability": 100},
                {"note": 64, "velocity": 90, "gate": 6, "probability": 80},
            ],
        },
        {
            "track": "drum1",
            "length": 16,
            "steps": [
                {"note": 60, "velocity": 120},
                {"note": 60, "velocity": 110},
            ],
        },
    ]

    result = mcp_server.compose_pattern_batch(
        patterns=patterns,
        tempo=128.0,
        swing=54,
        firmware_profile="stock",
    )

    assert result["status"] == "success"
    session = result["session"]
    assert session["tempo"] == 128.0
    assert session["swing"] == 54
    assert session["validated"] is True
    assert "synth1" in session["tracks"]
    assert "drum1" in session["tracks"]
    assert session["total_steps"] == 4


def test_compose_pattern_batch_invalid_tempo(mcp_server):
    with pytest.raises(ValueError, match="Tempo .* out of range"):
        mcp_server.compose_pattern_batch(patterns=[], tempo=300.0)


def test_compose_pattern_batch_invalid_firmware(mcp_server):
    with pytest.raises(ValueError, match="Unknown firmware_profile"):
        mcp_server.compose_pattern_batch(patterns=[], firmware_profile="invalid")


def test_design_synth_patch(mcp_server):
    result = mcp_server.design_synth_patch(
        synth_index=1,
        patch_name="AcidLead",
        macro_assignments={"macro1": 100, "macro2": 45},
    )

    assert result["status"] == "success"
    assert result["synth_index"] == 1
    assert result["patch_name"] == "AcidLead"
    assert result["byte_length"] == 340
    assert result["validated"] is True


def test_design_synth_patch_invalid_index(mcp_server):
    with pytest.raises(ValueError, match="synth_index must be 1 or 2"):
        mcp_server.design_synth_patch(synth_index=3, patch_name="Fail")


def test_configure_mix_and_fx(mcp_server):
    track_levels = {
        "synth1": 100,
        "synth2": 90,
        "drum1": 120,
    }
    fx_settings = {
        "reverb_preset": 5,
        "delay_preset": 8,
        "sidechain_depth": 64,
    }

    result = mcp_server.configure_mix_and_fx(
        track_levels=track_levels,
        fx_settings=fx_settings,
    )

    assert result["status"] == "success"
    assert result["track_levels"]["synth1"] == 100
    assert result["fx_settings"]["reverb_preset"] == 5
    assert result["validated"] is True


def test_configure_mix_and_fx_invalid_level(mcp_server):
    with pytest.raises(ValueError, match="out of MIDI CC bounds"):
        mcp_server.configure_mix_and_fx(track_levels={"synth1": 128})


def test_hardware_sync_mock_fallback(mcp_server):
    # Port 8770 is not expected to run during isolated unit tests,
    # so fallback should engage smoothly.
    res = mcp_server.hardware_sync(target="session", slot=64, verify=True)
    assert res["status"] in ("synced", "synced_mock_fallback")
    assert res["slot"] == 64
    assert res["verification"] is True


def test_hardware_sync_invalid_slot(mcp_server):
    with pytest.raises(ValueError, match="out of valid Circuit range"):
        mcp_server.hardware_sync(target="session", slot=65)


def test_dispatch_tool(mcp_server):
    res = dispatch_tool(
        mcp_server,
        "design_synth_patch",
        {"synth_index": 2, "patch_name": "Pad2"},
    )
    assert res["status"] == "success"
    assert res["synth_index"] == 2

    with pytest.raises(ValueError, match="Unknown tool"):
        dispatch_tool(mcp_server, "non_existent_tool", {})
