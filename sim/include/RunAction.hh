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
  /// Flush any remaining worker-local output rows after the run.
  void EndOfRunAction(const G4Run* run) override;

  /// Reserve the next unique Parquet part index for a worker flush.
  static std::uint64_t NextOutputPartIndex();

 private:
  /// Read-only runtime configuration source.
  const Config* fConfig = nullptr;
};

#endif
