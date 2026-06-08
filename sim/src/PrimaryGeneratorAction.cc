#include "PrimaryGeneratorAction.hh"

#include "config.hh"

#include "G4Event.hh"
#include "G4GeneralParticleSource.hh"
#include "G4Neutron.hh"
#include "G4ParticleDefinition.hh"
#include "G4PrimaryParticle.hh"
#include "G4PrimaryVertex.hh"

namespace {
G4double GetPrimaryRestMass(const G4PrimaryParticle* primary) {
  if (!primary) {
    return 0.0;
  }
  if (const auto* definition = primary->GetParticleDefinition()) {
    return definition->GetPDGMass();
  }
  return primary->GetMass();
}
}  // namespace

PrimaryGeneratorAction::PrimaryGeneratorAction(const Config* config)
    : fConfig(config), fGPS(new G4GeneralParticleSource()) {
  // Default source particle; macro commands may override it.
  fGPS->SetParticleDefinition(G4Neutron::Definition());
}

PrimaryGeneratorAction::~PrimaryGeneratorAction() { delete fGPS; }

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* event) {
  fGPS->GeneratePrimaryVertex(event);
  if (!event || !fConfig) {
    return;
  }

  const auto timing = fConfig->GetSourceTimingForEvent(event->GetEventID());
  if (!timing.enabled) {
    return;
  }

  for (G4int index = 0; index < event->GetNumberOfPrimaryVertex(); ++index) {
    auto* vertex = event->GetPrimaryVertex(index);
    if (vertex) {
      const auto* primary = vertex->GetPrimary();
      const auto timeOfFlight = fConfig->GetSourceTimingEffectiveTimeOfFlight(
          primary ? primary->GetKineticEnergy() : 0.0,
          GetPrimaryRestMass(primary));
      vertex->SetT0(timing.sourceTime + timeOfFlight);
    }
  }
}
