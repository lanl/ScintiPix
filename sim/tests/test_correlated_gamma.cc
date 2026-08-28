// Unit tests for the optional coincident 4.439 MeV gamma (issue #26):
// the Config storage, the messenger commands that set it, and the coincidence
// (the gamma shares the neutron's primary vertex).

#include <gtest/gtest.h>

#include "PrimaryGeneratorAction.hh"
#include "config.hh"
#include "messenger.hh"

#include "G4Event.hh"
#include "G4Gamma.hh"
#include "G4Neutron.hh"
#include "G4PrimaryParticle.hh"
#include "G4PrimaryVertex.hh"
#include "G4RunManager.hh"
#include "G4RunManagerFactory.hh"
#include "G4SystemOfUnits.hh"
#include "G4UImanager.hh"
#include "G4VModularPhysicsList.hh"

namespace {

// --- Config storage ------------------------------------------------------

TEST(CorrelatedGammaConfig, DefaultsOff) {
  Config config;
  EXPECT_FALSE(config.GetCorrelatedGammaEnabled());
  EXPECT_DOUBLE_EQ(config.GetCorrelatedGammaProbability(), 0.0);
}

TEST(CorrelatedGammaConfig, SettersStoreValidValues) {
  Config config;
  config.SetCorrelatedGammaEnabled(true);
  config.SetCorrelatedGammaProbability(0.582);
  EXPECT_TRUE(config.GetCorrelatedGammaEnabled());
  EXPECT_DOUBLE_EQ(config.GetCorrelatedGammaProbability(), 0.582);
}

TEST(CorrelatedGammaConfig, ProbabilityOutOfRangeRejected) {
  Config config;
  config.SetCorrelatedGammaProbability(0.4);
  config.SetCorrelatedGammaProbability(1.5);   // out of range, keeps 0.4
  EXPECT_DOUBLE_EQ(config.GetCorrelatedGammaProbability(), 0.4);
  config.SetCorrelatedGammaProbability(-0.1);  // out of range, keeps 0.4
  EXPECT_DOUBLE_EQ(config.GetCorrelatedGammaProbability(), 0.4);
}

// --- Messenger wiring ----------------------------------------------------

TEST(CorrelatedGammaMessenger, CommandsUpdateConfig) {
  Config config;
  Messenger messenger(&config);
  auto* ui = G4UImanager::GetUIpointer();

  ui->ApplyCommand("/source/correlatedGamma/enabled 1");
  EXPECT_TRUE(config.GetCorrelatedGammaEnabled());

  ui->ApplyCommand("/source/correlatedGamma/probability 0.582");
  EXPECT_DOUBLE_EQ(config.GetCorrelatedGammaProbability(), 0.582);

  ui->ApplyCommand("/source/correlatedGamma/enabled 0");
  EXPECT_FALSE(config.GetCorrelatedGammaEnabled());
}

// --- Coincidence ---------------------------------------------------------

// Geant4 forbids constructing a primary generator before a physics list is set
// on the run manager, so the coincidence tests establish that minimal context
// once for the whole suite.
class CorrelatedGammaCoincidence : public ::testing::Test {
 protected:
  static void SetUpTestSuite() {
    if (!G4RunManager::GetRunManager()) {
      auto* runManager =
          G4RunManagerFactory::CreateRunManager(G4RunManagerType::SerialOnly);
      runManager->SetUserInitialization(new G4VModularPhysicsList());
    }
  }
  static void TearDownTestSuite() { delete G4RunManager::GetRunManager(); }
};

TEST_F(CorrelatedGammaCoincidence, DisabledLeavesNeutronOnly) {
  Config config;  // gamma disabled by default
  PrimaryGeneratorAction generator(&config);
  G4Event event;
  generator.GeneratePrimaries(&event);

  ASSERT_GE(event.GetNumberOfPrimaryVertex(), 1);
  const auto* vertex = event.GetPrimaryVertex(0);
  ASSERT_NE(vertex, nullptr);
  EXPECT_EQ(vertex->GetNumberOfParticle(), 1);
  EXPECT_EQ(vertex->GetPrimary(0)->GetParticleDefinition(),
            G4Neutron::Definition());
}

TEST_F(CorrelatedGammaCoincidence, ZeroProbabilityAddsNoGamma) {
  Config config;
  config.SetCorrelatedGammaEnabled(true);
  config.SetCorrelatedGammaProbability(0.0);
  PrimaryGeneratorAction generator(&config);
  G4Event event;
  generator.GeneratePrimaries(&event);

  ASSERT_GE(event.GetNumberOfPrimaryVertex(), 1);
  const auto* vertex = event.GetPrimaryVertex(0);
  ASSERT_NE(vertex, nullptr);
  EXPECT_EQ(vertex->GetNumberOfParticle(), 1);
}

TEST_F(CorrelatedGammaCoincidence, CertainProbabilityAddsGammaToSameVertex) {
  Config config;
  config.SetCorrelatedGammaEnabled(true);
  config.SetCorrelatedGammaProbability(1.0);
  PrimaryGeneratorAction generator(&config);
  G4Event event;
  generator.GeneratePrimaries(&event);

  // One vertex holds both primaries, so neutron and gamma share position/time.
  ASSERT_EQ(event.GetNumberOfPrimaryVertex(), 1);
  const auto* vertex = event.GetPrimaryVertex(0);
  ASSERT_NE(vertex, nullptr);
  ASSERT_EQ(vertex->GetNumberOfParticle(), 2);

  const auto* neutron = vertex->GetPrimary(0);
  const auto* gamma = vertex->GetPrimary(1);
  ASSERT_NE(neutron, nullptr);
  ASSERT_NE(gamma, nullptr);
  EXPECT_EQ(neutron->GetParticleDefinition(), G4Neutron::Definition());
  EXPECT_EQ(gamma->GetParticleDefinition(), G4Gamma::Definition());
  EXPECT_NEAR(gamma->GetTotalEnergy(), 4.439 * MeV, 1e-6 * MeV);
}

}  // namespace
