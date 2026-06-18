#include "TrackingAction.hh"

#include "EventAction.hh"
#include "config.hh"

#include "G4ParticleDefinition.hh"
#include "G4SystemOfUnits.hh"
#include "G4Track.hh"

#include <cmath>
#include <string>

namespace {
std::string ToSpeciesLabel(const G4String& particleName) {
  if (particleName == "neutron") return "n";
  if (particleName == "gamma") return "g";
  if (particleName == "alpha") return "a";
  if (particleName == "proton") return "p";
  if (particleName == "e-") return "electron";
  if (particleName == "e+") return "positron";

  const auto bracket = particleName.find('[');
  if (bracket != std::string::npos) {
    return particleName.substr(0, bracket);
  }
  return particleName;
}

G4int ResolvePrimaryTrackID(const G4Track* track, EventAction* eventAction) {
  if (!track || !eventAction) {
    return -1;
  }
  if (track->GetParentID() == 0) {
    return track->GetTrackID();
  }
  if (const auto* parentInfo = eventAction->FindTrackInfo(track->GetParentID())) {
    return parentInfo->primaryTrackID;
  }
  return -1;
}

bool IsOpticalPhoton(const G4String& particleName) {
  return particleName == "opticalphoton";
}
}  // namespace

TrackingAction::TrackingAction(EventAction* eventAction, const Config* config)
    : fEventAction(eventAction), fConfig(config) {}

bool TrackingAction::ShouldCullPhoton(const G4ThreeVector& photonDirection,
                                      const G4ThreeVector& photonOrigin,
                                      const G4ThreeVector& detectorCenter) const {
  // If culling is disabled, don't cull any photons
  if (!fConfig || !fConfig->GetPhotonCullingEnabled()) {
    return false;
  }

  // Get acceptance angle from config (convert to radians for calculation)
  G4double acceptanceAngleRad = fConfig->GetPhotonCullingAcceptanceAngleDeg() * CLHEP::pi / 180.0;
  G4double cosAcceptanceAngle = std::cos(acceptanceAngleRad);

  // Calculate vector from photon origin to detector center
  G4ThreeVector toDetector = detectorCenter - photonOrigin;

  // If the vector is zero (same position), don't cull
  if (toDetector.mag2() == 0.0) {
    return false;
  }

  // Normalize the direction to detector
  toDetector = toDetector.unit();

  // Calculate dot product (cosine of angle between photon direction and to-detector direction)
  G4double cosAngle = photonDirection.dot(toDetector);

  // Cull if the angle is greater than the acceptance angle
  // (i.e., cosine is less than the cosine of the acceptance angle)
  return cosAngle < cosAcceptanceAngle;
}

void TrackingAction::PreUserTrackingAction(const G4Track* track) {
  if (!fEventAction || !track) {
    return;
  }

  EventAction::TrackInfo trackInfo;
  const auto trackID = track->GetTrackID();
  const auto parentID = track->GetParentID();
  const auto particleName = track->GetParticleDefinition()->GetParticleName();
  trackInfo.species = ToSpeciesLabel(particleName);
  trackInfo.originPosition = track->GetVertexPosition();
  trackInfo.originEnergy = track->GetVertexKineticEnergy();
  trackInfo.primaryTrackID = ResolvePrimaryTrackID(track, fEventAction);
  fEventAction->RecordTrackInfo(trackID, trackInfo);

  if (IsOpticalPhoton(particleName)) {
    // Photon culling: check if photon should be killed based on direction
    if (fConfig && fConfig->GetPhotonCullingEnabled()) {
      const G4ThreeVector photonDirection = track->GetMomentumDirection();
      const G4ThreeVector photonOrigin = track->GetVertexPosition();
      const G4ThreeVector detectorCenter(fConfig->GetOpticalInterfacePosX(),
                                        fConfig->GetOpticalInterfacePosY(),
                                        fConfig->GetOpticalInterfacePosZ());

      if (ShouldCullPhoton(photonDirection, photonOrigin, detectorCenter)) {
        // Kill the track immediately - prevent Geant4 from tracking it
        const_cast<G4Track*>(track)->SetTrackStatus(fStopAndKill);
        return;
      }
    }

    EventAction::PhotonCreationInfo info;
    info.primaryTrackID = trackInfo.primaryTrackID;
    info.secondaryTrackID = parentID;
    info.scintOriginPosition = track->GetVertexPosition();

    // Prefer stepping-recorded creation point when available.
    fEventAction->ConsumePendingPhotonOrigin(track, &info.scintOriginPosition);

    if (parentID > 0) {
      if (const auto* parentInfo = fEventAction->FindTrackInfo(parentID)) {
        if (parentInfo->primaryTrackID >= 0) {
          info.primaryTrackID = parentInfo->primaryTrackID;
        }
        info.secondarySpecies = parentInfo->species;
        info.secondaryOriginPosition = parentInfo->originPosition;
        info.secondaryOriginEnergy = parentInfo->originEnergy;
      }
    }

    fEventAction->RecordPhotonCreationInfo(trackID, info);
  }
}
