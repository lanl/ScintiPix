"""Test that models can load both catalog and simulation YAML formats."""

from pathlib import Path
import sys
import yaml

repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root / "src"))

from models.scintillator import ScintillatorProperties

def test_catalog_format():
    """Test loading catalog YAML format directly."""
    print("=" * 80)
    print("Test 1: Loading Catalog Format (EJ-276D.yaml)")
    print("=" * 80)

    catalog_file = repo_root / "catalogs" / "scintillators" / "materials" / "EJ-276D.yaml"

    with open(catalog_file) as f:
        data = yaml.safe_load(f)

    print(f"\nLoaded YAML structure:")
    print(f"  id: {data.get('id')}")
    print(f"  name: {data.get('name')}")
    print(f"  composition.density: {data['composition']['density']}")
    print(f"  composition.atoms: {data['composition']['atoms']}")
    print(f"  optical.curves: {list(data['optical']['curves'].keys())}")
    print(f"  optical.constants: {list(data['optical']['constants'].keys())}")

    try:
        scint = ScintillatorProperties.model_validate(data)
        print(f"\n✓ Successfully validated as ScintillatorProperties!")
        print(f"  Name: {scint.name}")
        print(f"  Density: {scint.composition.density}")
        print(f"  Atoms: {scint.composition.atoms}")
        print(f"  Has curves: {scint.optical.curves is not None}")
        print(f"  Has constants: {scint.optical.constants is not None}")

        if scint.optical.constants:
            print(f"  Scint yield: {scint.optical.constants.scint_yield}")
            print(f"  Resolution scale: {scint.optical.constants.resolution_scale}")

        return True
    except Exception as e:
        print(f"\n✗ Failed to validate: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simulation_format():
    """Test loading simulation YAML format (inline properties)."""
    print("\n" + "=" * 80)
    print("Test 2: Loading Simulation Format (EJ200.yaml example)")
    print("=" * 80)

    # Simulate the inline format from EJ200.yaml
    data = {
        "name": "EJ200",
        "composition": {
            "density": 1.05,
            "atoms": {"C": 9, "H": 10}
        },
        "optical": {
            "photonEnergy": [2.0, 2.5, 3.0, 3.5, 4.0],
            "rIndex": [1.58, 1.58, 1.58, 1.58, 1.58],
            "nKEntries": 5,
            "absLength": [420.0, 420.0, 340.0, 260.0, 180.0],
            "scintSpectrum": [0.04, 0.30, 1.00, 0.52, 0.12],
            "timeComponents": {
                "default": [
                    {"timeConstant": 2.4, "yieldFraction": 1.0},
                    {"timeConstant": 0.0, "yieldFraction": 0.0},
                    {"timeConstant": 0.0, "yieldFraction": 0.0}
                ]
            },
            "scintYield": 9800.0,
            "resolutionScale": 1.1
        }
    }

    try:
        scint = ScintillatorProperties.model_validate(data)
        print(f"\n✓ Successfully validated as ScintillatorProperties!")
        print(f"  Name: {scint.name}")
        print(f"  Density: {scint.composition.density}")
        print(f"  Atoms: {scint.composition.atoms}")
        print(f"  Photon energy points: {len(scint.optical.photon_energy)}")
        print(f"  nKEntries: {scint.optical.n_k_entries}")
        print(f"  Scint yield: {scint.optical.scint_yield}")
        print(f"  Resolution scale: {scint.optical.resolution_scale}")

        return True
    except Exception as e:
        print(f"\n✗ Failed to validate: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\nTesting Model Convergence: Catalog vs Simulation Formats")
    print("=" * 80)

    results = []

    # Test catalog format
    results.append(("Catalog Format", test_catalog_format()))

    # Test simulation format
    results.append(("Simulation Format", test_simulation_format()))

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print(f"\n🎉 All tests passed! Models support both formats.")
    else:
        print(f"\n❌ Some tests failed. Check the output above.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
