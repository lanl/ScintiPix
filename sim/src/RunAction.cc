#include "RunAction.hh"

#include "config.hh"

#include "G4Exception.hh"
#include "G4ExceptionSeverity.hh"
#include "G4Run.hh"
#include "G4ios.hh"

#include <filesystem>
#include <mutex>
#include <string>
#include <vector>

namespace {
std::mutex gOutputRowsMutex;
std::vector<SimIO::PrimaryInfo> gPrimaryRows;
std::vector<SimIO::SecondaryInfo> gSecondaryRows;
std::vector<SimIO::PhotonInfo> gPhotonRows;

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

  {
    std::lock_guard<std::mutex> lock(gOutputRowsMutex);
    gPrimaryRows.clear();
    gSecondaryRows.clear();
    gPhotonRows.clear();
  }

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
  if (!IsMaster() || fConfig == nullptr) {
    return;
  }

  std::vector<SimIO::PrimaryInfo> primaryRows;
  std::vector<SimIO::SecondaryInfo> secondaryRows;
  std::vector<SimIO::PhotonInfo> photonRows;
  {
    std::lock_guard<std::mutex> lock(gOutputRowsMutex);
    primaryRows = gPrimaryRows;
    secondaryRows = gSecondaryRows;
    photonRows = gPhotonRows;
  }

  const SimIO::ParquetOutputPaths paths = {
      fConfig->GetPrimariesOutputFile(),
      fConfig->GetSecondariesOutputFile(),
      fConfig->GetPhotonsOutputFile(),
  };

  std::string error;
  if (!SimIO::WriteParquet(paths, primaryRows, secondaryRows, photonRows, &error)) {
    if (error.empty()) {
      G4cout << "Failed writing Parquet output." << G4endl;
    } else {
      G4cout << error << G4endl;
    }
  }
}

void RunAction::AppendOutputRows(
    const std::vector<SimIO::PrimaryInfo>& primaryRows,
    const std::vector<SimIO::SecondaryInfo>& secondaryRows,
    const std::vector<SimIO::PhotonInfo>& photonRows) {
  std::lock_guard<std::mutex> lock(gOutputRowsMutex);
  gPrimaryRows.insert(gPrimaryRows.end(), primaryRows.begin(), primaryRows.end());
  gSecondaryRows.insert(gSecondaryRows.end(), secondaryRows.begin(),
                        secondaryRows.end());
  gPhotonRows.insert(gPhotonRows.end(), photonRows.begin(), photonRows.end());
}
