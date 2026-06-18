#ifndef TrackingAction_h
#define TrackingAction_h 1

#include "G4UserTrackingAction.hh"
#include "G4ThreeVector.hh"

class Config;
class EventAction;
class G4Track;

/// Per-track hook that records ancestry/origin metadata at track start.
class TrackingAction : public G4UserTrackingAction {
 public:
  /// `eventAction` receives track and photon creation context.
  TrackingAction(EventAction* eventAction, const Config* config);
  ~TrackingAction() override = default;

  /// Called by Geant4 before each track is processed.
  void PreUserTrackingAction(const G4Track* track) override;

 private:
  /// Event-local sink for per-track metadata.
  EventAction* fEventAction = nullptr;
  /// Runtime configuration for photon culling parameters.
  const Config* fConfig = nullptr;

  /// Photon culling: check if photon is emitted toward detector
  bool ShouldCullPhoton(const G4ThreeVector& photonDirection,
                       const G4ThreeVector& photonOrigin,
                       const G4ThreeVector& detectorCenter) const;
};

#endif
