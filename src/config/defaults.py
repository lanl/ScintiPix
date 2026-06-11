"""Default simulation configuration payloads."""

from __future__ import annotations


def default_sim_config_payload() -> dict:
    """Return the canonical default payload used to build `SimConfig`."""

    return {
        "scintillator": {
            "catalogId": "EJ200",
            "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0},
            "dimension_mm": {"x_mm": 50.0, "y_mm": 50.0, "z_mm": 10.0},
            "properties": {
                "name": "EJ200",
                "photonEnergy": [2.00, 2.40, 2.76, 3.10, 3.50],
                "rIndex": [1.58, 1.58, 1.58, 1.58, 1.58],
                "absLength": [380.0, 380.0, 380.0, 300.0, 220.0],
                "scintSpectrum": [0.05, 0.35, 1.00, 0.45, 0.08],
                "nKEntries": 5,
                "timeComponents": {
                    "default": [
                        {"timeConstant": 2.1, "yieldFraction": 1.0},
                        {"timeConstant": 0.0, "yieldFraction": 0.0},
                        {"timeConstant": 0.0, "yieldFraction": 0.0},
                    ]
                },
                "density": 1.023,
                "carbonAtoms": 9,
                "hydrogenAtoms": 10,
                "scintYield": 10000.0,
                "resolutionScale": 1.0,
            },
        },
        "source": {
            "gps": {
                "particle": "neutron",
                "position": {
                    "type": "Plane",
                    "shape": "Circle",
                    "centerMm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": -20.0},
                    "radiusMm": 1.0,
                },
                "angular": {
                    "type": "beam2d",
                    "rot1": {"x": 1.0, "y": 0.0, "z": 0.0},
                    "rot2": {"x": 0.0, "y": 1.0, "z": 0.0},
                    "direction": {"x": 0.0, "y": 0.0, "z": 1.0},
                },
                "energy": {"type": "Mono", "monoMeV": 2.45},
            }
        },
        "optical": {
            "lenses": [
                {
                    "name": "PrimaryLensOrMacro",
                    "primary": True,
                    "zmxFile": "primary.zmx",
                }
            ],
            "geometry": {"entranceDiameter": 50.0, "sensorMaxWidth": 36.0},
            "sensitiveDetectorConfig": {
                "position_mm": {"x_mm": 0.0, "y_mm": 0.0, "z_mm": 25.0},
                "shape": "circle",
                "diameterRule": "min(entranceDiameter,sensorMaxWidth)",
            },
            "showTransportProgress": True,
            "transportAssumptions": {
                "objectPlane": "scintillator_back_face",
                "opticalInterfaceRepresents": "lens_entrance_plane",
            },
        },
        "intensifier": {
            "model": "Cricket2",
            "write_output_hdf5": False,
            "input_screen": {
                "image_circle_diameter_mm": 18.0,
                "center_mm": [0.0, 0.0],
                "magnification": 1.0,
                "coordinate_frame": "intensifier_input_plane",
                "notes": "Cricket2 nominal image-circle diameter and 1:1 magnification.",
            },
        },
        "simulation": {
            "numberOfParticles": 10000,
        },
        "runner": {
            "binary": "scintipix",
            "showProgress": True,
            "verifyOutput": True,
        },
        "Metadata": {
            "author": "Your Name",
            "date": "YEAR-MONTH-DAY",
            "version": "ScintPiX [VERSION]",
            "description": "Simulation configuration for scintillator and optical system.",
            "RunEnvironment": {
                "SimulationRunID": "sim_001",
                "WorkingDirectory": "data",
                "MacroDirectory": "macros",
                "LogDirectory": "logs",
                "OutputInfo": {
                    "SimulatedPhotonsDirectory": "simulatedPhotons",
                    "TransportedPhotonsDirectory": "transportedPhotons",
                    "TransportChunkRows": "auto",
                    "TransportChunkTargetMiB": 32.0,
                },
            },
        },
    }
