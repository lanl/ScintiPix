#include "RunAction.hh"

#include "EventAction.hh"
#include "SimIO.hh"
#include "config.hh"

#include "G4Exception.hh"
#include "G4ExceptionSeverity.hh"
#include "G4Run.hh"
#include "G4ios.hh"

#include <string>

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

  if (!SimIO::InitOutput(paths, selection, &missingPaths)) {
    G4ExceptionDescription message;
    message
        << "Output initialization failed before run start.\n"
        << "Could not initialize binary output files:\n"
        << missingPaths
        << "Create directories in Python before launching Geant4 "
        << "(for example via ConfigIO.ensure_output_directories / write_macro).";

    G4Exception("RunAction::BeginOfRunAction", "scintipix/output/init-failed",
                FatalException, message);
  }
}

void RunAction::EndOfRunAction(const G4Run* /*run*/) {
  if (auto* eventAction = EventAction::Instance()) {
    eventAction->FlushOutputRows();
  }

  // Close output file handles for this thread.
  if (fConfig) {
    SimIO::CloseOutput(fConfig->GetPrimariesOutputFile());
    SimIO::CloseOutput(fConfig->GetSecondariesOutputFile());
    SimIO::CloseOutput(fConfig->GetPhotonsOutputFile());
  }
}
