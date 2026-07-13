#include "ResolutionTargetConstruction.hh"

#include "G4Colour.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4PVPlacement.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4Tubs.hh"
#include "G4VisAttributes.hh"

#include <string>

void ConstructSiemensStarResolutionTarget(G4LogicalVolume* motherVolume,
                                          G4Material* absorberMaterial,
                                          const G4ThreeVector& center,
                                          G4double innerRadius,
                                          G4double outerRadius,
                                          G4double thickness,
                                          G4int linePairs) {
  if (!motherVolume || !absorberMaterial || linePairs <= 0 || thickness <= 0.0 ||
      innerRadius < 0.0 || outerRadius <= innerRadius) {
    return;
  }

  const auto pairPhi = 360.0 * deg / static_cast<G4double>(linePairs);
  const auto opaquePhi = 0.5 * pairPhi;

  static auto* targetVisAttributes = []() {
    auto* vis = new G4VisAttributes(G4Colour(1.0, 1.0, 1.0, 0.95));
    vis->SetVisibility(true);
    vis->SetForceSolid(true);
    return vis;
  }();

  for (G4int i = 0; i < linePairs; ++i) {
    const auto startPhi = static_cast<G4double>(i) * pairPhi;
    const auto suffix = std::to_string(i);
    auto* wedgeSolid = new G4Tubs(("SiemensStarWedgeSolid_" + suffix).c_str(),
                                  innerRadius,
                                  outerRadius,
                                  0.5 * thickness,
                                  startPhi,
                                  opaquePhi);
    auto* wedgeLV = new G4LogicalVolume(
        wedgeSolid, absorberMaterial, ("SiemensStarWedgeLV_" + suffix).c_str());
    wedgeLV->SetVisAttributes(targetVisAttributes);

    new G4PVPlacement(nullptr,
                      center,
                      wedgeLV,
                      ("SiemensStarWedgePV_" + suffix).c_str(),
                      motherVolume,
                      false,
                      i,
                      true);
  }
}
