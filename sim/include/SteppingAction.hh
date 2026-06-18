#ifndef SteppingAction_h
#define SteppingAction_h 1

#include "G4UserSteppingAction.hh"
#include "G4ThreeVector.hh"

class Config;
class DetectorConstruction;
class EventAction;
class G4Step;

/// Per-step hook that records scintillator interactions and photon context.
class SteppingAction : public G4UserSteppingAction {
  public:
    /// Requires detector geometry access and event-level accumulator.
    SteppingAction(const DetectorConstruction* detector, EventAction* eventAction, const Config* config);
    ~SteppingAction() override = default;

    /// Process one Geant4 step (filtered to the scintillator scoring volume).
    void UserSteppingAction(const G4Step* step) override;

  private:
    /// Geometry access (for scoring-volume lookup).
    const DetectorConstruction* fDetector = nullptr;
    /// Event-local sink for recorded step-derived state.
    EventAction* fEventAction = nullptr;
    /// Runtime configuration for photon culling parameters.
    const Config* fConfig = nullptr;
    
    /// Photon culling: check if photon is emitted toward detector
    bool ShouldCullPhoton(const G4ThreeVector& photonDirection, 
                         const G4ThreeVector& scintillatorCenter,
                         const G4ThreeVector& detectorCenter) const;
};

#endif
