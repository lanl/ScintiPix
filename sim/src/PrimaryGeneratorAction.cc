#include "PrimaryGeneratorAction.hh"

#include "config.hh"

#include "G4Event.hh"
#include "G4GeneralParticleSource.hh"
#include "G4Neutron.hh"
#include "G4PrimaryVertex.hh"

PrimaryGeneratorAction::PrimaryGeneratorAction(const Config* config)
    : fConfig(config), fGPS(new G4GeneralParticleSource()) {
  // Default source particle; macro commands may override it.
  fGPS->SetParticleDefinition(G4Neutron::Definition());
}

PrimaryGeneratorAction::~PrimaryGeneratorAction() { delete fGPS; }

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* event) {
  if (!event) {
    return;
  }

  fGPS->GeneratePrimaryVertex(event);
  if (!fConfig) {
    return;
  }

  const auto timing = fConfig->GetSourceTimingForEvent(event->GetEventID());
  if (!timing.enabled) {
    return;
  }

  for (G4int index = 0; index < event->GetNumberOfPrimaryVertex(); ++index) {
    auto* vertex = event->GetPrimaryVertex(index);
    if (vertex) {
      vertex->SetT0(timing.creationTime);
    }
  }
}
