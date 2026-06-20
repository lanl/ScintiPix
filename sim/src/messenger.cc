#include "messenger.hh"

#include "config.hh"

#include "G4ApplicationState.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4UIcmdWithADouble.hh"
#include "G4UIcmdWithADoubleAndUnit.hh"
#include "G4UIcmdWithAnInteger.hh"
#include "G4UIcmdWithAString.hh"
#include "G4UIcommand.hh"
#include "G4UIdirectory.hh"
#include "G4UnitsTable.hh"
#include "G4ios.hh"

#include <algorithm>
#include <sstream>
#include <string>
#include <vector>

namespace {
bool TryParseDouble(const std::string& text, G4double* out) {
  if (!out) {
    return false;
  }
  std::istringstream stream(text);
  G4double value = 0.0;
  stream >> value;
  if (!stream.fail() && stream.eof()) {
    *out = value;
    return true;
  }
  return false;
}

bool ParseListWithOptionalUnit(const G4String& rawValue,
                               std::vector<G4double>* values,
                               std::string* unitToken) {
  if (!values) {
    return false;
  }
  values->clear();
  if (unitToken) {
    unitToken->clear();
  }

  std::string normalized = rawValue;
  std::replace(normalized.begin(), normalized.end(), ',', ' ');
  std::istringstream stream(normalized);
  std::vector<std::string> tokens;
  for (std::string token; stream >> token;) {
    tokens.push_back(token);
  }
  if (tokens.empty()) {
    return false;
  }

  std::size_t end = tokens.size();
  G4double parsed = 0.0;
  if (!TryParseDouble(tokens.back(), &parsed)) {
    if (unitToken) {
      *unitToken = tokens.back();
    }
    end = tokens.size() - 1;
  }
  if (end == 0) {
    return false;
  }

  values->reserve(end);
  for (std::size_t i = 0; i < end; ++i) {
    if (!TryParseDouble(tokens[i], &parsed)) {
      return false;
    }
    values->push_back(parsed);
  }
  return true;
}
}  // namespace

Messenger::Messenger(Config* config) : fConfig(config) {
  fScintillatorDir = new G4UIdirectory("/scintillator/");
  fScintillatorDir->SetGuidance("Scintillator controls");

  fScintillatorGeomDir = new G4UIdirectory("/scintillator/geom/");
  fScintillatorGeomDir->SetGuidance("Scintillator geometry and material controls");

  fScintillatorPropertiesDir = new G4UIdirectory("/scintillator/properties/");
  fScintillatorPropertiesDir->SetGuidance("Scintillator optical/material properties");

  fOpticalInterfaceDir = new G4UIdirectory("/optical_interface/");
  fOpticalInterfaceDir->SetGuidance("Optical-interface controls");

  fOpticalInterfaceGeomDir = new G4UIdirectory("/optical_interface/geom/");
  fOpticalInterfaceGeomDir->SetGuidance("Optical-interface geometry controls");

  fSourceDir = new G4UIdirectory("/source/");
  fSourceDir->SetGuidance("Source controls");

  fSourceTimingDir = new G4UIdirectory("/source/timing/");
  fSourceTimingDir->SetGuidance("Source timing controls");

  fOutputDir = new G4UIdirectory("/output/");
  fOutputDir->SetGuidance("Output controls");

  fPhotonCullingDir = new G4UIdirectory("/photonCulling/");
  fPhotonCullingDir->SetGuidance("Photon culling optimization controls");

  fGeomMaterialCmd = new G4UIcmdWithAString("/scintillator/geom/material", this);
  fGeomMaterialCmd->SetGuidance("Set scintillator material name (EJ200 or NIST name)");
  fGeomMaterialCmd->SetParameterName("material", false);
  fGeomMaterialCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fGeomScintXCmd = new G4UIcmdWithADoubleAndUnit("/scintillator/geom/scintX", this);
  fGeomScintXCmd->SetGuidance("Set scintillator size in X");
  fGeomScintXCmd->SetParameterName("scintX", false);
  fGeomScintXCmd->SetUnitCategory("Length");
  fGeomScintXCmd->SetRange("scintX > 0.");
  fGeomScintXCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fGeomScintYCmd = new G4UIcmdWithADoubleAndUnit("/scintillator/geom/scintY", this);
  fGeomScintYCmd->SetGuidance("Set scintillator size in Y");
  fGeomScintYCmd->SetParameterName("scintY", false);
  fGeomScintYCmd->SetUnitCategory("Length");
  fGeomScintYCmd->SetRange("scintY > 0.");
  fGeomScintYCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fGeomScintZCmd = new G4UIcmdWithADoubleAndUnit("/scintillator/geom/scintZ", this);
  fGeomScintZCmd->SetGuidance("Set scintillator thickness in Z");
  fGeomScintZCmd->SetParameterName("scintZ", false);
  fGeomScintZCmd->SetUnitCategory("Length");
  fGeomScintZCmd->SetRange("scintZ > 0.");
  fGeomScintZCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fGeomScintPosXCmd = new G4UIcmdWithADoubleAndUnit("/scintillator/geom/posX", this);
  fGeomScintPosXCmd->SetGuidance("Set scintillator center X position in world coordinates");
  fGeomScintPosXCmd->SetParameterName("posX", false);
  fGeomScintPosXCmd->SetUnitCategory("Length");
  fGeomScintPosXCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fGeomScintPosYCmd = new G4UIcmdWithADoubleAndUnit("/scintillator/geom/posY", this);
  fGeomScintPosYCmd->SetGuidance("Set scintillator center Y position in world coordinates");
  fGeomScintPosYCmd->SetParameterName("posY", false);
  fGeomScintPosYCmd->SetUnitCategory("Length");
  fGeomScintPosYCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fGeomScintPosZCmd = new G4UIcmdWithADoubleAndUnit("/scintillator/geom/posZ", this);
  fGeomScintPosZCmd->SetGuidance("Set scintillator center Z position in world coordinates");
  fGeomScintPosZCmd->SetParameterName("posZ", false);
  fGeomScintPosZCmd->SetUnitCategory("Length");
  fGeomScintPosZCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fGeomMaskRadiusCmd =
      new G4UIcmdWithADoubleAndUnit("/scintillator/geom/maskRadius", this);
  fGeomMaskRadiusCmd->SetGuidance(
      "Set circular mask pass-through radius on scintillator +Z face (0 disables mask)");
  fGeomMaskRadiusCmd->SetParameterName("maskRadius", false);
  fGeomMaskRadiusCmd->SetUnitCategory("Length");
  fGeomMaskRadiusCmd->SetRange("maskRadius >= 0.");
  fGeomMaskRadiusCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fResolutionTargetEnabledCmd =
      new G4UIcmdWithAnInteger("/scintillator/geom/resolutionTargetEnabled", this);
  fResolutionTargetEnabledCmd->SetGuidance(
      "Enable Siemens star resolution target on scintillator +Z face: 0 or 1");
  fResolutionTargetEnabledCmd->SetParameterName("resolutionTargetEnabled", false);
  fResolutionTargetEnabledCmd->SetRange(
      "resolutionTargetEnabled >= 0 && resolutionTargetEnabled <= 1");
  fResolutionTargetEnabledCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fResolutionTargetOuterRadiusCmd = new G4UIcmdWithADoubleAndUnit(
      "/scintillator/geom/resolutionTargetOuterRadius", this);
  fResolutionTargetOuterRadiusCmd->SetGuidance(
      "Set Siemens star resolution target outer radius");
  fResolutionTargetOuterRadiusCmd->SetParameterName(
      "resolutionTargetOuterRadius", false);
  fResolutionTargetOuterRadiusCmd->SetUnitCategory("Length");
  fResolutionTargetOuterRadiusCmd->SetRange("resolutionTargetOuterRadius > 0.");
  fResolutionTargetOuterRadiusCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fResolutionTargetLinePairsCmd = new G4UIcmdWithAnInteger(
      "/scintillator/geom/resolutionTargetLinePairs", this);
  fResolutionTargetLinePairsCmd->SetGuidance(
      "Set Siemens star resolution target line-pair count");
  fResolutionTargetLinePairsCmd->SetParameterName(
      "resolutionTargetLinePairs", false);
  fResolutionTargetLinePairsCmd->SetRange("resolutionTargetLinePairs > 0");
  fResolutionTargetLinePairsCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fScintDensityCmd =
      new G4UIcmdWithADoubleAndUnit("/scintillator/properties/density", this);
  fScintDensityCmd->SetGuidance("Set scintillator density");
  fScintDensityCmd->SetParameterName("density", false);
  fScintDensityCmd->SetUnitCategory("Volumic Mass");
  fScintDensityCmd->SetRange("density > 0.");
  fScintDensityCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fScintCarbonAtomsCmd =
      new G4UIcmdWithAnInteger("/scintillator/properties/carbonAtoms", this);
  fScintCarbonAtomsCmd->SetGuidance("Set scintillator carbon atom count");
  fScintCarbonAtomsCmd->SetParameterName("carbonAtoms", false);
  fScintCarbonAtomsCmd->SetRange("carbonAtoms > 0");
  fScintCarbonAtomsCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fScintHydrogenAtomsCmd =
      new G4UIcmdWithAnInteger("/scintillator/properties/hydrogenAtoms", this);
  fScintHydrogenAtomsCmd->SetGuidance("Set scintillator hydrogen atom count");
  fScintHydrogenAtomsCmd->SetParameterName("hydrogenAtoms", false);
  fScintHydrogenAtomsCmd->SetRange("hydrogenAtoms > 0");
  fScintHydrogenAtomsCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fScintPhotonEnergyCmd =
      new G4UIcmdWithAString("/scintillator/properties/photonEnergy", this);
  fScintPhotonEnergyCmd->SetGuidance(
      "Set photon-energy nodes list (comma/space separated; optional trailing unit, default eV)");
  fScintPhotonEnergyCmd->SetParameterName("values", false);
  fScintPhotonEnergyCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fScintRIndexCmd = new G4UIcmdWithAString("/scintillator/properties/rIndex", this);
  fScintRIndexCmd->SetGuidance(
      "Set refractive-index list (comma/space separated, unitless)");
  fScintRIndexCmd->SetParameterName("values", false);
  fScintRIndexCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fScintAbsLengthCmd =
      new G4UIcmdWithAString("/scintillator/properties/absLength", this);
  fScintAbsLengthCmd->SetGuidance(
      "Set absorption-length list (comma/space separated; optional trailing unit, default cm)");
  fScintAbsLengthCmd->SetParameterName("values", false);
  fScintAbsLengthCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fScintSpectrumCmd =
      new G4UIcmdWithAString("/scintillator/properties/scintSpectrum", this);
  fScintSpectrumCmd->SetGuidance(
      "Set scintillation-spectrum list (comma/space separated, unitless)");
  fScintSpectrumCmd->SetParameterName("values", false);
  fScintSpectrumCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fScintYieldCmd =
      new G4UIcmdWithADouble("/scintillator/properties/scintYield", this);
  fScintYieldCmd->SetGuidance("Set scintillation yield in photons/MeV");
  fScintYieldCmd->SetParameterName("scintYield", false);
  fScintYieldCmd->SetRange("scintYield > 0.");
  fScintYieldCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fScintResolutionScaleCmd =
      new G4UIcmdWithADouble("/scintillator/properties/resolutionScale", this);
  fScintResolutionScaleCmd->SetGuidance("Set scintillation resolution scale");
  fScintResolutionScaleCmd->SetParameterName("resolutionScale", false);
  fScintResolutionScaleCmd->SetRange("resolutionScale > 0.");
  fScintResolutionScaleCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  for (std::size_t i = 0; i < fScintTimeConstantCmds.size(); ++i) {
    const auto componentNumber = std::to_string(i + 1);
    const auto timeCommand = "/scintillator/properties/timeConstant" + componentNumber;
    fScintTimeConstantCmds[i] =
        new G4UIcmdWithADoubleAndUnit(timeCommand.c_str(), this);
    fScintTimeConstantCmds[i]->SetGuidance(
        ("Set scintillation time constant for component " + componentNumber).c_str());
    fScintTimeConstantCmds[i]->SetParameterName("timeConstant", false);
    fScintTimeConstantCmds[i]->SetUnitCategory("Time");
    fScintTimeConstantCmds[i]->SetRange("timeConstant >= 0.");
    fScintTimeConstantCmds[i]->AvailableForStates(G4State_PreInit, G4State_Idle);

    const auto yieldCommand = "/scintillator/properties/yieldFraction" + componentNumber;
    fScintYieldFractionCmds[i] = new G4UIcmdWithADouble(yieldCommand.c_str(), this);
    fScintYieldFractionCmds[i]->SetGuidance(
        ("Set scintillation yield fraction for component " + componentNumber).c_str());
    fScintYieldFractionCmds[i]->SetParameterName("yieldFraction", false);
    fScintYieldFractionCmds[i]->SetRange("yieldFraction >= 0.");
    fScintYieldFractionCmds[i]->AvailableForStates(G4State_PreInit, G4State_Idle);
  }

  fOpticalInterfaceXCmd =
      new G4UIcmdWithADoubleAndUnit("/optical_interface/geom/sizeX", this);
  fOpticalInterfaceXCmd->SetGuidance(
      "Set optical-interface size in X (0 means inherit scintillator X)");
  fOpticalInterfaceXCmd->SetParameterName("sizeX", false);
  fOpticalInterfaceXCmd->SetUnitCategory("Length");
  fOpticalInterfaceXCmd->SetRange("sizeX >= 0.");
  fOpticalInterfaceXCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fOpticalInterfaceYCmd =
      new G4UIcmdWithADoubleAndUnit("/optical_interface/geom/sizeY", this);
  fOpticalInterfaceYCmd->SetGuidance(
      "Set optical-interface size in Y (0 means inherit scintillator Y)");
  fOpticalInterfaceYCmd->SetParameterName("sizeY", false);
  fOpticalInterfaceYCmd->SetUnitCategory("Length");
  fOpticalInterfaceYCmd->SetRange("sizeY >= 0.");
  fOpticalInterfaceYCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fOpticalInterfaceThicknessCmd =
      new G4UIcmdWithADoubleAndUnit("/optical_interface/geom/thickness", this);
  fOpticalInterfaceThicknessCmd->SetGuidance("Set optical-interface thickness in Z");
  fOpticalInterfaceThicknessCmd->SetParameterName("thickness", false);
  fOpticalInterfaceThicknessCmd->SetUnitCategory("Length");
  fOpticalInterfaceThicknessCmd->SetRange("thickness > 0.");
  fOpticalInterfaceThicknessCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fOpticalInterfacePosXCmd = new G4UIcmdWithADoubleAndUnit("/optical_interface/geom/posX", this);
  fOpticalInterfacePosXCmd->SetGuidance(
      "Set optical-interface center X position in world coordinates (default aligns with scintillator center)");
  fOpticalInterfacePosXCmd->SetParameterName("posX", false);
  fOpticalInterfacePosXCmd->SetUnitCategory("Length");
  fOpticalInterfacePosXCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fOpticalInterfacePosYCmd = new G4UIcmdWithADoubleAndUnit("/optical_interface/geom/posY", this);
  fOpticalInterfacePosYCmd->SetGuidance(
      "Set optical-interface center Y position in world coordinates (default aligns with scintillator center)");
  fOpticalInterfacePosYCmd->SetParameterName("posY", false);
  fOpticalInterfacePosYCmd->SetUnitCategory("Length");
  fOpticalInterfacePosYCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fOpticalInterfacePosZCmd = new G4UIcmdWithADoubleAndUnit("/optical_interface/geom/posZ", this);
  fOpticalInterfacePosZCmd->SetGuidance(
      "Set optical-interface center Z position in world coordinates (default is flush on scintillator +Z face when not set)");
  fOpticalInterfacePosZCmd->SetParameterName("posZ", false);
  fOpticalInterfacePosZCmd->SetUnitCategory("Length");
  fOpticalInterfacePosZCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fEventsPerOutputCmd = new G4UIcmdWithAnInteger("/output/eventsPerOutput", this);
  fEventsPerOutputCmd->SetGuidance(
      "Set number of Geant4 events accumulated before writing one Parquet part.");
  fEventsPerOutputCmd->SetParameterName("eventsPerOutput", false);
  fEventsPerOutputCmd->SetRange("eventsPerOutput > 0");
  fEventsPerOutputCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fWritePrimariesOutputCmd = new G4UIcmdWithAnInteger("/output/writePrimaries", this);
  fWritePrimariesOutputCmd->SetGuidance("Enable primary Parquet output: 0 or 1.");
  fWritePrimariesOutputCmd->SetParameterName("writePrimaries", false);
  fWritePrimariesOutputCmd->SetRange("writePrimaries >= 0 && writePrimaries <= 1");
  fWritePrimariesOutputCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fWriteSecondariesOutputCmd =
      new G4UIcmdWithAnInteger("/output/writeSecondaries", this);
  fWriteSecondariesOutputCmd->SetGuidance(
      "Enable secondary Parquet output: 0 or 1.");
  fWriteSecondariesOutputCmd->SetParameterName("writeSecondaries", false);
  fWriteSecondariesOutputCmd->SetRange(
      "writeSecondaries >= 0 && writeSecondaries <= 1");
  fWriteSecondariesOutputCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fWritePhotonsOutputCmd = new G4UIcmdWithAnInteger("/output/writePhotons", this);
  fWritePhotonsOutputCmd->SetGuidance("Enable photon Parquet output: 0 or 1.");
  fWritePhotonsOutputCmd->SetParameterName("writePhotons", false);
  fWritePhotonsOutputCmd->SetRange("writePhotons >= 0 && writePhotons <= 1");
  fWritePhotonsOutputCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fPrimariesOutputFileCmd = new G4UIcmdWithAString("/output/primariesFile", this);
  fPrimariesOutputFileCmd->SetGuidance("Set primaries Parquet output file.");
  fPrimariesOutputFileCmd->SetParameterName("primariesFile", false);
  fPrimariesOutputFileCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fSecondariesOutputFileCmd = new G4UIcmdWithAString("/output/secondariesFile", this);
  fSecondariesOutputFileCmd->SetGuidance("Set secondaries Parquet output file.");
  fSecondariesOutputFileCmd->SetParameterName("secondariesFile", false);
  fSecondariesOutputFileCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fPhotonsOutputFileCmd = new G4UIcmdWithAString("/output/photonsFile", this);
  fPhotonsOutputFileCmd->SetGuidance("Set photons Parquet output file.");
  fPhotonsOutputFileCmd->SetParameterName("photonsFile", false);
  fPhotonsOutputFileCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fSourceTimingModeCmd = new G4UIcmdWithAString("/source/timing/mode", this);
  fSourceTimingModeCmd->SetGuidance(
      "Set source timing mode: none, continuous, or pulsed");
  fSourceTimingModeCmd->SetParameterName("mode", false);
  fSourceTimingModeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fSourceTimingStartTimeCmd =
      new G4UIcmdWithADoubleAndUnit("/source/timing/startTime", this);
  fSourceTimingStartTimeCmd->SetGuidance("Set source timing start time");
  fSourceTimingStartTimeCmd->SetParameterName("startTime", false);
  fSourceTimingStartTimeCmd->SetUnitCategory("Time");
  fSourceTimingStartTimeCmd->SetRange("startTime >= 0.");
  fSourceTimingStartTimeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fSourceTimingEventSpacingCmd =
      new G4UIcmdWithADoubleAndUnit("/source/timing/eventSpacing", this);
  fSourceTimingEventSpacingCmd->SetGuidance(
      "Set fixed source-time spacing for continuous mode");
  fSourceTimingEventSpacingCmd->SetParameterName("eventSpacing", false);
  fSourceTimingEventSpacingCmd->SetUnitCategory("Time");
  fSourceTimingEventSpacingCmd->SetRange("eventSpacing > 0.");
  fSourceTimingEventSpacingCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fSourceTimingPulsePeriodCmd =
      new G4UIcmdWithADoubleAndUnit("/source/timing/pulsePeriod", this);
  fSourceTimingPulsePeriodCmd->SetGuidance("Set pulse period for pulsed mode");
  fSourceTimingPulsePeriodCmd->SetParameterName("pulsePeriod", false);
  fSourceTimingPulsePeriodCmd->SetUnitCategory("Time");
  fSourceTimingPulsePeriodCmd->SetRange("pulsePeriod > 0.");
  fSourceTimingPulsePeriodCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fSourceTimingNeutronsPerPulseCmd =
      new G4UIcmdWithAnInteger("/source/timing/neutronsPerPulse", this);
  fSourceTimingNeutronsPerPulseCmd->SetGuidance(
      "Set number of generated neutron events assigned to each pulse");
  fSourceTimingNeutronsPerPulseCmd->SetParameterName("neutronsPerPulse", false);
  fSourceTimingNeutronsPerPulseCmd->SetRange("neutronsPerPulse > 0");
  fSourceTimingNeutronsPerPulseCmd->AvailableForStates(G4State_PreInit,
                                                       G4State_Idle);

  fSourceTimingPulseTimeOffsetCmd =
      new G4UIcmdWithADoubleAndUnit("/source/timing/pulseTimeOffset", this);
  fSourceTimingPulseTimeOffsetCmd->SetGuidance(
      "Set offset between T-zero and pulse start for pulsed mode");
  fSourceTimingPulseTimeOffsetCmd->SetParameterName("pulseTimeOffset", false);
  fSourceTimingPulseTimeOffsetCmd->SetUnitCategory("Time");
  fSourceTimingPulseTimeOffsetCmd->SetRange("pulseTimeOffset >= 0.");
  fSourceTimingPulseTimeOffsetCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fSourceTimingPulseTimeWidthCmd =
      new G4UIcmdWithADoubleAndUnit("/source/timing/pulseTimeWidth", this);
  fSourceTimingPulseTimeWidthCmd->SetGuidance(
      "Set random creation-time window width for pulsed mode");
  fSourceTimingPulseTimeWidthCmd->SetParameterName("pulseTimeWidth", false);
  fSourceTimingPulseTimeWidthCmd->SetUnitCategory("Time");
  fSourceTimingPulseTimeWidthCmd->SetRange("pulseTimeWidth >= 0.");
  fSourceTimingPulseTimeWidthCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fSourceTimingPulseShapeCmd =
      new G4UIcmdWithAString("/source/timing/pulseShape", this);
  fSourceTimingPulseShapeCmd->SetGuidance(
      "Set pulsed source-time distribution shape; currently uniform");
  fSourceTimingPulseShapeCmd->SetParameterName("pulseShape", false);
  fSourceTimingPulseShapeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fPhotonCullingEnabledCmd =
      new G4UIcmdWithAnInteger("/photonCulling/enabled", this);
  fPhotonCullingEnabledCmd->SetGuidance(
      "Enable or disable photon culling optimization (0=disabled, 1=enabled)");
  fPhotonCullingEnabledCmd->SetParameterName("enabled", false);
  fPhotonCullingEnabledCmd->SetRange("enabled >= 0 && enabled <= 1");
  fPhotonCullingEnabledCmd->AvailableForStates(G4State_PreInit, G4State_Idle);

  fPhotonCullingAcceptanceAngleDegCmd =
      new G4UIcmdWithADouble("/photonCulling/acceptanceAngleDeg", this);
  fPhotonCullingAcceptanceAngleDegCmd->SetGuidance(
      "Set acceptance cone angle in degrees for photon culling");
  fPhotonCullingAcceptanceAngleDegCmd->SetParameterName("acceptanceAngleDeg", false);
  fPhotonCullingAcceptanceAngleDegCmd->SetRange("acceptanceAngleDeg > 0. && acceptanceAngleDeg <= 180.");
  fPhotonCullingAcceptanceAngleDegCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

Messenger::~Messenger() {
  delete fPhotonCullingAcceptanceAngleDegCmd;
  delete fPhotonCullingEnabledCmd;

  delete fSourceTimingPulseShapeCmd;
  delete fSourceTimingPulseTimeWidthCmd;
  delete fSourceTimingPulseTimeOffsetCmd;
  delete fSourceTimingNeutronsPerPulseCmd;
  delete fSourceTimingPulsePeriodCmd;
  delete fSourceTimingEventSpacingCmd;
  delete fSourceTimingStartTimeCmd;
  delete fSourceTimingModeCmd;

  delete fPhotonsOutputFileCmd;
  delete fSecondariesOutputFileCmd;
  delete fPrimariesOutputFileCmd;
  delete fWritePhotonsOutputCmd;
  delete fWriteSecondariesOutputCmd;
  delete fWritePrimariesOutputCmd;
  delete fEventsPerOutputCmd;

  delete fOpticalInterfacePosZCmd;
  delete fOpticalInterfacePosYCmd;
  delete fOpticalInterfacePosXCmd;

  delete fOpticalInterfaceThicknessCmd;
  delete fOpticalInterfaceYCmd;
  delete fOpticalInterfaceXCmd;

  delete fGeomScintPosZCmd;
  delete fGeomScintPosYCmd;
  delete fGeomScintPosXCmd;
  for (auto* command : fScintYieldFractionCmds) {
    delete command;
  }
  for (auto* command : fScintTimeConstantCmds) {
    delete command;
  }
  delete fScintResolutionScaleCmd;
  delete fScintYieldCmd;
  delete fScintSpectrumCmd;
  delete fScintAbsLengthCmd;
  delete fScintRIndexCmd;
  delete fScintPhotonEnergyCmd;
  delete fScintHydrogenAtomsCmd;
  delete fScintCarbonAtomsCmd;
  delete fScintDensityCmd;
  delete fResolutionTargetLinePairsCmd;
  delete fResolutionTargetOuterRadiusCmd;
  delete fResolutionTargetEnabledCmd;
  delete fGeomMaskRadiusCmd;
  delete fGeomScintZCmd;
  delete fGeomScintYCmd;
  delete fGeomScintXCmd;
  delete fGeomMaterialCmd;

  delete fPhotonCullingDir;
  delete fOutputDir;
  delete fSourceTimingDir;
  delete fSourceDir;
  delete fOpticalInterfaceGeomDir;
  delete fOpticalInterfaceDir;
  delete fScintillatorPropertiesDir;
  delete fScintillatorGeomDir;
  delete fScintillatorDir;
}

void Messenger::SetNewValue(G4UIcommand* command, G4String newValue) {
  if (!fConfig) {
    return;
  }

  if (command == fGeomMaterialCmd) {
    fConfig->SetScintMaterial(newValue);
    G4cout << "Scintillator material set to '" << newValue
           << "'. Run /run/initialize before /beamOn." << G4endl;
    NotifyGeometryChanged();
    return;
  }

  if (command == fGeomScintXCmd) {
    fConfig->SetScintX(fGeomScintXCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fGeomScintYCmd) {
    fConfig->SetScintY(fGeomScintYCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fGeomScintZCmd) {
    fConfig->SetScintZ(fGeomScintZCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fGeomScintPosXCmd) {
    fConfig->SetScintPosX(fGeomScintPosXCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fGeomScintPosYCmd) {
    fConfig->SetScintPosY(fGeomScintPosYCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fGeomScintPosZCmd) {
    fConfig->SetScintPosZ(fGeomScintPosZCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fGeomMaskRadiusCmd) {
    fConfig->SetMaskRadius(
        fGeomMaskRadiusCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fResolutionTargetEnabledCmd) {
    fConfig->SetResolutionTargetEnabled(
        fResolutionTargetEnabledCmd->GetNewIntValue(newValue) != 0);
    NotifyGeometryChanged();
    return;
  }

  if (command == fResolutionTargetOuterRadiusCmd) {
    fConfig->SetResolutionTargetOuterRadius(
        fResolutionTargetOuterRadiusCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fResolutionTargetLinePairsCmd) {
    fConfig->SetResolutionTargetLinePairs(
        fResolutionTargetLinePairsCmd->GetNewIntValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fScintDensityCmd) {
    fConfig->SetScintDensity(fScintDensityCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fScintCarbonAtomsCmd) {
    fConfig->SetScintCarbonAtoms(fScintCarbonAtomsCmd->GetNewIntValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fScintHydrogenAtomsCmd) {
    fConfig->SetScintHydrogenAtoms(fScintHydrogenAtomsCmd->GetNewIntValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fScintPhotonEnergyCmd) {
    std::vector<G4double> values;
    std::string unit = "eV";
    if (!ParseListWithOptionalUnit(newValue, &values, &unit)) {
      G4cout << "Failed to parse photonEnergy list: '" << newValue << "'." << G4endl;
      return;
    }
    if (!G4UnitDefinition::IsUnitDefined(unit)) {
      G4cout << "Unknown photonEnergy unit '" << unit << "'." << G4endl;
      return;
    }
    const G4double factor = G4UIcommand::ValueOf(unit.c_str());
    for (auto& value : values) {
      value *= factor;
    }
    fConfig->SetScintPhotonEnergy(values);
    NotifyGeometryChanged();
    return;
  }

  if (command == fScintRIndexCmd) {
    std::vector<G4double> values;
    std::string unit;
    if (!ParseListWithOptionalUnit(newValue, &values, &unit)) {
      G4cout << "Failed to parse rIndex list: '" << newValue << "'." << G4endl;
      return;
    }
    if (!unit.empty() && unit != "unitless") {
      G4cout << "rIndex list does not accept unit token '" << unit << "'." << G4endl;
      return;
    }
    fConfig->SetScintRIndex(values);
    NotifyGeometryChanged();
    return;
  }

  if (command == fScintAbsLengthCmd) {
    std::vector<G4double> values;
    std::string unit = "cm";
    if (!ParseListWithOptionalUnit(newValue, &values, &unit)) {
      G4cout << "Failed to parse absLength list: '" << newValue << "'." << G4endl;
      return;
    }
    if (!G4UnitDefinition::IsUnitDefined(unit)) {
      G4cout << "Unknown absLength unit '" << unit << "'." << G4endl;
      return;
    }
    const G4double factor = G4UIcommand::ValueOf(unit.c_str());
    for (auto& value : values) {
      value *= factor;
    }
    fConfig->SetScintAbsLength(values);
    NotifyGeometryChanged();
    return;
  }

  if (command == fScintSpectrumCmd) {
    std::vector<G4double> values;
    std::string unit;
    if (!ParseListWithOptionalUnit(newValue, &values, &unit)) {
      G4cout << "Failed to parse scintSpectrum list: '" << newValue << "'." << G4endl;
      return;
    }
    if (!unit.empty() && unit != "unitless") {
      G4cout << "scintSpectrum list does not accept unit token '" << unit << "'."
             << G4endl;
      return;
    }
    fConfig->SetScintSpectrum(values);
    NotifyGeometryChanged();
    return;
  }

  if (command == fScintYieldCmd) {
    fConfig->SetScintYield(fScintYieldCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fScintResolutionScaleCmd) {
    fConfig->SetScintResolutionScale(
        fScintResolutionScaleCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  for (std::size_t i = 0; i < fScintTimeConstantCmds.size(); ++i) {
    if (command == fScintTimeConstantCmds[i]) {
      fConfig->SetScintTimeConstant(
          static_cast<G4int>(i + 1),
          fScintTimeConstantCmds[i]->GetNewDoubleValue(newValue));
      NotifyGeometryChanged();
      return;
    }
  }

  for (std::size_t i = 0; i < fScintYieldFractionCmds.size(); ++i) {
    if (command == fScintYieldFractionCmds[i]) {
      fConfig->SetScintYieldFraction(
          static_cast<G4int>(i + 1),
          fScintYieldFractionCmds[i]->GetNewDoubleValue(newValue));
      NotifyGeometryChanged();
      return;
    }
  }

  if (command == fOpticalInterfaceXCmd) {
    fConfig->SetOpticalInterfaceX(fOpticalInterfaceXCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fOpticalInterfaceYCmd) {
    fConfig->SetOpticalInterfaceY(fOpticalInterfaceYCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fOpticalInterfaceThicknessCmd) {
    fConfig->SetOpticalInterfaceThickness(fOpticalInterfaceThicknessCmd->GetNewDoubleValue(newValue));
    NotifyGeometryChanged();
    return;
  }

  if (command == fOpticalInterfacePosXCmd) {
    const auto value = fOpticalInterfacePosXCmd->GetNewDoubleValue(newValue);
    fConfig->SetOpticalInterfacePosX(value);
    G4cout << "Optical-interface posX set to " << value / mm << " mm." << G4endl;
    NotifyGeometryChanged();
    return;
  }

  if (command == fOpticalInterfacePosYCmd) {
    const auto value = fOpticalInterfacePosYCmd->GetNewDoubleValue(newValue);
    fConfig->SetOpticalInterfacePosY(value);
    G4cout << "Optical-interface posY set to " << value / mm << " mm." << G4endl;
    NotifyGeometryChanged();
    return;
  }

  if (command == fOpticalInterfacePosZCmd) {
    const auto value = fOpticalInterfacePosZCmd->GetNewDoubleValue(newValue);
    fConfig->SetOpticalInterfacePosZ(value);
    G4cout << "Optical-interface posZ set to " << value / mm << " mm." << G4endl;
    NotifyGeometryChanged();
    return;
  }

  if (command == fSourceTimingModeCmd) {
    fConfig->SetSourceTimingMode(newValue);
    G4cout << "Source timing mode set to '" << newValue << "'." << G4endl;
    return;
  }

  if (command == fSourceTimingStartTimeCmd) {
    const auto value = fSourceTimingStartTimeCmd->GetNewDoubleValue(newValue);
    fConfig->SetSourceTimingStartTime(value);
    G4cout << "Source timing start time set to " << value / ns << " ns."
           << G4endl;
    return;
  }

  if (command == fSourceTimingEventSpacingCmd) {
    const auto value = fSourceTimingEventSpacingCmd->GetNewDoubleValue(newValue);
    fConfig->SetSourceTimingEventSpacing(value);
    G4cout << "Source timing event spacing set to " << value / ns << " ns."
           << G4endl;
    return;
  }

  if (command == fSourceTimingPulsePeriodCmd) {
    const auto value = fSourceTimingPulsePeriodCmd->GetNewDoubleValue(newValue);
    fConfig->SetSourceTimingPulsePeriod(value);
    G4cout << "Source timing pulse period set to " << value / ns << " ns."
           << G4endl;
    return;
  }

  if (command == fSourceTimingNeutronsPerPulseCmd) {
    const auto value = fSourceTimingNeutronsPerPulseCmd->GetNewIntValue(newValue);
    fConfig->SetSourceTimingNeutronsPerPulse(value);
    G4cout << "Source timing neutrons per pulse set to " << value << "."
           << G4endl;
    return;
  }

  if (command == fSourceTimingPulseTimeOffsetCmd) {
    const auto value = fSourceTimingPulseTimeOffsetCmd->GetNewDoubleValue(newValue);
    fConfig->SetSourceTimingPulseTimeOffset(value);
    G4cout << "Source timing pulse time offset set to " << value / ns << " ns."
           << G4endl;
    return;
  }

  if (command == fSourceTimingPulseTimeWidthCmd) {
    const auto value = fSourceTimingPulseTimeWidthCmd->GetNewDoubleValue(newValue);
    fConfig->SetSourceTimingPulseTimeWidth(value);
    G4cout << "Source timing pulse time width set to " << value / ns << " ns."
           << G4endl;
    return;
  }

  if (command == fSourceTimingPulseShapeCmd) {
    fConfig->SetSourceTimingPulseShape(newValue);
    G4cout << "Source timing pulse shape set to '" << newValue << "'." << G4endl;
    return;
  }

  if (command == fPrimariesOutputFileCmd) {
    fConfig->SetPrimariesOutputFile(newValue);
    G4cout << "Primaries Parquet output file set to '"
           << fConfig->GetPrimariesOutputFile() << "'." << G4endl;
    return;
  }

  if (command == fEventsPerOutputCmd) {
    fConfig->SetEventsPerOutput(fEventsPerOutputCmd->GetNewIntValue(newValue));
    G4cout << "Parquet events per output part set to "
           << fConfig->GetEventsPerOutput() << "." << G4endl;
    return;
  }

  if (command == fWritePrimariesOutputCmd) {
    fConfig->SetWritePrimariesOutput(
        fWritePrimariesOutputCmd->GetNewIntValue(newValue) != 0);
    G4cout << "Primary Parquet output "
           << (fConfig->GetWritePrimariesOutput() ? "enabled" : "disabled")
           << "." << G4endl;
    return;
  }

  if (command == fWriteSecondariesOutputCmd) {
    fConfig->SetWriteSecondariesOutput(
        fWriteSecondariesOutputCmd->GetNewIntValue(newValue) != 0);
    G4cout << "Secondary Parquet output "
           << (fConfig->GetWriteSecondariesOutput() ? "enabled" : "disabled")
           << "." << G4endl;
    return;
  }

  if (command == fWritePhotonsOutputCmd) {
    fConfig->SetWritePhotonsOutput(
        fWritePhotonsOutputCmd->GetNewIntValue(newValue) != 0);
    G4cout << "Photon Parquet output "
           << (fConfig->GetWritePhotonsOutput() ? "enabled" : "disabled")
           << "." << G4endl;
    return;
  }

  if (command == fSecondariesOutputFileCmd) {
    fConfig->SetSecondariesOutputFile(newValue);
    G4cout << "Secondaries Parquet output file set to '"
           << fConfig->GetSecondariesOutputFile() << "'." << G4endl;
    return;
  }

  if (command == fPhotonsOutputFileCmd) {
    fConfig->SetPhotonsOutputFile(newValue);
    G4cout << "Photons Parquet output file set to '"
           << fConfig->GetPhotonsOutputFile() << "'." << G4endl;
    return;
  }

  if (command == fPhotonCullingEnabledCmd) {
    fConfig->SetPhotonCullingEnabled(
        fPhotonCullingEnabledCmd->GetNewIntValue(newValue) != 0);
    G4cout << "Photon culling "
           << (fConfig->GetPhotonCullingEnabled() ? "enabled" : "disabled")
           << "." << G4endl;
    return;
  }

  if (command == fPhotonCullingAcceptanceAngleDegCmd) {
    const auto value = fPhotonCullingAcceptanceAngleDegCmd->GetNewDoubleValue(newValue);
    fConfig->SetPhotonCullingAcceptanceAngleDeg(value);
    G4cout << "Photon culling acceptance angle set to " << value << " degrees."
           << G4endl;
    return;
  }
}

void Messenger::NotifyGeometryChanged() const {
  auto* runManager = G4RunManager::GetRunManager();
  if (runManager) {
    // Mark geometry dirty; users can rebuild with reinitialize/initialize commands.
    runManager->GeometryHasBeenModified();
  }
  G4cout << "Geometry updated. Run /run/reinitializeGeometry, then /run/initialize, then /vis/drawVolume."
         << G4endl;
}
