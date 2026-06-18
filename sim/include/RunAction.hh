#ifndef RunAction_h
#define RunAction_h 1

#include "G4UserRunAction.hh"

#include <cstdint>

class G4Run;
class Config;

/// Run-level validation before event processing starts.
class RunAction : public G4UserRunAction {
 public:
  explicit RunAction(const Config* config);
  ~RunAction() override = default;

  /// Validate output paths on run start.
  void BeginOfRunAction(const G4Run* run) override;
  /// Flush any remaining worker-local output rows after the run and close output files.
  void EndOfRunAction(const G4Run* run) override;

 private:
  /// Read-only runtime configuration source.
  const Config* fConfig = nullptr;
};

#endif
