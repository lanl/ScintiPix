# Python module for ScintiPix

This module provides the python interface for ScintiPix, a simulation framework for scintillator-based event-mode imaging detectors. It includes tools for configuring GEANT4 simulations, running them, and subsequent transport and analysis of the resulting data.

This module is broken down into the following sub modules. 
- `models`: Pydantic models defining the data structures used across the simulation, ensuring data validation and consistency.
- `common`: Common information used across the simulation, like loggers and utility functions.
- `io`: Tools for input and output operations for different stages of the simulation, like reading and writing GEANT4 macros or YAML config files.
- `config`: Tools for configuring GEANT4 simulations.
- `optics`: Tools for optical transport simulations.
- `intensifier`: Tools for simulating intensifier stage.
- `sensor`: Tools for simulating the sensor stage, including the conversion of native pixel activations to TPX3 binary data.

## models
The `models` submodule provides Pydantic models defining the data structures used across the simulation, ensuring data validation and consistency. It serves as a foundation for other submodules, ensuring consistency and reducing code duplication.

**All classes should be pydantic models, and all models should be located in the `models` submodule.**

- `base`: Contains foundational Pydantic models and utility classes used across the simulation models, such as `StrictModel`, `Vec3`, `Vec3Mm`, and `Size3Mm`.
- `geant4runtime`: Contains Pydantic models related to the Geant4 runtime configuration, such as `Geant4RuntimeControlsConfig`, `Geant4RunConfig`, and `RunnerConfig`. These models define the structure and validation for simulation run controls and Python-side runner settings.
- `runner`: Contains Pydantic models related to the Python-side simulation launch settings, such as `RunnerConfig`. These models define how Python should launch and verify a Geant4 simulation, separate from the Geant4 macro commands.
- `source`: Contains Pydantic models related to the source configuration, such as `SourceConfig`, `SourceGpsConfig`, `GpsPositionConfig`, `GpsAngularConfig`, `GpsEnergyConfig`, and `SourceTimingConfig`. These models define the structure and validation for the particle source settings in the simulation.
- `scintillator`: Contains Pydantic models related to the scintillator configuration, such as `ScintillatorConfig`, `ScintillatorProperties`, `ScintillationTimeComponent`, and `ScintillationTimeComponentsByExcitation`.
- `intensifier`: Contains Pydantic models related to the intensifier configuration, such as `IntensifierConfig` and `IntensifierInputScreenConfig`. These models define the structure and validation for the intensifier stage in the simulation.
- `optics`: Contains Pydantic models related to the optical configuration, such as `OpticalConfig`, `LensConfig`, `OpticalGeometry`, `OpticalTransportAssumptionsConfig`, and `SensitiveDetectorConfig`. These models define the structure and validation for the optical transport stage in the simulation.
- `sensor`: Contains Pydantic models related to the sensor configuration, such as `SensorConfig`. These models define the structure and validation for the sensor stage in the simulation, including the conversion of native pixel activations to TPX3 binary data.

## common
The `common` submodule provides logger and utility functions that are shared across different parts of the simulation. 

- `logger`: Provides a centralized logging mechanism for the simulation, allowing consistent and configurable logging across different submodules.

## config
The `config` submodule provides all the configuration capabilties to convert the pydantic models into various configuration formats and vice versa. It enables the serialization and deserialization of the simulation settings, allowing for easy saving, loading, and modification of configuration files while maintaining the structure and validation defined by the Pydantic models.

A given ScintiPix simulation can be controlled and executed with a single YAML configuration file. This file encapsulates all the settings for the various submodules, including the runner, source, scintillator, intensifier, optics, and sensor configurations. The `config` submodule facilitates the conversion between the Pydantic models and the YAML format, ensuring that the configuration file accurately represents the simulation setup and can be easily modified and reused.

- `ConfigIO`: Provides functions for reading and writing configuration files, enabling the conversion between Pydantic models and various configuration formats such as YAML. This allows for easy loading, saving, and modification of simulation settings while maintaining the structure and validation defined by the Pydantic models.