#ifndef RunAction_h
#define RunAction_h 1

#include "SimIO.hh"

#include "G4UserRunAction.hh"

#include <vector>

class G4Run;
class Config;

/// Run-level validation before event processing starts.
class RunAction : public G4UserRunAction {
 public:
  explicit RunAction(const Config* config);
  ~RunAction() override = default;

  /// Validate output paths on run start.
  void BeginOfRunAction(const G4Run* run) override;
  /// Write accumulated output rows once after the run.
  void EndOfRunAction(const G4Run* run) override;

  static void AppendOutputRows(const std::vector<SimIO::PrimaryInfo>& primaryRows,
                               const std::vector<SimIO::SecondaryInfo>& secondaryRows,
                               const std::vector<SimIO::PhotonInfo>& photonRows);

 private:
  /// Read-only runtime configuration source.
  const Config* fConfig = nullptr;
};

#endif
