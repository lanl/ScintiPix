# Simulation Working Environment

This document describes the working environment for running ScintiPix simulations. ScintiPix can be called with either a config file that specifies the simulation running environment, such as working directories and output paths, or by itself with default settings. The following sections describe the default working environment and how to specify a custom one.

The simulations working environment is defined in the pydantic model `Simulation`. Within`Simulation` there is a `metadata` submodule that contains all the needed information out the runtime environment, along with the various needed directories for logging and outputs.

Becuase ScintiPix is multistaged and users can define at what stage to stop, the working environment from one simulation to another might look different depending on what stages of the simulation are enabled. 


## Default Working Environment

ScintiPix uses a model called `Simulation` to specify the simulation running environment. If no `Simulation` is provided, ScintiPix uses the following default settings:

- `SimulationRunID`: "example"
- `SubRunNumber`: `0`
- `WorkingDirectory`: `data/`
- `MacroDirectory`: `macros/`
- `LogDirectory`: `logs/`
- `PrimariesDirectory`: `primaries/`
- `SecondariesDirectory`: `secondaries/`
- `SimulatedPhotonsDirectory`: `simulatedPhotons/`
- `TransportedPhotonsDirectory`: `transportedPhotons/`
- `IntensifiedPhotonsDirectory`: `intensifiedPhotons/`
- `SensorHitsDirectory`: `sensorHits/`

This will create the following directory structure under `data/`:

```text
data/
  example_000/
    primaries/
    secondaries/
    simulatedPhotons/
      photons.bin
    transportedPhotons/
      photons.bin
    intensifiedPhotons/
    sensorHits/
    macros/
    logs/
```

## Custom Working Environment

Users can specify custom values for any of the `RunEnvironmentConfig` fields in `Simulation` to create a different working environment. For example, a user could set `WorkingDirectory` to `my_simulations/`, `SimulationRunID` to `run_001`, and `PrimariesDirectory` to `neutrons` which would create the following directory structure:

```text 
my_simulations/
  run_001/
    neutrons/
    secondaries/
    simulatedPhotons/
    transportedPhotons/
    intensifiedPhotons/
    sensorHits/
    macros/
    logs/
```

All working directories should be verified using validation checks within the pydantic model to ensure they are valid paths and have the necessary permissions for reading/writing files.
