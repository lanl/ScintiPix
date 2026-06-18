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

  const SimIO::OutputPaths paths = {
      fConfig->GetPrimariesOutputFile(),
      fConfig->GetSecondariesOutputFile(),
      fConfig->GetPhotonsOutputFile(),
  };
  const SimIO::OutputSelection selection = {
      fConfig->GetWritePrimariesOutput(),
      fConfig->GetWriteSecondariesOutput(),
      fConfig->GetWritePhotonsOutput(),
  };

  if (fConfig->GetWritePrimariesOutput() && !ParentDirectoryExists(paths.primaries)) {
    missingPaths += "  - Primaries output: " + paths.primaries + "\n";
  }
  if (fConfig->GetWriteSecondariesOutput() &&
      !ParentDirectoryExists(paths.secondaries)) {
    missingPaths += "  - Secondaries output: " + paths.secondaries + "\n";
  }
  if (fConfig->GetWritePhotonsOutput() && !ParentDirectoryExists(paths.photons)) {
    missingPaths += "  - Photons output: " + paths.photons + "\n";
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

  // NOTE: Binary files are created lazily on first append
  // No explicit initialization needed
}

void RunAction::EndOfRunAction(const G4Run* /*run*/) {
  if (auto* eventAction = EventAction::Instance()) {
    eventAction->FlushOutputRows();
  }

  // Close output file handles (no-op for binary files)
  if (fConfig) {
    SimIO::CloseOutput(fConfig->GetPrimariesOutputFile());
    SimIO::CloseOutput(fConfig->GetSecondariesOutputFile());
    SimIO::CloseOutput(fConfig->GetPhotonsOutputFile());
  }
}
