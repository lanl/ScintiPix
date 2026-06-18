#include "SteppingAction.hh"

#include "DetectorConstruction.hh"
#include "EventAction.hh"
#include "config.hh"

#include "G4LogicalVolume.hh"
#include "G4OpticalPhoton.hh"
#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4StepStatus.hh"
#include "G4SystemOfUnits.hh"
#include "G4Track.hh"
#include "G4TouchableHandle.hh"
#include "G4VProcess.hh"
#include "G4VPhysicalVolume.hh"

namespace {
bool IsInteractionProcess(const G4VProcess* process) {
  if (!process) {
    return false;
  }
  const auto& processName = process->GetProcessName();
  return processName != "Transportation" && processName != "CoupledTransportation";
}

G4int ResolvePrimaryTrackID(const G4Track* track, const EventAction* eventAction) {
  if (!track || !eventAction) {
    return -1;
  }
  if (track->GetParentID() == 0) {
    return track->GetTrackID();
  }
  if (const auto* trackInfo = eventAction->FindTrackInfo(track->GetTrackID())) {
    return trackInfo->primaryTrackID;
  }
  return -1;
}
}  // namespace

SteppingAction::SteppingAction(const DetectorConstruction* detector,
                                EventAction* eventAction, const Config* config)
    : fDetector(detector), fEventAction(eventAction), fConfig(config) {}

bool SteppingAction::ShouldCullPhoton(const G4ThreeVector& photonDirection, 
                                     const G4ThreeVector& scintillatorCenter,
                                     const G4ThreeVector& detectorCenter) const {
  // If culling is disabled, don't cull any photons
  if (!fConfig || !fConfig->GetPhotonCullingEnabled()) {
    return false;
  }
  
  // Get acceptance angle from config (convert to radians for calculation)
  G4double acceptanceAngleRad = fConfig->GetPhotonCullingAcceptanceAngleDeg() * CLHEP::pi / 180.0;
  G4double cosAcceptanceAngle = std::cos(acceptanceAngleRad);
  
  // Calculate vector from scintillator center to detector center
  G4ThreeVector toDetector = detectorCenter - scintillatorCenter;
  
  // If the vector is zero (same position), don't cull
  if (toDetector.mag2() == 0.0) {
    return false;
  }
  
  // Normalize the vectors
  G4ThreeVector photonDirNorm = photonDirection.unit();
  G4ThreeVector toDetectorNorm = toDetector.unit();
  
  // Calculate cosine of angle between photon direction and detector direction
  G4double cosAngle = photonDirNorm.dot(toDetectorNorm);
  
  // If cosine of angle is less than cosine of acceptance angle, 
  // then the angle is greater than acceptance angle -> cull
  return cosAngle < cosAcceptanceAngle;
}

void SteppingAction::UserSteppingAction(const G4Step* step) {
  if (!step || !fEventAction || !fDetector) {
    return;
  }

  const auto* preStepPoint = step->GetPreStepPoint();
  if (!preStepPoint) {
    return;
  }

  const auto* volume = preStepPoint->GetTouchableHandle()->GetVolume();
  if (!volume) {
    return;
  }

  auto* preLogicalVolume = volume->GetLogicalVolume();
  if (preLogicalVolume != fDetector->GetScoringVolume()) {
    return;
  }

  const auto* track = step->GetTrack();
  const auto* postStepPoint = step->GetPostStepPoint();
  const auto* opticalPhoton = G4OpticalPhoton::OpticalPhotonDefinition();

  if (track && postStepPoint && track->GetParentID() == 0) {
    if (IsInteractionProcess(postStepPoint->GetProcessDefinedStep())) {
      fEventAction->RecordPrimaryScintillatorFirstInteraction(
          track->GetTrackID(), postStepPoint->GetGlobalTime());
    }
  }

  if (track && postStepPoint &&
      track->GetParticleDefinition() == opticalPhoton &&
      postStepPoint->GetStepStatus() == fGeomBoundary) {
    const auto* postVolume = postStepPoint->GetTouchableHandle()->GetVolume();
    const auto* postLogicalVolume =
        postVolume ? postVolume->GetLogicalVolume() : nullptr;
    if (postLogicalVolume != preLogicalVolume) {
      fEventAction->RecordPhotonScintillatorExit(track->GetTrackID(),
                                                 postStepPoint->GetPosition());
    }
  }

  if (track && postStepPoint && track->GetParentID() > 0 &&
      track->GetParticleDefinition() != opticalPhoton) {
    fEventAction->RecordSecondaryScintillatorEndpoint(track->GetTrackID(),
                                                      postStepPoint->GetPosition());
  }

  const auto* secondaries = step->GetSecondaryInCurrentStep();
  if (!secondaries || secondaries->empty()) {
    return;
  }

    const G4int primaryTrackID = ResolvePrimaryTrackID(track, fEventAction);

    for (const auto* secondary : *secondaries) {
      if (!secondary) {
        continue;
      }
      const G4bool isOpticalPhoton = secondary->GetParticleDefinition() == opticalPhoton;
      fEventAction->RecordPrimarySecondaryCreation(primaryTrackID, isOpticalPhoton);
      if (!isOpticalPhoton) {
        continue;
      }

      // Record the photon's creation point for later use in TrackingAction
      // Note: Photon culling happens in TrackingAction::PreUserTrackingAction
      // where we can actually kill the track before it's processed
      fEventAction->RecordPendingPhotonOrigin(secondary, secondary->GetPosition());
    }
}
