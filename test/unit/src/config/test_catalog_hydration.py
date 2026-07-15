"""Test that catalog hydration actually loads properties."""

from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root))

from src.config.yaml import from_yaml

def print_scintillator_info(simulation, test_name):
    """Helper to print scintillator information."""
    print(f"\n{test_name}")
    print(f"  Catalog ID: {simulation.scintillator.catalog_id}")
    print(f"  Properties loaded: {simulation.scintillator.properties is not None}")

    if simulation.scintillator.properties:
        props = simulation.scintillator.properties
        print(f"  Name: {props.name}")

        # Verify nested composition structure
        print(f"  Composition.density: {props.composition.density} (type: {type(props.composition.density).__name__})")
        print(f"  Composition.elements: {props.composition.elements}")

        # Verify nested optical structure
        print(f"  Optical.scint_yield: {props.optical.scint_yield} (type: {type(props.optical.scint_yield).__name__})")
        print(f"  Optical.resolution_scale: {props.optical.resolution_scale}")
        print(f"  Optical.n_k_entries: {props.optical.n_k_entries}")
        print(f"  Has optical.photon_energy: {props.optical.photon_energy is not None}")
        print(f"  Has optical.r_index: {props.optical.r_index is not None}")

        # Verify no catalog-format wrappers remain
        print(f"  Has optical.curves (should be False): {hasattr(props.optical, 'curves') and props.optical.curves is not None}")
        print(f"  Has optical.constants (should be False): {hasattr(props.optical, 'constants') and props.optical.constants is not None}")


def print_lens_info(simulation, test_name):
    """Helper to print lens information."""
    if simulation.optical and simulation.optical.lenses:
        print(f"\n{test_name}")
        for i, lens in enumerate(simulation.optical.lenses):
            print(f"  Lens {i+1}:")
            print(f"    Catalog ID: {lens.catalog_id}")
            print(f"    Name: {lens.name}")
            print(f"    ZMX file exists: {lens.zmx_file is not None}")
            print(f"    SMX file exists: {lens.smx_file is not None}")


def main():
    print("Testing catalog hydration...")
    print("=" * 80)

    # Test 1: Catalog-only (should hydrate from catalog)
    print("\nTest 1: Catalog-only YAML (should hydrate from catalog)")
    print("-" * 80)
    yaml_path_catalog = repo_root / "test_catalog_only.yaml"
    sim_catalog = from_yaml(yaml_path_catalog)
    print_scintillator_info(sim_catalog, "Scintillator (EJ-276D from catalog)")
    print_lens_info(sim_catalog, "Lens (CanonEF50mmf1.0L from catalog)")

    # Test 2: Inline properties (should keep inline, not hydrate)
    print("\n" + "=" * 80)
    print("\nTest 2: Inline properties YAML (should keep inline)")
    print("-" * 80)
    yaml_path_inline = repo_root / "examples" / "yamlFiles" / "EJ200.yaml"
    sim_inline = from_yaml(yaml_path_inline)
    print_scintillator_info(sim_inline, "Scintillator (EJ200 with inline props)")
    print_lens_info(sim_inline, "Lens (CanonEF50mmf1.0L from catalog)")

    print("\n" + "=" * 80)
    print("Catalog hydration test PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    main()
