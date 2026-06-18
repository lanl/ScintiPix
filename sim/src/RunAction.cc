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
std::atomic<std::uint64_t> gNextOutputPartIndex{0};

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

  gNextOutputPartIndex.store(0);

  std::string missingPaths;

  const SimIO::ParquetOutputPaths paths = {
      fConfig->GetPrimariesOutputFile(),
      fConfig->GetSecondariesOutputFile(),
      fConfig->GetPhotonsOutputFile(),
  };
  if (!ParentDirectoryExists(paths.primaries)) {
    missingPaths += "  - Parquet primaries target: " + paths.primaries + "\n";
  }
  if (!ParentDirectoryExists(paths.secondaries)) {
    missingPaths += "  - Parquet secondaries target: " + paths.secondaries + "\n";
  }
  if (!ParentDirectoryExists(paths.photons)) {
    missingPaths += "  - Parquet photons target: " + paths.photons + "\n";
  }

  if (missingPaths.empty()) {
    return;
  }

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

void RunAction::EndOfRunAction(const G4Run* /*run*/) {
  if (auto* eventAction = EventAction::Instance()) {
    eventAction->FlushOutputRows();
  }
}

std::uint64_t RunAction::NextOutputPartIndex() {
  return gNextOutputPartIndex.fetch_add(1);
}
