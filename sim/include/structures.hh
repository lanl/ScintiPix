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

namespace detail {

constexpr std::size_t kSpeciesLabelSize = 24;

// Native binary row structures (fixed-size, with explicit padding to ensure stable layout)
// Used for both HDF5 and raw binary output formats
struct BinaryPrimaryRow {
  std::int64_t gun_call_id;
  std::int32_t primary_track_id;
  std::int32_t _padding0;
  char primary_species[kSpeciesLabelSize];
  double primary_x_mm;
  double primary_y_mm;
  double primary_energy_MeV;
  double primary_interaction_time_ns;
  std::int64_t primary_created_secondary_count;
  std::int64_t primary_generated_optical_photon_count;
  std::int64_t primary_detected_optical_interface_photon_count;
};

struct BinarySecondaryRow {
  std::int64_t gun_call_id;
  std::int32_t primary_track_id;
  std::int32_t secondary_track_id;
  char secondary_species[kSpeciesLabelSize];
  double secondary_origin_x_mm;
  double secondary_origin_y_mm;
  double secondary_origin_z_mm;
  double secondary_origin_energy_MeV;
  double secondary_end_x_mm;
  double secondary_end_y_mm;
  double secondary_end_z_mm;
};

struct BinaryPhotonRow {
  std::int64_t gun_call_id;
  std::int32_t primary_track_id;
  std::int32_t secondary_track_id;
  std::int32_t photon_track_id;
  double photon_creation_time_ns;
  double photon_origin_x_mm;
  double photon_origin_y_mm;
  double photon_origin_z_mm;
  double photon_scint_exit_x_mm;
  double photon_scint_exit_y_mm;
  double photon_scint_exit_z_mm;
  double optical_interface_hit_x_mm;
  double optical_interface_hit_y_mm;
  double optical_interface_hit_time_ns;
  double optical_interface_hit_dir_x;
  double optical_interface_hit_dir_y;
  double optical_interface_hit_dir_z;
  double optical_interface_hit_pol_x;
  double optical_interface_hit_pol_y;
  double optical_interface_hit_pol_z;
  double optical_interface_hit_energy_eV;
  double optical_interface_hit_wavelength_nm;
};

}  // namespace detail
}  // namespace SimStructures

#endif
