#include "PrimaryGeneratorAction.hh"

#include "config.hh"

#include "G4Event.hh"
#include "G4Gamma.hh"
#include "G4GeneralParticleSource.hh"
#include "G4Neutron.hh"
#include "G4PhysicalConstants.hh"
#include "G4PrimaryParticle.hh"
#include "G4PrimaryVertex.hh"
#include "G4SystemOfUnits.hh"
#include "Randomize.hh"

#include <algorithm>
#include <cmath>

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

  // Optionally add a coincident 4.439 MeV gamma (C-12 first excited state) to the
  // same vertex as the neutron, so both share the vertex position and time.
  if (fConfig->GetCorrelatedGammaEnabled() &&
      G4UniformRand() < fConfig->GetCorrelatedGammaProbability()) {
    if (auto* vertex = event->GetPrimaryVertex(0)) {
      const G4double energy = 4.439 * MeV;
      const G4double cosTheta = 1.0 - 2.0 * G4UniformRand();
      const G4double sinTheta = std::sqrt(std::max(0.0, 1.0 - cosTheta * cosTheta));
      const G4double phi = CLHEP::twopi * G4UniformRand();
      vertex->SetPrimary(new G4PrimaryParticle(
          G4Gamma::Definition(), energy * sinTheta * std::cos(phi),
          energy * sinTheta * std::sin(phi), energy * cosTheta));
    }
  }

  // Every vertex keeps its default time of zero. Each event is timed from the moment
  // its own source fired; when the event happens in the run is assigned afterwards.
}
