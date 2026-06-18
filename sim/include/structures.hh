#ifndef structures_h
#define structures_h 1

#include <cstdint>
#include <limits>
#include <string>

namespace SimStructures {

/// Primary-particle output data.
struct PrimaryInfo {
  std::int64_t gunCallId = -1;
  std::int32_t primaryTrackId = -1;
  std::string primarySpecies = "unknown";
  double primaryXmm = 0.0;
  double primaryYmm = 0.0;
  double primaryEnergyMeV = 0.0;
  double primaryInteractionTimeNs = std::numeric_limits<double>::quiet_NaN();
  std::int64_t primaryCreatedSecondaryCount = 0;
  std::int64_t primaryGeneratedOpticalPhotonCount = 0;
  std::int64_t primaryDetectedOpticalInterfacePhotonCount = 0;
};

/// Secondary-particle output data.
struct SecondaryInfo {
  std::int64_t gunCallId = -1;
  std::int32_t primaryTrackId = -1;
  std::int32_t secondaryTrackId = -1;
  std::string secondarySpecies = "unknown";
  double secondaryOriginXmm = 0.0;
  double secondaryOriginYmm = 0.0;
  double secondaryOriginZmm = 0.0;
  double secondaryOriginEnergyMeV = 0.0;
  double secondaryEndXmm = std::numeric_limits<double>::quiet_NaN();
  double secondaryEndYmm = std::numeric_limits<double>::quiet_NaN();
  double secondaryEndZmm = std::numeric_limits<double>::quiet_NaN();
};

/// Detected optical-photon output data.
struct PhotonInfo {
  std::int64_t gunCallId = -1;
  std::int32_t primaryTrackId = -1;
  std::int32_t secondaryTrackId = -1;
  std::int32_t photonTrackId = -1;
  double photonCreationTimeNs = 0.0;

  double photonOriginXmm = 0.0;
  double photonOriginYmm = 0.0;
  double photonOriginZmm = 0.0;

  double photonScintExitXmm = 0.0;
  double photonScintExitYmm = 0.0;
  double photonScintExitZmm = 0.0;

  double opticalInterfaceHitXmm = 0.0;
  double opticalInterfaceHitYmm = 0.0;
  double opticalInterfaceHitTimeNs = 0.0;

  double opticalInterfaceHitDirX = 0.0;
  double opticalInterfaceHitDirY = 0.0;
  double opticalInterfaceHitDirZ = 0.0;

  double opticalInterfaceHitPolX = 0.0;
  double opticalInterfaceHitPolY = 0.0;
  double opticalInterfaceHitPolZ = 0.0;

  double opticalInterfaceHitEnergyEV = -1.0;
  double opticalInterfaceHitWavelengthNm = -1.0;
};

}  // namespace SimStructures

#endif
