#include "RunAction.hh"

#include "EventAction.hh"
#include "config.hh"

#include "G4Exception.hh"
#include "G4ExceptionSeverity.hh"
#include "G4Run.hh"
#include "G4ios.hh"

#include <atomic>
#include <cstdint>
#include <filesystem>
#include <string>

namespace {
// Return true when the output path has no parent or its parent exists.
bool ParentDirectoryExists(const std::string& outputFilePath) {
  const std::filesystem::path parent =
      std::filesystem::path(outputFilePath).parent_path();
  if (parent.empty()) {
    return true;
  }
  std::error_code ec;
  return std::filesystem::exists(parent, ec) && !ec;
}
}  // namespace

RunAction::RunAction(const Config* config) : fConfig(config) {}

void RunAction::BeginOfRunAction(const G4Run* /*run*/) {
  // Validate once on master before worker dispatch.
  if (!IsMaster() || fConfig == nullptr) {
    return;
  }

  std::string missingPaths;

  const SimIO::HDF5OutputPaths paths = {
      fConfig->GetPrimariesOutputFile(),
      fConfig->GetSecondariesOutputFile(),
      fConfig->GetPhotonsOutputFile(),
  };
  const SimIO::HDF5OutputSelection selection = {
      fConfig->GetWritePrimariesOutput(),
      fConfig->GetWriteSecondariesOutput(),
      fConfig->GetWritePhotonsOutput(),
  };

  if (fConfig->GetWritePrimariesOutput() && !ParentDirectoryExists(paths.primaries)) {
    missingPaths += "  - HDF5 primaries target: " + paths.primaries + "\n";
  }
  if (fConfig->GetWriteSecondariesOutput() &&
      !ParentDirectoryExists(paths.secondaries)) {
    missingPaths += "  - HDF5 secondaries target: " + paths.secondaries + "\n";
  }
  if (fConfig->GetWritePhotonsOutput() && !ParentDirectoryExists(paths.photons)) {
    missingPaths += "  - HDF5 photons target: " + paths.photons + "\n";
  }

  if (!missingPaths.empty()) {
    G4ExceptionDescription message;
    message
        << "Output directory validation failed before run start.\n"
        << "Expected output parent directories do not exist:\n"
        << missingPaths
        << "Create directories in Python before launching Geant4 "
        << "(for example via ConfigIO.ensure_output_directories / write_macro).";

    G4Exception("RunAction::BeginOfRunAction", "scintipix/output/missing-directory",
                FatalException, message);
  }

  // Initialize HDF5 files before workers start
  std::string error;
  if (!SimIO::InitHDF5(paths, selection, &error)) {
    G4ExceptionDescription message;
    message << "Failed to initialize HDF5 output files: " << error;
    G4Exception("RunAction::BeginOfRunAction", "scintipix/output/hdf5-init-failed",
                FatalException, message);
  }
}

void RunAction::EndOfRunAction(const G4Run* /*run*/) {
  if (auto* eventAction = EventAction::Instance()) {
    eventAction->FlushOutputRows();
  }

  // Close HDF5 file handles
  if (fConfig) {
    SimIO::CloseHDF5(fConfig->GetPrimariesOutputFile());
    SimIO::CloseHDF5(fConfig->GetSecondariesOutputFile());
    SimIO::CloseHDF5(fConfig->GetPhotonsOutputFile());
  }
}
