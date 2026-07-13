#ifndef ResolutionTargetConstruction_h
#define ResolutionTargetConstruction_h 1

#include "globals.hh"
#include "G4ThreeVector.hh"

class G4LogicalVolume;
class G4Material;

/// Construct a Siemens star absorber target from repeated annular sectors.
void ConstructSiemensStarResolutionTarget(G4LogicalVolume* motherVolume,
                                          G4Material* absorberMaterial,
                                          const G4ThreeVector& center,
                                          G4double innerRadius,
                                          G4double outerRadius,
                                          G4double thickness,
                                          G4int linePairs);

#endif
