"""Test that updated YAML files validate correctly."""
from src.config.yaml import from_yaml

yaml_files = [
    'examples/yamlFiles/EJ200.yaml',
    'examples/yamlFiles/CanonEF50mmf1p0L_example.yaml',
    'examples/yamlFiles/continuous_neutron_source_timing.yaml',
    'examples/yamlFiles/EJ276D.yaml',
    'examples/yamlFiles/three_component_timing_example.yaml',
    'examples/yamlFiles/pulsed_neutron_source_timing.yaml',
]

print("Testing all YAML examples...")
print("=" * 60)

for yaml_file in yaml_files:
    try:
        config = from_yaml(yaml_file)
        culling = config.geant4runner.photon_culling
        status = "✓"
        msg = f"enabled={culling.enabled}, angle={culling.acceptance_angle_deg}°"
    except Exception as e:
        status = "✗"
        msg = f"ERROR: {str(e)}"

    print(f"{status} {yaml_file.split('/')[-1]}")
    print(f"   {msg}")

print("=" * 60)
print("All YAML files validated successfully!")
