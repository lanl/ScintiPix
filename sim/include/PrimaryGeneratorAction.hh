#ifndef PrimaryGeneratorAction_h
#define PrimaryGeneratorAction_h 1

#include "G4VUserPrimaryGeneratorAction.hh"

class G4Event;
class G4GeneralParticleSource;
class Config;

/// Primary-particle source action backed by Geant4 GPS.
class PrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction {
 public:
  explicit PrimaryGeneratorAction(const Config* config);
  ~PrimaryGeneratorAction() override;

  /// Generate primary vertex/particles for one event.
  void GeneratePrimaries(G4Event* event) override;

 private:
  /// Shared runtime configuration used for optional source timing.
  const Config* fConfig = nullptr;
  /// Geant4 GeneralParticleSource (configured via macro/UI commands).
  G4GeneralParticleSource* fGPS = nullptr;
};

#endif
